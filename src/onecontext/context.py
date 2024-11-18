import dataclasses
import json
import mimetypes
import os
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm
from urllib3.util import Retry

from onecontext.client import URLS, ApiClient
from onecontext.models import Chunk, File, PydanticV2BaseModel
from onecontext.utils import batch_by_size

SUPPORTED_FILE_TYPES = (
    ".pdf",
    ".docx",
    ".doc",
    ".docx",
    ".epub",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".heic",
    ".eml",
    ".html",
    ".md",
    ".msg",
    ".rst",
    ".rtf",
    ".txt",
    ".xml",
)


MAX_UPLOAD = 15_000


def guess_mime_type(file_path: Union[str, Path]):
    _mime_type = mimetypes.guess_type(file_path)
    mime_type = _mime_type[0] if _mime_type else "application/octet-stream"
    return mime_type


def is_supported_file(file_path: Union[str, Path]) -> bool:
    return Path(file_path).suffix in SUPPORTED_FILE_TYPES


def parse_file_path(file_path: Union[str, Path]):
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"The file at {file_path} does not exist.")

    if not is_supported_file(file_path):
        msg = f"{file_path} is not supported. Supported file types: {SUPPORTED_FILE_TYPES}"
        raise ValueError(msg)
    return file_path


def flatten_dict(dict_: Dict, parent_key: str = "", sep: str = "_") -> Dict:
    items = []
    for k, v in dict_.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def check_keys(dictionary):
    bad_chars = [".", "-", "\\"]
    for key, value in dictionary.items():
        if any(char in key for char in bad_chars):
            raise ValueError(f"Key '{key}' contains invalid character(s): {bad_chars}")
        if isinstance(value, dict):
            check_keys(value)


def parse_metadata(metadata: Dict, flatten: bool = False):
    # Check if the dictionary is JSON serializable

    try:
        json.dumps(metadata)
    except (TypeError, OverflowError) as error:
        raise ValueError("The provided metadata is not JSON serializable") from error

    check_keys(metadata)

    if flatten:
        return flatten_dict(metadata)
    return metadata


def parse_plain_text_file_name(file_name: str) -> Path:
    plain_text_extensions = [
        ".eml",
        ".html",
        ".md",
        ".msg",
        ".rst",
        ".rtf",
        ".txt",
        ".xml",
    ]

    file_name_path = Path(file_name)
    if file_name_path.suffix not in plain_text_extensions:
        raise ValueError(
            f"{file_name} is not a valid plain text file_name. Extension must be one of {plain_text_extensions}"
        )
    return file_name_path


