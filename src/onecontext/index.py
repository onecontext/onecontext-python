from __future__ import annotations
from dataclasses import dataclass, field

from onecontext.client import URLS, ApiClient


@dataclass
class VectorIndex:
    """
    A dataclass that represents a vector index in the OneContext API.

    Parameters
    ----------
    name : str
        The name of the vector index.
    model_name : str
        The name of the model associated with this vector index.
    _client : ApiClient
        An instance of the ApiClient.
    _urls : URLS
        An instance of URLS containing the API endpoints.

    """

    name: str
    model_name: str
    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)
