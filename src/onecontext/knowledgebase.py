import io
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from onecontext.client import URLS, ApiClient

SUPPORTED_FILE_TYPES = (".pdf", ".docx", ".txt", ".md")


@dataclass
class KnowledgeBase:
    """
    A class representing a knowledge base client to interact with an API for file management.

    Attributes
    ----------
    name : str
        The name of the knowledge base.
    _client : ApiClient
        The API client to make requests to the knowledge base.
    _urls : URLS
        Object containing URL templates for API requests.
    id : Optional[str], optional
        The identifier for the knowledge base, by default None.
    """

    name: str
    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)
    id: Optional[str] = None

    def list_files(
        self,
        skip=0,
        limit=500,
        sort="date_created",
        metadata_filters=None,
        date_created_gte=None,
        date_created_lte=None,
    ) -> List[Dict[str, Any]]:
        """
        Lists files in the knowledge base with various filtering, sorting, and pagination options.

        Parameters
        ----------
        skip : int, optional
            The number of files to skip (default is 0).
        limit : int, optional
            The maximum number of files to return (default is 20).
        sort : str, optional
            The field to sort by (default is "date_created").
            Reverse with "-date_created"
        metadata_filters : dict, optional
            A dictionary of metadata fields to filter results (default is None).
        date_created_gte : datetime, optional
            The minimum creation date of files to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"
        date_created_lte : datetime, optional
            The maximum creation date of files to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries, each representing a file with its metadata.

        """
        files: List[Dict[str, Any]] = self._client.post(
            self._urls.files(),
            json={
                "knowledgebase_names": [self.name],
                "skip": skip,
                "limit": limit,
                "date_created_gte": date_created_gte,
                "date_created_lte": date_created_lte,
                "metadata_json": metadata_filters,
                "sort": sort,
            },
        )
        return files

    def delete_files(self, file_names: list[str]) -> None:
        """
        Deletes a list of files from the knowledge base.

        Parameters
        ----------
        file_names : list[str]
            A list of filenames as strings that are to be deleted.

        Returns
        -------
        None

        """
        self._client.delete(
            self._urls.files(),
            json={
                "file_names": file_names,
                "knowledgebase_names": [self.name],
            },
        )

    def upload_file(self, file_path: Union[str, Path], metadata: Optional[dict] = None) -> list[str]:
        """
        Uploads a file to the knowledge base.

        This method uploads a file specified by `file_path` to the knowledge base, optionally
        associating it with metadata.

        Parameters
        ----------
        file_path : Union[str, Path]
            The path to the file to be uploaded. Can be a string or a Path object.
        metadata : Optional[dict], optional
            A dictionary containing metadata for the file. The keys "file_name", "knowledge_base",
            "user_id", "file_path", and "file_id" are reserved and cannot be used.
            If provided, it should not contain any of these keys. The default is None, which means
            no metadata will be associated with the file.

        Returns
        -------
        list[str]
            A list of pipeline run IDs generated after the file is uploaded.

        Raises
        ------
        ValueError
            If any reserved keys are present in the metadata.
            If the file type is not supported (not in SUPPORTED_FILE_TYPES).

        """
        if metadata is not None:
            if any(
                key in metadata.keys() for key in ["file_name", "knowledge_base", "user_id", "file_path", "file_id"]
            ):
                msg = '"file_name", "knowledge_base", "user_id", "namespace", "file_path", and "file_id" are reserved keys in metadata. Please try another key value!'
                raise ValueError(msg)
            metadata_json = json.dumps(metadata)
        else:
            metadata_json = None

        file_path = Path(file_path)
        suffix = file_path.suffix

        if suffix not in SUPPORTED_FILE_TYPES:
            msg = f"{suffix} files are not supported. Supported file types: {SUPPORTED_FILE_TYPES}"
            raise ValueError(msg)

        file_path = file_path.expanduser().resolve()

        with open(file_path, "rb") as file:
            files = {"files": (str(file_path), file)}
            data = {"knowledgebase_name": self.name}
            if metadata_json:
                data.update({"metadata_json": metadata_json})

            run_ids = self._client.post(self._urls.upload(), data=data, files=files)
        return run_ids

    def upload_yt_urls(self, upload_urls: list[str]):
        data = {"knowledgebase_name": self.name, "urls": upload_urls}
        self._client.post(self._urls.upload_urls(), json=data)

    def upload_text(self, text: str, file_name: str, metadata: Optional[dict] = None) -> None:
        """
        Uploads a text string as a file to a knowledge base with optional metadata.

        Parameters
        ----------
        text : str
            The text content to be uploaded.
        file_name : str
            The name of the file to be created. If the provided file_name does not end with '.txt',
            it is automatically modified to end with this extension.
        metadata : dict, optional
            A dictionary containing metadata for the upload. There are reserved keys that
            cannot be used: 'file_name', 'knowledge_base', 'user_id',
            'file_path', and 'file_id'. If any of these keys are present, a ValueError is raised.

        Raises
        ------
        ValueError
            If any reserved key is present in the metadata dictionary.


        """
        if metadata is not None:
            if any(
                key in metadata.keys()
                for key in ["file_name", "knowledge_base", "user_id", "namespace", "file_path", "file_id"]
            ):
                msg = '"file_name", "knowledgebase_name", "user_id",, "file_path", and "file_id" are reserved keys in metadata. Please try another key value!'
                raise ValueError(msg)
            metadata_json = json.dumps(metadata)
        else:
            metadata_json = None

        file = io.StringIO(text)

        if not file_name.endswith(".txt"):
            file_name = file_name.split(".")[0]
            file_name += ".txt"

        files = {"files": (file_name, file)}
        data = {"knowledgebase_name": self.name}
        if metadata_json:
            data.update({"metadata_json": metadata_json})

        self._client.post(self._urls.upload(), data=data, files=files)
        file.close()

    def upload_from_directory(
        self, directory: Union[str, Path], metadata: Optional[Union[dict, List[dict]]] = None
    ) -> None:
        """
        Uploads files from a given directory to a knowledgebase.

        This method uploads all files within a specified directory that match the supported file types.

        Parameters
        ----------
        directory : Union[str, Path]
            The path to the directory containing the files to be uploaded. Can be a string or a Path object.
        metadata : Optional[Union[dict, List[dict]]], optional
            Metadata associated with the files to be uploaded. This can be a single dictionary applied to all files,
            or a list of dictionaries with one dictionary for each file. If a list is provided, its length must match
            the number of files. If omitted or `None`, no metadata will be applied.

        Raises
        ------
        ValueError
            If the provided directory is not an actual directory or if the length of the metadata list does not match
            the number of files to be uploaded.

        """
        directory = Path(directory).expanduser().resolve()

        if not directory.is_dir():
            msg = "You must provide a direcotry"
            raise ValueError(msg)
        directory = str(directory)
        all_files = [os.path.join(directory, file) for file in os.listdir(directory)]
        files_to_upload = [file for file in all_files if file.endswith(SUPPORTED_FILE_TYPES)]

        metadata = metadata or {}

        if isinstance(metadata, list):
            if len(metadata) != len(files_to_upload):
                msg = "Metadata list len does not match the number of files in directory"
                raise ValueError(msg)

        elif isinstance(metadata, dict):
            metadata = [metadata] * len(files_to_upload)
        else:
            raise ValueError("Invalid metadata object")

        for file_path, file_metadata in zip(files_to_upload, metadata):
            self.upload_file(file_path, file_metadata)
