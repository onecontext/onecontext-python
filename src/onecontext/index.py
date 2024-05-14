from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from onecontext.client import URLS, ApiClient


@dataclass
class VectorIndex:
    name: str
    _client: ApiClient = field(repr=False)
    _urls: URLS = field(repr=False)
    model_name: Jank

    def list_files(self) -> List[Dict[str, Any]]:
        return self._client.get(self._urls.index_files(self.name))
