import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from onecontext.client import URLS, ApiClient, ApiError, ConfigurationError
from onecontext.context import Context


class OneContext:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        open_ai_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the OneContext client with an API key and base URL.

        Parameters
        ----------
        api_key : Optional[str], optional
            The API key for authenticating requests to the OneContext API.
            If not provided, the environment variable 'ONECONTEXT_API_KEY'
            will be used. Defaults to None.

        open_api_key : Optional[str], optional
            The OPEN AI API key for authenticating requests to the OPEN AI.

        base_url : str, optional
            The base URL for the OneContext API. Defaults to "https://app.onecontext.ai/v5/".
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

        extra_headers = extra_headers or {}

        if open_ai_key:
            extra_headers.update({"OPENAI-API-KEY": open_ai_key})

        base_url = base_url or "https://app.onecontext.ai/api/v5/"
        self._client = ApiClient(api_key, extra_headers=extra_headers)
        self._urls = URLS(base_url)

    def create_context(self, name: str) -> Context:
        """
        Create a new context with the given name.

        Parameters
        ----------
        name : str
            The name for the new knowledge base.

        Returns
        -------
        Context
            An instance of the Context class initialized with the given name.

        """
        data = {"contextName": name}
        response = self._client.post(self._urls.context(), json=data)
        return Context(**response, _client=self._client, _urls=self._urls)

    def delete_context(self, name: str) -> None:
        self._client.delete(self._urls.context(), json={"contextName": name})

    def list_contexts(self) -> List[Context]:
        """
        List the available Contexts

        This method fetches a list of contexts from the API.

        Returns
        -------
        List[Context]
            A list of Context objects.

        """
        response = self._client.get(self._urls.context())

        return [Context(**ctxt, _client=self._client, _urls=self._urls) for ctxt in response["data"]]

    def Context(self, name: str) -> Context:
        contexts = self._client.get(self._urls.context(), params={"contextName": name}).get("data")
        if not contexts:
            raise ApiError(f"Context {name} not found")
        if len(contexts) > 1:
            raise RuntimeError("unreachable: please contact support!")
        context = contexts.pop()
        return Context(**context, _client=self._client, _urls=self._urls)