@dataclass
class Context:
    name: str
    _urls: URLS = field(repr=False)
    _client: ApiClient = field(repr=False)
    id: Optional[str] = None
    user_id: Optional[str] = None
    date_created: Optional[datetime] = None

    def list_files(
        self,
        *,
        file_ids: Optional[list] = None,
        file_names: Optional[list] = None,
        skip=0,
        limit=500,
        sort="date_created",
        get_download_urls: bool = False,
    ) -> List[File]:
        """
        Lists files in the context base with various filtering, sorting, and pagination options.

        Parameters
        ----------
        file_ids : list, optional
            A list of file IDs to filter the files to be listed. If None, all files are listed.
        file_names: list, optional
            A list of files names to filter the files to be listed. If None, all files are listed.
        skip : int, optional
            The number of files to skip (default is 0).
        limit : int, optional
            The maximum number of files to return (default is 20).
        sort : str, optional
            The field to sort by (default is "date_created").
            Reverse with "-date_created"

        get_download_urls : bool, optional
            If True, also returns download URLs for each file (default is False).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries, each representing a file with its metadata.

        """

        if file_names and file_ids:
            raise ValueError("You cannot pass both file_names AND file_ids parameters. You have to choose one.")

        data: Dict[str, Any] = self._client.post(
            self._urls.context_files(),
            json={
                "contextName": self.name,
                "skip": skip,
                "limit": limit,
                "sort": sort,
                "getDownloadUrls": get_download_urls,
                "fileIds": file_ids,
                "fileNames": file_names,
            },
        )

        file_dicts = [
            {field.name: file.get(field.name) for field in dataclasses.fields(File)} for file in data["files"]
        ]

        files = [File(**file_dict) for file_dict in file_dicts]

        return files

    def get_chunks_by_ids(self, ids: List[str]) -> List[Chunk]:
        data = {"contextName": self.name, "chunkIds": ids}

        response = self._client.post(self._urls.context_chunks_by_ids(), json=data)

        chunk_dicts = [
            {field.name: chunk.get(field.name) for field in dataclasses.fields(Chunk)} for chunk in response["chunks"]
        ]
        chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
        return chunks

    def _get_upload_params(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Retrieves the upload parameters for the given file names.

        This method posts a request to the context files upload URL with the file names
        and context name. It processes the response to retrieve upload parameters for each file.

        :param file_names: A list of file names for which to retrieve upload parameters
        :return: A list of dictionaries each containing the upload parameters for a file.
                 The dictionary keys include:
                 - "presignedUrl": A URL for the client to upload files directly to the storage
                 - "fileId": A unique identifier for the file
                 - "gcsUri": The Google Cloud Storage URI of the uploaded file
                -  "fileType" : the file type
        """

        file_names = [path.name for path in file_paths]
        data = {"fileNames": file_names, "contextName": self.name}
        upload_params_data = self._client.post(self._urls.context_files_upload_url(), json=data)
        for path, params in zip(file_paths, upload_params_data):
            params["fileName"] = path.name
            params["fileType"] = guess_mime_type(path)

        return upload_params_data

    def _upload_file(self, file_path: Path, upload_url: str, content_type: str):
        file_content = file_path.read_bytes()
        # Upload the file to the presigned URL
        s = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retries))
        response = s.put(upload_url, data=file_content, headers={"Content-Type": content_type})

        if response.status_code != 200:
            raise ValueError(f"Failed to upload {file_path!s} to OneContext Storage.")

    def upload_files(
        self,
        file_paths: Union[List[str], List[Path]],
        metadata: Optional[List[dict]] = None,
        max_chunk_size: int = 200,
        flatten_metadata: bool = False,
        max_workers: int = 10,
        verbose: Optional[bool] = None,
    ) -> List[str]:
        """
        Uploads files to the context.

        This method uploads files specified by `file_paths` to the context, optionally
        associating them with metadata. It retrieves a presigned URL for each file,
        uploads the file to the presigned URL, and then notifies the context about the
        uploaded file.

        Parameters
        ----------
        file_paths : Union[str, Path]
            The paths to the files to be uploaded. Can be strings or Path objects.

        metadata : Optional[list[dict]], optional
            A list of dictionaries containing metadata for each file. The keys "file_name",
            "user_id", "file_path", and "file_id" are reserved and cannot be used.

        max_chunk_size : int, optional
            The maximum size of the resulting chunks in words

        flatten_metadata: bool
            Whether to flatten metadata dicts with a "_" separator
            ie. {"key" : {"nestedkey": "value"}} => {"key_nestedkey" : "value"}}
            Note metadata filters only work for top level keys, use this option
            to make all metadata queryable

        max_workers : int
            The maximum number of threads to use for uploading files


        verbose : Optional[bool]
            Display tqdm progress bar


        Raises
        ------
        ValueError
            If any reserved keys are present in the metadata.
            If the file type is not supported (not in SUPPORTED_FILE_TYPES).
        """

        if len(file_paths) > MAX_UPLOAD:
            raise ValueError(f"You cannot upload more that {MAX_UPLOAD} files at a time")

        _file_paths = [parse_file_path(path) for path in file_paths]

        if metadata and len(metadata) != len(file_paths):
            raise ValueError("Number of metadata entries and files do not match.")

        if not metadata:
            metadata = [{} for _ in _file_paths]

        metadata = [parse_metadata(m, flatten_metadata) for m in metadata]

        disable = not verbose if verbose is not None else None

        upload_files_spec = self._get_upload_params(_file_paths)

        upload_args = [
            (path, upload_file["presignedUrl"], upload_file["fileType"])
            for path, upload_file in zip(_file_paths, upload_files_spec)
        ]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(
                tqdm(
                    executor.map(lambda args: self._upload_file(*args), upload_args),
                    total=len(upload_args),
                    disable=disable,
                    desc="Uploading files",
                )
            )

        for uploaded_file, meta in zip(upload_files_spec, metadata):
            uploaded_file["metadataJson"] = meta

        process_uploaded_batches = []

        for batch in batch_by_size(upload_files_spec, 3):
            data = {
                "contextName": self.name,
                "contextId": self.id,
                "maxChunkSize": max_chunk_size,
                "files": batch,
            }

            process_uploaded_batches.append(data)

        def _processes_uploaded(data):
            self._client.post(self._urls.context_files_upload_processed(), json=data)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(
                tqdm(
                    executor.map(_processes_uploaded, process_uploaded_batches),
                    total=len(process_uploaded_batches),
                    desc="Uploading metadata (batches)",
                    disable=disable,
                )
            )

        file_ids = [spec["fileId"] for spec in upload_files_spec]

        return file_ids

    def upload_texts(
        self,
        contents: List[str],
        file_names: Optional[List[str]] = None,
        metadata: Optional[List[dict]] = None,
        max_chunk_size: int = 200,
        flatten_metadata: bool = False,
        max_workers: int = 10,
    ) -> List[str]:
        """
        Uploads text content as files to the context.

        This method uploads text content specified by `contents` to the context, optionally
        associating them with file names and metadata. It generates temporary files for the
        contents, , and then notifies the context about the uploaded file.

        Parameters
        ----------
        contents : list[str]
            The text content to be uploaded.

        file_names : Optional[list[str]], optional
            The names for the files to be created from `contents`. If not provided, UUIDs
            will be used as file names with .txt extension.

        metadata : Optional[list[dict]], optional
            A list of dictionaries containing metadata for each file.

        max_chunk_size : int, optional
            The maximum size of the resulting chunks in characters

        flatten_metadata: bool
            Whether to flatten metadata dicts with a "_" separator
            ie. {"key" : {"nestedkey": "value"}} => {"key_nestedkey" : "value"}}
            Note metadata filters only work for top level keys, use this option
            to make all metadata queryable

        max_workers : int
            The maximum number of threads to use for uploading files

        Raises
        ------
        ValueError
            If the number of file names and contents do not match.
        """

        if file_names and len(file_names) != len(contents):
            raise ValueError("Number of file names and contents do not match.")

        if file_names:
            valid_file_names = [parse_plain_text_file_name(file_name) for file_name in file_names]
        else:
            valid_file_names = [Path(f"{uuid.uuid4()}.txt") for _ in contents]

        all_contents = [bool(len(content)) for content in contents]

        if not all(all_contents):
            raise ValueError("Attempting to upload empty string")

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_paths = []

            for content, file_name in zip(contents, valid_file_names):
                file_path = Path(tmp_dir) / file_name
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                file_paths.append(file_path)

            file_ids = self.upload_files(
                file_paths=file_paths,
                metadata=metadata,
                max_chunk_size=max_chunk_size,
                flatten_metadata=flatten_metadata,
                max_workers=max_workers,
            )

        return file_ids

    def upload_from_directory(
        self,
        directory: Union[str, Path],
        metadata: Optional[dict] = None,
        max_chunk_size: int = 200,
        flatten_metadata: bool = False,
        max_workers: int = 10,
    ) -> List[str]:
        """
        Uploads files from a given directory to a context.

        This method uploads all files within a specified directory that match the supported file types.

        Parameters
        ----------
        directory : Union[str, Path]
            The path to the directory containing the files to be uploaded. Can be a string or a Path object.

        metadata : Optional[dict], optional
            Metadata associated with the files to be uploaded.
            Note, the same metadata will be associated with every file in the directory

        max_chunk_size : int, optional
            The maximum size of the resulting chunks in characters

        flatten_metadata: bool
            Whether to flatten metadata dicts with a "_" separator
            ie. {"key" : {"nestedkey": "value"}} => {"key_nestedkey" : "value"}}
            Note metadata filters only work for top level keys, use this option
            to make all metadata queryable

        max_workers : int
            The maximum number of threads to use for uploading files
        Raises
        ------
        ValueError
            If the provided directory is not an actual directory or no valid files are found

        """
        directory = Path(directory).expanduser().resolve()

        if not directory.is_dir():
            msg = "You must provide a directory"
            raise ValueError(msg)
        directory = str(directory)

        all_files = [os.path.join(dp, f) for dp, _, filenames in os.walk(directory) for f in filenames]

        files_to_upload = [file for file in all_files if is_supported_file(file)]

        if not files_to_upload:
            raise ValueError("No supported files found")

        metadata_list = [metadata] * len(files_to_upload) if metadata else None

        file_ids = self.upload_files(
            file_paths=files_to_upload,
            metadata=metadata_list,
            flatten_metadata=flatten_metadata,
            max_workers=max_workers,
        )

        return file_ids

    def search(
        self,
        query: str,
        top_k: int = 10,
        *,
        semantic_weight: float = 0.5,
        full_text_weight: float = 0.5,
        rrf_k: int = 60,
        include_embedding: bool = False,
        metadata_filters: Optional[dict] = None,
    ) -> List[Chunk]:
        """
        Runs a hybrid query using semantic and full-text search
        against the context.

        Parameters
        ----------
        query : str
            The query string to search for.
        semantic_weight : float, optional
            The weight given to semantic search results, by default 0.5.
        full_text_weight : float, optional
            The weight given to full-text search results, by default 0.5.
            this is uses key word search to compliment semantic search results
        rrf_k : int, optional
            The reciprocal rank fusion parameter for combining semantic and full-text search scores, by default 60.
        top_k : int, optional
            The number of top results to return, by default 10.
        include_embedding : bool, optional
            Flag to include the embedding in the returned Chunk objects, by default False.
        metadata_filters : Optional[dict[str, Any]], optional
            A dictionary of filters based on metadata to apply to the chunk retrieval.

        Returns
        -------
        List[Chunk]
            A list of Chunk objects that are the result of running the query with the specified parameters.

        Examples
        --------
        >>> context = oc.Context("my_context")
        >>> query_str = "What are consequences of inventing a computer?"
        >>> chunks = context.query(
        ...     query=query_str,
        ...     semantic_weight=0.7,
        ...     full_text_weight=0.3,
        ...     top_k=5
        ... )
        """
        if not query:
            raise ValueError("The query string must not be empty.")

        if not (0 <= semantic_weight <= 1):
            raise ValueError("semantic_weight must be between 0 and 1.")

        if not (0 <= full_text_weight <= 1):
            raise ValueError("full_text_weight must be between 0 and 1.")

        if semantic_weight == 0 and full_text_weight == 0:
            raise ValueError("Both semantic_weight and full_text_weight cannot be zero.")

        params = {
            "query": query,
            "semanticWeight": semantic_weight,
            "fullTextWeight": full_text_weight,
            "rrfK": rrf_k,
            "topK": top_k,
            "includeEmbedding": include_embedding,
            "contextName": self.name,
            "structuredOutput": None,
        }

        if metadata_filters is not None:
            params.update({"metadataFilters": metadata_filters})

        return self._post_query(params)

    def _post_query(self, params: Dict[str, Any]) -> List[Chunk]:
        results = self._client.post(self._urls.context_search(), json=params)
        return [Chunk(**chunk) for chunk in results["chunks"]]

    def delete_file(self, file_id: str) -> None:
        data = {"fileId": file_id}
        self._client.delete(self._urls.context_files(), json=data)

    def get_download_url(self, file_id: str) -> str:
        data = {"fileId": file_id}
        result = self._client.post(self._urls.context_files_download_url(), json=data)
        return result

    def list_chunks(
        self,
        *,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        include_embedding: bool = False,
        file_id: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Retrieves a list of Chunk objects from the context with optional filters.

        Parameters
        ----------
        metadata_filters : Optional[dict[str, Any]], optional
            A dictionary of filters based on metadata to apply to the chunk retrieval.
        limit : int, optional
            The maximum number of Chunk objects to return, by default 50.
        include_embedding : bool, optional
            Flag to include the embedding in the returned Chunk objects, by default False.
        file_id : Optional[str], optional
            A specific file ID to filter chunks by, by default None.

        Returns
        -------
        list[Chunk]
            A list of Chunk objects

        Examples
        --------
        >>> context = oc.Context("my_context")
        >>> file_id = "example-file-id"
        >>> chunks = context.list_chunks(
        ...     metadata_filters={'author': {'$eq' : 'Jane Doe'}},
        ...     limit=20,
        ...     include_embedding=,
        ...     file_id=file_id
        ... )
        """
        data = {
            "contextName": self.name,
            "limit": limit,
            "includeEmbedding": include_embedding,
        }

        if metadata_filters is not None:
            data.update({"metadataFilters": metadata_filters})

        if file_id is not None:
            data.update({"fileId": file_id})

        out = self._client.post(self._urls.context_chunks(), json=data)
        chunk_dicts = out["chunks"]
        chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
        return chunks

    def extract_from_search(
        self,
        query: str,
        schema: Union[Dict[str, Any], PydanticV2BaseModel],
        extraction_prompt: str,
        *,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        full_text_weight: float = 0.5,
        rrf_k: int = 60,
        include_embedding: bool = False,
        metadata_filters: Optional[dict] = None,
    ) -> Tuple[dict, List[Chunk]]:
        """
        Runs a hybrid query using semantic and full-text search
        against the context.

        Parameters
        ----------
        query : str
            The query string to search for.
        schema: dict | PydanticV2BaseModel
            the schema to be populated or a pydantic (v2) Base Model
        extraction_prompt: str
            the prompt to pass to the model at extraction time. eg: "Produce only json output matching the given schema"

        semantic_weight : float, optional
            The weight given to semantic search results, by default 0.5.
        full_text_weight : float, optional
            The weight given to full-text search results, by default 0.5.
            this is uses key word search to compliment semantic search results
        rrf_k : int, optional
            The reciprocal rank fusion parameter for combining semantic and full-text search scores, by default 60.
        top_k : int, optional
            The number of top results to return, by default 10.
        include_embedding : bool, optional
            Flag to include the embedding in the returned Chunk objects, by default False.
        metadata_filters : Optional[dict[str, Any]], optional
            A dictionary of filters based on metadata to apply to the chunk retrieval.

        Returns
        -------
        List[Chunk]
            A list of Chunk objects that are the result of running the query with the specified parameters.

        """

        if isinstance(schema, PydanticV2BaseModel):
            schema = schema.model_json_schema()
        elif not isinstance(schema, dict):
            raise ValueError(
                "The Schema passed must be either a Pydantic v2 BaseModel (i.e. a BaseModel with a 'model_json_schema' method which outputs valid json schema, or, a dictionary which already confirms to valid json schema. (For more on the exact definition of json schema see: https://json-schema.org/)."
            )

        if not query:
            raise ValueError("The query string must not be empty.")

        if not extraction_prompt:
            raise ValueError("The prompt string must not be empty.")

        if not (0 <= semantic_weight <= 1):
            raise ValueError("semantic_weight must be between 0 and 1.")

        if not (0 <= full_text_weight <= 1):
            raise ValueError("full_text_weight must be between 0 and 1.")

        if semantic_weight == 0 and full_text_weight == 0:
            raise ValueError("Both semantic_weight and full_text_weight cannot be zero.")

        params = {
            "query": query,
            "semanticWeight": semantic_weight,
            "fullTextWeight": full_text_weight,
            "rrfK": rrf_k,
            "topK": top_k,
            "includeEmbedding": include_embedding,
            "contextName": self.name,
            "structuredOutputRequest": {"structuredOutputSchema": schema, "prompt": extraction_prompt},
        }

        if metadata_filters is not None:
            params.update({"metadataFilters": metadata_filters})

        results = self._client.post(self._urls.context_search(), json=params)
        chunks = [Chunk(**chunk) for chunk in results["chunks"]]
        output = results["output"]
        return output, chunks

    def extract_from_chunks(
        self,
        schema: Union[Dict[str, Any], PydanticV2BaseModel],
        extraction_prompt: str,
        *,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        include_embedding: bool = False,
        file_id: Optional[str] = None,
    ) -> Tuple[dict, List[Chunk]]:
        """
        Retrieves a list of Chunk objects from the context with optional filters.

        Parameters
        ----------
        schema: dict | PydanticV2BaseModel
            the schema to be populated, either a valid json schema or pydantic BaseModel
        extraction_prompt: str
            the prompt to pass to the model at extraction time. eg: "Produce only json output matching the given schema"
        metadata_filters : Optional[dict[str, Any]], optional
            A dictionary of filters based on metadata to apply to the chunk retrieval.
        limit : int, optional
            The maximum number of Chunk objects to return, by default 50.
        include_embedding : bool, optional
            Flag to include the embedding in the returned Chunk objects, by default False.
        file_id : Optional[str], optional
            A specific file ID to filter chunks by, by default None.

        Returns
        -------
        list[Chunk]
            A list of Chunk objects

        """

        if isinstance(schema, PydanticV2BaseModel):
            schema = schema.model_json_schema()
        elif not isinstance(schema, dict):
            raise ValueError(
                "The Schema passed must be either a Pydantic v2 BaseModel (i.e. a BaseModel with a 'model_json_schema' method which outputs valid json schema, or, a dictionary which already confirms to valid json schema. (For more on the exact definition of json schema see: https://json-schema.org/)."
            )

        if not extraction_prompt:
            raise ValueError("The prompt string must not be empty.")

        data = {
            "contextName": self.name,
            "limit": limit,
            "includeEmbedding": include_embedding,
            "structuredOutputRequest": {"structuredOutputSchema": schema, "prompt": extraction_prompt},
        }

        if metadata_filters is not None:
            data.update({"metadataFilters": metadata_filters})

        if file_id is not None:
            data.update({"fileId": file_id})

        out = self._client.post(self._urls.context_chunks(), json=data)
        chunk_dicts = out["chunks"]
        output = out["output"]
        chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
        return output, chunks

