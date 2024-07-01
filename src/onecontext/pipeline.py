from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from onecontext.client import URLS, ApiClient


@dataclass
class Chunk:
    """
    A chunk of a file, stored in a vector index

    Attributes
    ----------
    id : str
        A unique identifier for the chunk.
    content : str
        The actual content of the chunk.
    metadata_json : Optional[dict], optional
        A dictionary containing metadata about the chunk.
    file_name : str | None, optional
        The name of the file associated with the chunk.
    """

    id: str
    content: str
    metadata_json: Optional[dict] = None
    file_name: str | None = None
    date_created: str | None = None


@dataclass
class Pipeline:
    """
    A dataclass that represents a pipeline capable of interacting with an API client to perform various operations.

    Parameters
    ----------
    name : str
        The name of the pipeline.
    id : Optional[str], default=None
        The unique identifier of the pipeline.
    yaml_config : Optional[str], default=None
        The YAML configuration of the pipeline, if any.
    run_results : Optional[str], default=None
        The results of the pipeline run, if any.
    run_id : Optional[str], default=None
        The unique identifier of the run that is started when the pipeline is first deployed.
    _client : ApiClient
        An instance of ApiClient to make API calls. This parameter is hidden in the representation of the object.
    _urls : URLS
        An instance of URLS that contains the endpoint URLs required for API calls. This parameter is hidden in the representation of the object.
    """

    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)

    name: str
    id: Optional[str] = None
    yaml_config: Optional[str] = None
    run_id: Optional[str] = None

    def run(
        self,
        override_args: dict[str, Any] | None = None,
    ) -> List[Chunk]:
        """
        Runs the pipeline with optional override arguments.

        Parameters
        ----------
        override_args : dict[str, Any], optional
            A dictionary of step names and step_args to override the default pipeline arguments, by default None.

        Returns
        -------
        List[Chunk]
            A list of Chunk objects that are the result of running the pipeline with the specified parameters.


        Examples
        --------
        >>> query_pipeline = oc.Pipeline("basic_query")
        >>> query = "What are consequences of inventing a computer?"
        >>> retriever_top_k = 50
        >>> top_k = 5
        >>> override_args = {
        ...     "retriever": {
        ...         "top_k": retriever_top_k,
        ...         "query": query,
        ...     },
        ...     "reranker": {"top_k": top_k, "query": query},
        ... }
        >>> chunks = query_pipeline.run(override_args)

        """
        override_args = override_args or {}

        params = {"pipeline_name": self.name, "override_args": override_args}

        return self._post_query(params)

    def _post_query(self, params: Dict[str, Any]) -> List[Chunk]:
        results = self._client.post(self._urls.run(), json=params)
        return [Chunk(**document) for document in results["chunks"]]
