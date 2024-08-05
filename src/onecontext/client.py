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

    def submit_run(self) -> str:
        return self._join_base("submit-run")

    def run(self) -> str:
        return self._join_base("run")

    def upload(self) -> str:
        return self._join_base("upload")

    def upload_urls(self) -> str:
        return self._join_base("yt_urls")

    def knowledge_base(self, knowledge_base_name: Optional[str] = None) -> str:
        return self._join_base(f"knowledgebase/{knowledge_base_name}" if knowledge_base_name else "knowledgebase")

    def index(self, index: Optional[str] = None) -> str:
        return self._join_base(f"index/{index}" if index else "index")

    def files(self) -> str:
        return self._join_base("files")

    def delete_duplicate_files(self) -> str:
        return self._join_base("delete_duplicate_files")

    def chunks(self) -> str:
        return self._join_base("chunks")

    def pipeline(self, pipeline_name: Optional[str] = None) -> str:
        return self._join_base(f"pipeline/{pipeline_name}" if pipeline_name else "pipeline")

    def run_results(self):
        return self._join_base("run_results/")

    def submit_openai_key(self):
        return self._join_base("submit_openai_key")

    def evaluation(self, eval_run_id: Optional[str] = None):
        return self._join_base(f"evaluation/{eval_run_id}" if eval_run_id else "evaluation")

    def context_run_results(self) -> str:
        return self._join_base("context/run_results")

    def context_delete_duplicate_files(self) -> str:
        return self._join_base("context/delete_duplicate_files")

    def context_files(self) -> str:
        return self._join_base("context/files")

    def context_chunks(self) -> str:
        return self._join_base("context/chunks")

    def context(self) -> str:
        return self._join_base("context")

    def context_upload(self) -> str:
        return self._join_base("context/upload")

    def context_query(self) -> str:
        return self._join_base("context/query")


class ApiClient:
    def __init__(self, api_key: str) -> None:
        self.session = requests.Session()
        self.api_key = api_key
        self.session.headers.update(self._auth_headers)

    @property
    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _handle_response(self, response: requests.Response):
        try:
            response_json = response.json()
        except ValueError:
            response_json = {}

        if not response.ok:
            error_msg = response_json.get("detail", [])
            if error_msg:
                msg = f"{response.status_code}: {error_msg}"
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
