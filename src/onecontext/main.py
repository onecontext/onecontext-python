from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
import os
from onecontext.index import VectorIndex
from onecontext.client import URLS, ApiClient, ConfigurationError
from onecontext.knowledgebase import KnowledgeBase
from onecontext.pipeline import Pipeline


class OneContext:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.onecontext.ai/v1/"):
        """
        Initialize the OneContext client with an API key and base URL.

        Parameters
        ----------
        api_key : Optional[str], optional
            The API key for authenticating requests to the OneContext API.
            If not provided, the environment variable 'ONECONTEXT_API_KEY'
            will be used. Defaults to None.
        base_url : str, optional
            The base URL for the OneContext API. Defaults to "https://api.onecontext.ai/v1/".

        Raises
        ------
        ConfigurationError
            If no API key is provided and 'ONECONTEXT_API_KEY' environment
            variable is not set, a ConfigurationError is raised.

        """
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

    def create_knowledgebase(self, name: str) -> KnowledgeBase:
        """
        Create a new knowledge base with the given name.

        Parameters
        ----------
        name : str
            The name for the new knowledge base.

        Returns
        -------
        KnowledgeBase
            An instance of the KnowledgeBase class initialized with the given name.

        """
        data = {"name": name}
        self._client.post(self._urls.knowledge_base(), json=data)
        return KnowledgeBase(name, self._client, self._urls)

    def delete_knowledgebase(self, name: str) -> None:
        """
        Delete a knowledge base by its name.

        Parameters
        ----------
        name : str
            The name of the knowledge base to delete.

        Returns
        -------
        None
        """
        self._client.delete(self._urls.knowledge_base(name))

    def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """
        List the available Knowledge Bases.

        This method fetches a list of knowledge base dictionaries from the API and
        instantiates a list of KnowledgeBase objects with the provided information.

        Returns
        -------
        List[KnowledgeBase]
            A list of KnowledgeBase objects representing the available knowledge bases.

        """
        knowledge_base_dicts: Dict = self._client.get(self._urls.knowledge_base())
        return [KnowledgeBase(**kb, _client=self._client, _urls=self._urls) for kb in knowledge_base_dicts]

    def KnowledgeBase(self, name: str) -> KnowledgeBase:
        """
        Factory method to create a KnowledgeBase object with the given name.

        Parameters
        ----------
        name : str
            The name of the knowledge base to create.

        Returns
        -------
        KnowledgeBase
            An instance of KnowledgeBase associated with the provided name and the current client context.

        See Also
        --------
        KnowledgeBase : The KnowledgeBase class that this method constructs instances of.

        """
        return KnowledgeBase(name, self._client, self._urls)

    def deploy_pipeline(
        self, name: str, pipeline_yaml_path: Optional[Union[Path, str]] = None, pipeline_yaml: Optional[str] = None
    ) -> Pipeline:
        """
        Deploys a pipeline based on the provided YAML configuration.

        Parameters
        ----------
        name : str
            The name of the pipeline to be deployed.

        pipeline_yaml_path : Optional[Union[Path, str]]
            The file path to the pipeline YAML configuration. It can be a string or a Path object.
            Provide pipeline_yaml_path or pipeline_yaml, not both.

        pipeline_yaml : Optional[str]
            The pipeline YAML configuration.
            Provide pipeline_yaml_path or pipeline_yaml, not both.

        Returns
        -------
        Pipeline
            An instance of the deployed Pipeline.

        Raises
        ------
        ValueError
            If the provided file path does not have a .yaml or .yml extension.

        """
        if pipeline_yaml_path is not None and pipeline_yaml is not None:
            raise ValueError("Provide pipeline_yaml_path or pipeline_yaml, not both.")

        if pipeline_yaml_path is not None:
            path = Path(pipeline_yaml_path)

            if path.suffix not in {".yaml", ".yml"}:
                msg = "Expected a yaml file"
                raise ValueError(msg)

            yaml_config = path.read_text()

        elif pipeline_yaml is not None:
            yaml_config = pipeline_yaml

        else:
            raise ValueError("Provide pipeline_yaml_path or pipeline_yaml")

        data = {"name": name, "yaml_config": yaml_config}
        create_response = self._client.post(self._urls.pipeline(), json=data)

        return Pipeline(**create_response, _client=self._client, _urls=self._urls)

    def delete_pipeline(self, name: str) -> None:
        """
        Deletes a pipeline by name.

        Parameters
        ----------
        name : str
            The name of the pipeline to delete.

        Returns
        -------
        None
        """
        self._client.delete(self._urls.pipeline(name))

    def list_pipelines(self) -> List[Pipeline]:
        """
        Retrieve a list of Pipeline objects from the API.

        Returns
        -------
        List[Pipeline]
            A list of Pipeline objects.

        """
        pipelines = self._client.get(self._urls.pipeline())
        return [Pipeline(**pipe, _client=self._client, _urls=self._urls) for pipe in pipelines]

    def list_runs(
        self,
        *,
        status: Optional[Literal["RUNNING", "SUCCESSFUL", "FAILED"]] = None,
        run_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort: str = "date_created",
        date_created_gte: Optional[str] = None,
        date_created_lte: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve a list of runs with optional filtering and sorting.

        Parameters
        ----------
        status : str, optional
            The status of the runs to filter by.
        run_id : str, optional
            The unique identifier for a run to filter by.
        skip : int, optional
            The number of items to skip (for pagination), default is 0.
        limit : int, optional
            The maximum number of items to return, default is 20.
        sort : str, optional
            The field to sort the results by, default is 'date_created'.
            You can inverte the sort like so '-date_created'
        date_created_gte : str, optional
            The minimum creation date to filter by (greater than or equal to).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"
        date_created_lte : str, optional
            The maximum creation date to filter by (less than or equal to).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the run information.

        """
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

    def Pipeline(self, name: str) -> Pipeline:
        """
        Create a new Pipeline object with a specified name.

        Use this to access existing pipelines.

        Parameters
        ----------
        name : str
            The name of the pipeline to create.

        Returns
        -------
        Pipeline
            An instance of the Pipeline class initialized with the given name.

        """
        return Pipeline(name=name, _client=self._client, _urls=self._urls)

    def create_index(self, name: str, model: str) -> VectorIndex:
        """
        Creates a new vector index with the specified name and model.

        Parameters
        ----------
        name : str
            The name of the index to be created.
        model : str
            The name of the model to use for the index.

        Returns
        -------
        VectorIndex
            An instance of `VectorIndex` with the response data.


        Examples
        --------
        >>> oc = OneContextContext(...)
        >>> index = oc.create_index('my_index', 'BAAI/bge-base-en-v1.5')

        """
        data = {"name": name, "model_name": model}
        create_response: Dict[str, Any] = self._client.post(self._urls.index(), json=data)
        return VectorIndex(**create_response, _client=self._client, _urls=self._urls)

    def list_indexes(self):
        """
        Retrieve a list of VectorIndex objects from teh API.

        Returns
        -------
        list of VectorIndex
            A list of VectorIndex objects, each initialized with the index data
            and the reference to the current client and urls objects.

        """
        response = self._client.get(self._urls.index())
        return [VectorIndex(**index, _client=self._client, _urls=self._urls) for index in response]

    def VectorIndex(self, name: str, model_name: Optional[str] = None) -> VectorIndex:
        """
        Create a new instance of VectorIndex with the specified name and model name.

        Parameters
        ----------
        name : str
            The name of the VectorIndex.
        model_name : Optional[str], optional
            The name of the model associated with the VectorIndex, by default None.

        Returns
        -------
        VectorIndex
            An instance of VectorIndex with the given configuration.
        """
        return VectorIndex(name, model_name=model_name, _client=self._client, _urls=self._urls)
