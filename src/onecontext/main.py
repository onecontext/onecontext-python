import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from onecontext.client import URLS, ApiClient, ConfigurationError
from onecontext.index import VectorIndex
from onecontext.knowledgebase import KnowledgeBase
from onecontext.pipeline import Pipeline


class OneContext:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
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
            Can be overridden with the environment variable 'ONECONTEXT_API_KEY'

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

        if base_url is None:
            base_url = os.environ.get("ONECONTEXT_BASE_URL")

        base_url = base_url or "https://api.onecontext.ai/v1/"

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

    def list_knowledgebases(self) -> List[KnowledgeBase]:
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

    def evaluate(
        self,
        dataset: list[dict],
        pipeline_yaml: str,
        target_metadata_key: str,
        override_args_map: Dict[str, list[str]],
        lables_column: str = "labels",
        eval_run_metadata: Optional[Dict] = None,
    ):
        """
        Evaluates a dataset using the specified pipeline and additional arguments.

        Parameters
        ----------
        dataset : list[dict]
            A list of dictionaries, each representing a record in the dataset to be evaluated.
        pipeline_yaml : str
            The pipeline yaml conifg for the pipeline to be evaluated.
        target_metadata_key : str
            The key in the chunk metadata to be used as the target for the evaluation.
            The predicted labels will be extracted from each retreived chunk
            using this metadata key.
        override_args_map : Dict[str, list[str]]
            A mapping from columns / keys present in the dataset to pipeline step arguments to be overridden for each record.
            eg. `{"Question" : ["query_embedder.query", "reranker.query"]} will fill the query arguments for the
            query embedder and reranker steps with the value from the "Question" column for each record in the dataset.
        labels_column : str, optional
            The name of the column in the dataset that contains the target labels
            for relevant chunks, by default "labels".
            These labels will be used to compute metrics against the target_metdata key.
        eval_run_metadata : Optional[Dict], optional
            Additional metadata to be included with the evaluation run, by default None.

        Returns
        -------
        The eval run id

        """
        eval_run_metadata = eval_run_metadata or {}

        data = {
            "dataset": dataset,
            "pipeline_yaml": pipeline_yaml,
            "override_args_map": override_args_map,
            "labels_column": lables_column,
            "target_metadata_key": target_metadata_key,
            "eval_run_metadata": eval_run_metadata,
        }

        return self._client.post(self._urls.evaluation(), json=data)

    def get_evaluation_results(
        self,
        eval_run_id: str,
    ):
        return self._client.get(self._urls.evaluation(eval_run_id))

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

        valid_status = ["RUNNING", "SUCCESSFUL", "FAILED", None]

        if status not in valid_status:
            err_msg = f"status must be one of {valid_status}"
            raise ValueError(err_msg)

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

    def create_vector_index(self, name: str, model: str) -> VectorIndex:
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
        >>> index = oc.create_vector_index('my_index', 'BAAI/bge-base-en-v1.5')

        """
        data = {"name": name, "model_name": model}
        create_response: Dict[str, Any] = self._client.post(self._urls.index(), json=data)
        return VectorIndex(**create_response, _client=self._client, _urls=self._urls)

    def delete_vector_index(self, name: str) -> None:
        """
        Delete a vecctor index base by its name.

        Parameters
        ----------
        name : str
            The name of the vector index to delete.

        Returns
        -------
        None
        """
        self._client.delete(self._urls.index(name))

    def list_vector_indexes(self):
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

    def set_openai_key(self, openai_api_key: str) -> None:
        """
        Submit your OpenAI API key to OneContext

        OneContext encrypts your key with a symmetric Google KMS key
        and only the ciphertext is stored on our servers.

        You can learn more about symmetric Google KMS encryption here:
        https://cloud.google.com/kms/docs/encrypt-decrypt

        Parameters
        ----------
        openai_api_key : str
            The OpenAI API key to be used by the client.
        """
        data = openai_api_key
        self._client.post(self._urls.submit_openai_key(), json=data)
