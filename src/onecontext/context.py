import dataclasses
import io
import json
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from onecontext.client import URLS, ApiClient
from onecontext.models import Chunk, File

SUPPORTED_FILE_TYPES = (".pdf", ".docx")


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
        skip=0,
        limit=500,
        sort="date_created",
    ) -> List[File]:
        """
        Lists files in the context base with various filtering, sorting, and pagination options.

        Parameters
        ----------
        skip : int, optional
            The number of files to skip (default is 0).
        limit : int, optional
            The maximum number of files to return (default is 20).
        sort : str, optional
            The field to sort by (default is "date_created").
            Reverse with "-date_created"

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
            },
        )
        return [
            File(**{field.name: file.get(field.name) for field in dataclasses.fields(File)}) for file in data["files"]
        ]

    def upload_files(
        self, file_paths: Union[list[str], list[Path]], metadata: Optional[dict] = None, max_chunk_size: int = 600
    ) -> None:
        """
        Uploads a file to the context.

        This method uploads a file specified by `file_path` to the context, optionally
        associating it with metadata.

        Parameters
        ----------
        file_paths : Union[str, Path]
            The paths to the files to be uploaded. Can be a strings or a Path objects.
        metadata : Optional[dict], optional
            A dictionary containing metadata for the file. The keys "file_name",
            "user_id", "file_path", and "file_id" are reserved and cannot be used.
            If provided, it should not contain any of these keys. The default is None, which means
            no metadata will be associated with the files.

        max_chunk_size : int, optional
            The maximum size of the resulting chunks in words


        Raises
        ------
        ValueError
            If any reserved keys are present in the metadata.
            If the file type is not supported (not in SUPPORTED_FILE_TYPES).

        """
        if metadata is not None:
            if any(key in metadata.keys() for key in ["file_name", "user_id", "file_path", "file_id"]):
                msg = '"file_name", "user_id", "file_path", and "file_id" are reserved keys in metadata. Please try another key value!'
                raise ValueError(msg)
            metadata_json = json.dumps(metadata)
        else:
            metadata_json = None

        files_to_upload = []

        for _file_path in file_paths:
            file_path = Path(_file_path)

            if not file_path.exists():
                raise ValueError(f"The file at {file_path} does not exist.")

            suffix = file_path.suffix

            if suffix not in SUPPORTED_FILE_TYPES:
                msg = f"{suffix} files are not supported. Supported file types: {SUPPORTED_FILE_TYPES}"
                raise ValueError(msg)

            file_path = file_path.expanduser().resolve()

            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"
            files_to_upload.append(("files", (file_path.name, file_path.read_bytes(), mime_type)))

        data = {"context_name": self.name, "max_chunk_size": max_chunk_size, "metadata_json": metadata_json}

        self._client.post(self._urls.context_upload(), data=data, files=files_to_upload)

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

        Raises
        ------
        ValueError
            If the provided directory is not an actual directory or no valid files are found

        """
        directory = Path(directory).expanduser().resolve()

        if not directory.is_dir():
            msg = "You must provide a direcotry"
            raise ValueError(msg)
        directory = str(directory)

        all_files = [os.path.join(dp, f) for dp, _, filenames in os.walk(directory) for f in filenames]

        files_to_upload = [file for file in all_files if file.endswith(SUPPORTED_FILE_TYPES)]

        if not files_to_upload:
            raise ValueError("No supported files found")

        metadata = metadata or {}

        self.upload_files(files_to_upload, metadata, max_chunk_size=max_chunk_size)

    def query(
        self,
        query: str,
        top_k: int = 10,
        *,
        semantic_weight: float = 0.5,
        full_text_weight: float = 0.5,
        rrf_k: int = 60,
        include_embedding: bool = False,
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

        return self._post_query(params)

    def _post_query(self, params: Dict[str, Any]) -> List[Chunk]:
        results = self._client.post(self._urls.context_query(), json=params)
        return [Chunk(**chunk) for chunk in results["data"]]
