from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import os
import io
from pathlib import Path
import json

from onecontext.client import URLS, ApiClient


SUPPORTED_FILE_TYPES = (".pdf", ".docx", ".txt", ".md")


@dataclass
class KnowledgeBase:
    """The KnowledgeBase class provides self._client access to a given knowledge base.
    knowledge bases names must unique.

    Args:
        name (str): The name of the knowledge base
        id (str): the id, this will be returned by the self._client
    """

    name: str
    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)
    id: Optional[str] = None

    def list_files(
        self, skip=0, limit=20, sort="date_created", metadata_filters=None, date_created_gte=None, date_created_lte=None
    ) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = self._client.post(
            self._urls.files(),
            json={
                "knowledgebase_name": self.name,
                "skip": skip,
                "limit": limit,
                "date_created_gte": date_created_gte,
                "date_created_lte": date_created_lte,
                "metadata_json": metadata_filters,
                "sort": sort,
            },
        )
        return files

    # %%

    # class FileQueryParams(BaseModel):
    #     knowledgebase_name: str
    #     skip: int = 0
    #     limit: int = 10
    #     sort: str = "date_created"
    #     metadata_json: dict | None = None
    #     date_created_gte: datetime | None = None
    #     date_created_lte: datetime | None = None

    # %%
    def delete_files(self, file_names: list[str]) -> None:
        self._client.delete(
            self._urls.knowledge_base_files(),
            params={"file_names": file_names},
        )

    def upload_urls(self, upload_urls: list[str]):
        data = {"knowledgebase_name": self.name, "self._urls": upload_urls}
        run_ids = self._client.post(self._urls.upload_urls(), json=data)
        return run_ids

    def upload_file(self, file_path: Union[str, Path], metadata: Optional[dict] = None) -> list[str]:
        if metadata is not None:
            if any(
                key in metadata.keys()
                for key in ["file_name", "knowledge_base", "user_id", "namespace", "file_path", "file_id"]
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

    def upload_text(self, text: str, file_name: str, metadata: Optional[dict] = None) -> None:
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
        data = {"pipeline_name": self.name}
        if metadata_json:
            data.update({"metadata_json": metadata_json})

        self._client.post(self._urls.upload(), data=data, files=files)
        file.close()

    def upload_from_directory(
        self, directory: Union[str, Path], metadata: Optional[Union[dict, List[dict]]] = None
    ) -> None:
        directory = Path(directory).expanduser().resolve()
        if not directory.is_dir():
            msg = "You must provide a direcotry"
            raise ValueError(msg)
        directory = str(directory)
        all_files = [os.path.join(directory, file) for file in os.listdir(directory)]
        files_to_upload = [file for file in all_files if file.endswith(SUPPORTED_FILE_TYPES)]

        if isinstance(metadata, list):
            if len(metadata) != len(files_to_upload):
                raise ValueError("Metadata list len does not match the number of files in directory")
        else:
            metadata = [metadata] * len(files_to_upload)

        for file_path, metadata in zip(files_to_upload, metadata):
            self.upload_file(file_path, metadata)
