import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests


class ApiError(Exception): ...


class ConfigurationError(Exception): ...


@dataclass
class URLS:
    base_url: str

    def _join_base(self, url: str) -> str:
        return urljoin(self.base_url, url)

    def submit_openai_key(self):
        return self._join_base("user/updateUserMeta")

    def context_files(self) -> str:
        return self._join_base("context/file")

    def context_files_download_url(self) -> str:
        return self._join_base("context/file/presigned-download-url/")

    def context_files_upload_url(self) -> str:
        return self._join_base("context/file/presigned-upload-url/")

    def context_files_upload_processed(self) -> str:
        return self._join_base("context/file/process-uploaded/")

    def context_chunks(self) -> str:
        return self._join_base("context/chunk/")
    
    def context_chunks_by_ids(self) -> str:
        return self._join_base("context/chunk/byids/")

    def context(self) -> str:
        return self._join_base("context")

    def context_upload(self) -> str:
        return self._join_base("context/file/upload")

    def context_search(self) -> str:
        return self._join_base("context/chunk/search")


class ApiClient:
    def __init__(self, api_key: str, extra_headers: Optional[Dict[str, Any]] = None) -> None:
        self.session = requests.Session()
        self.api_key = api_key
        self.session.headers.update(self._auth_headers)

        if extra_headers is not None:
            self.session.headers.update(extra_headers)

    @property
    def _auth_headers(self) -> Dict[str, str]:
        return {"API-KEY": f"{self.api_key}"}

    def _handle_response(self, response: requests.Response):
        try:
            response_json = response.json()
        except ValueError:
            response_json = {}

        if not response.ok:
            error_msg = response_json.get("error", [])
            message = response_json.get("message", "")

            if error_msg or message:
                user_message = f"{message} : {error_msg}"
                msg = f"{response.status_code}: {user_message}"
                raise ApiError(msg)
            else:
                response.raise_for_status()
        return response_json

    def get(self, endpoint: str, **kwargs: Any) -> Any:
        response = self.session.get(endpoint, **kwargs)
        return self._handle_response(response)

    def post(self, endpoint: str, **kwargs: Any) -> Any:
        response = self.session.post(endpoint, **kwargs)
        return self._handle_response(response)

    def delete(self, endpoint: str, **kwargs: Any) -> Any:
        response = self.session.delete(endpoint, **kwargs)
        return self._handle_response(response)
