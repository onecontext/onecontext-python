from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


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
    metadata_json: Optional[Dict] = None
    file_name: str | None = None
    date_created: datetime | None = None

