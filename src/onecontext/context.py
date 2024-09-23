import dataclasses
import json
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from onecontext.client import URLS, ApiClient
from onecontext.models import Chunk, File

SUPPORTED_FILE_TYPES = (".pdf", ".docx")


def parse_file_path(file_path: str | Path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"The file at {file_path} does not exist.")

    suffix = file_path.suffix
    if suffix not in SUPPORTED_FILE_TYPES:
        msg = f"{suffix} files are not supported. Supported file types: {SUPPORTED_FILE_TYPES}"
        raise ValueError(msg)
    return file_path


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

        data: Dict[str, Any] = self._client.post(
            self._urls.context_files(),
            json={
                "contextName": self.name,
                "skip": skip,
                "limit": limit,
                "sort": sort,
                "getDownloadUrls": get_download_urls,
                "fileIds": file_ids,
            },
        )

        file_dicts = [
            {field.name: file.get(field.name) for field in dataclasses.fields(File)} for file in data["files"]
        ]

        files = [File(**file_dict) for file_dict in file_dicts]

        return files

    def _get_upload_url(self, file_name: str):
        data = {"fileName": file_name, "contextName": self.name, "contextId": self.id}
        response = self._client.post(self._urls.context_files_upload_url(), json=data)

        upload_url = response.get("presignedUrl")
        file_id = response.get("fileId")
        storage_uri = response.get("gcsUri")

        return upload_url, file_id, storage_uri

    def _notify_uploaded(self, file_id, file_name, file_mime_type, gcs_uri, metadata_json, max_chunk_size=600):
        data = {
            "fileId": file_id,
            "fileName": file_name,
            "fileType": file_mime_type,
            "gcsUri": gcs_uri,
            "contextName": self.name,
            "contextId": self.id,
            "maxChunkSize": max_chunk_size,
            "metadataJson": metadata_json,
        }

        self._client.post(self._urls.context_files_upload_processed(), json=data)

    def upload_files(
        self, file_paths: Union[list[str], list[Path]], metadata: Optional[list[dict]] = None, max_chunk_size: int = 600
    ) -> None:
        """
        Uploads files to the context using presigned URLs.

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

        Raises
        ------
        ValueError
            If any reserved keys are present in the metadata.
            If the file type is not supported (not in SUPPORTED_FILE_TYPES).
        """
        if metadata and len(metadata) != len(file_paths):
            raise ValueError("Number of metadata entries and files do not match.")

        _file_paths = [parse_file_path(path) for path in file_paths]

        for index, file_path in enumerate(_file_paths):
            _mime_type = mimetypes.guess_type(file_path)

            mime_type = _mime_type[0] if _mime_type else "application/octet-stream"

            file_name = file_path.name
            file_content = file_path.read_bytes()

            gcs_upload_url, file_id, gcs_uri = self._get_upload_url(file_name)
            # Upload the file to the presigned URL
            response = requests.put(gcs_upload_url, data=file_content, headers={"Content-Type": mime_type})

            if response.status_code != 200:
                raise ValueError(f"Failed to upload {file_name} to Google Cloud Storage.")

            metadata_json = metadata[index] if metadata else {}
            self._notify_uploaded(file_id, file_name, mime_type, gcs_uri, metadata_json, max_chunk_size)

    def upload_from_directory(
        self, directory: Union[str, Path], metadata: Optional[dict] = None, max_chunk_size: int = 600
    ) -> None:
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

        files_to_upload = [file for file in all_files if file.endswith(SUPPORTED_FILE_TYPES)]

        if not files_to_upload:
            raise ValueError("No supported files found")

        metadata_list = [metadata] * len(files_to_upload) if metadata else None

        self.upload_files(files_to_upload, metadata_list)

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
        }

        if metadata_filters is not None:
            params.update({"metadataFilters": metadata_filters})

        return self._post_query(params)

    def _post_query(self, params: Dict[str, Any]) -> List[Chunk]:
        results = self._client.post(self._urls.context_search(), json=params)
        return [Chunk(**chunk) for chunk in results]

    def delete_file(self, file_id: str) -> None:
        data = {"fileId": file_id}
        self._client.post(self._urls.context_files(), json=data)

    def get_download_url(self, file_id: str) -> str:
        data = {"fileId": file_id}
        result = self._client.post(self._urls.context_files_download_url(), json=data)
        return result

    def list_chunks(
        self,
        *,
        metadata_filters: Optional[dict[str, Any]] = None,
        limit: int = 50,
        include_embedding: bool = False,
        file_id: Optional[str] = None,
    ) -> list[Chunk]:
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

        chunk_dicts = self._client.post(self._urls.context_chunks(), json=data)
        chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
        return chunks
