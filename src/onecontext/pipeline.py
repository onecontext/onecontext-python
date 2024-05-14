from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from onecontext.client import URLS, ApiClient


@dataclass
class Chunk:
    id: str
    content: str
    metadata_json: Optional[dict] = None
    file_name: str | None = None


@dataclass
class Pipeline:
    name: str
    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)
    id: Optional[str] = None
    yaml_config: Optional[str] = None
    run_results: Optional[str] = None
    run_id: Optional[str] = None

    def get_info(self) -> None:
        info = self._client.get(self._urls.pipeline(self.name))
        self.sync_status = info["sync_status"]
        self.id = info["id"]

    def run(
        self,
        override_args: dict[str, Any] | None = None,
    ) -> List[Chunk]:
        override_args = override_args or {}

        params = {"pipeline_name": self.name, "override_args": override_args}

        return self._post_query(params)

    def _post_query(self, params: Dict[str, Any]) -> List[Chunk]:
        results = self._client.post(self._urls.run(), json=params)
        return [Chunk(**document) for document in results["chunks"]]
