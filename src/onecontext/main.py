from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
from onecontext.index import VectorIndex
from onecontext.client import URLS, ApiClient, ConfigurationError
from onecontext.knowledgebase import KnowledgeBase
from onecontext.pipeline import Pipeline


class OneContext:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.onecontext.ai/v1/"):
        if api_key is None:
            api_key = os.environ.get("ONECONTEXT_API_KEY")
        if api_key is None:
            msg = (
                "No API key detected. Please pass the api_key directly or "
                "set the 'ONECONTEXT_API_KEY' environment variable."
            )
            raise ConfigurationError(msg)
        self._client = ApiClient(api_key)
        self._urls = URLS(base_url)

    def create_knowledgebase(self, name: str):
        data = {"name": name}
        self._client.post(self._urls.knowledge_base(), json=data)
        return KnowledgeBase(name, self._client, self._urls)

    def delete_knowledgebase(self, name: str) -> None:
        self._client.delete(self._urls.knowledge_base(name))

    def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """List the available Knowledge Bases"""
        knowledge_base_dicts: Dict = self._client.get(self._urls.knowledge_base())
        return [KnowledgeBase(**kb, _client=self._client, _urls=self._urls) for kb in knowledge_base_dicts]

    def KnowledgeBase(self, name: str) -> KnowledgeBase:
        return KnowledgeBase(name, self._client, self._urls)

    def deploy_pipeline(self, name: str, pipeline_yaml_path: Union[Path, str]) -> Pipeline:
        path = Path(pipeline_yaml_path)

        if path.suffix not in {".yaml", ".yml"}:
            msg = "Expected a yaml file"
            raise ValueError(msg)

        yaml_config = path.read_text()
        data = {"name": name, "yaml_config": yaml_config}
        create_response = self._client.post(self._urls.pipeline(), json=data)

        return Pipeline(**create_response, _client=self._client, _urls=self._urls)

    def delete_pipeline(self, name: str) -> None:
        self._client.delete(self._urls.pipeline(name))

    def list_pipelines(self) -> List[Pipeline]:
        pipelines = self._client.get(self._urls.pipeline())
        return [Pipeline(**pipe, _client=self._client, _urls=self._urls) for pipe in pipelines]

    def list_runs(
        self,
        *,
        status=None,
        run_id=None,
        skip=0,
        limit=20,
        sort="date_created",
        date_created_gte=None,
        date_created_lte=None,
    ) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = self._client.get(
            self._urls.run_results(),
            params={
                "skip": skip,
                "limit": limit,
                "date_created_gte": date_created_gte,
                "date_created_lte": date_created_lte,
                "sort": sort,
                "run_id": run_id,
                "status": status,
            },
        )
        return runs

    def Pipeline(self, name: str, yaml_config=None) -> Pipeline:
        return Pipeline(name=name, yaml_config=yaml_config, _client=self._client, _urls=self._urls)

    def create_index(self, name: str, model: str) -> VectorIndex:
        data = {"name": name, "model_name": model}
        create_response: Dict[str, Any] = self._client.post(self._urls.index(), json=data)
        return VectorIndex(**create_response, _client=self._client, _urls=self._urls)

    def list_indexes(self):
        create_response = self._client.get(self._urls.index())
        return [VectorIndex(**index, _client=self._client, _urls=self._urls) for index in create_response]

    def VectorIndex(self, name: str, model_name: Optional[str] = None) -> VectorIndex:
        return VectorIndex(name, model_name=model_name, _client=self._client, _urls=self._urls)
