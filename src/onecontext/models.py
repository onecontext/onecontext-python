from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class Chunk:
    """
    A chunk of a file, stored in a vector index

    Attributes
    ----------
    id : str
        A unique identifier for the chunk.
    content : str
        The content of the chunk.
    user_id : str
        The identifier of the user associated with the chunk.
    file_id : str
        The identifier of the file associated with the chunk.
    context_id : str
        The identifier of the context associated with the chunk.
    metadata_json : Optional[Dict], optional
        A dictionary containing metadata about the chunk.
    date_created : Optional[datetime], optional
        The creation date and time of the chunk.
    file_name : Optional[str], optional
        The name of the file associated with the chunk.
    embedding : Optional[List[float]], optional
        The vector embedding representing the semantic content of the chunk.
    semantic_score : Optional[float], optional
        A score representing the semantic relevance of the chunk.
    fulltext_score : Optional[float], optional
        A score representing the full-text search relevance of the chunk.
    combined_score : Optional[float], optional
        A combined score of semantic and full-text search relevance.
    """

    id: str
    content: str
    user_id: str
    file_id: str
    context_id: str
    metadata_json: Optional[Dict] = None
    date_created: Optional[datetime] = None
    file_name: Optional[str] = None
    embedding: Optional[List[float]] = None
    semantic_score: Optional[float] = None
    fulltext_score: Optional[float] = None
    combined_score: Optional[float] = None
    context_name: Optional[str] = None


@dataclass
class File:
    """
    A file associated with a user and a context.

    Attributes
    ----------
    id : str
        A unique identifier for the file.
    user_id : str
        The identifier of the user who owns the file.
    path : str
        The file system path where the file is located.
    context_name : str
        The name of the context associated with the file.
    name : str
        The name of the file.
    status : str
        The status of the file, indicating its current state or processing status.
    context_id : str
        The identifier of the context associated with the file.
    metadata_json : Optional[Dict], optional
        A dictionary containing metadata about the file.
    """

    id: str
    user_id: str
    path: str
    context_name: str
    name: str
    status: str
    context_id: str
    date_created: str
    metadata_json: Optional[Dict] = None
    download_url: Optional[str] = None


@runtime_checkable
class PydanticV2BaseModel(Protocol):
    def model_json_schema(*args, **kwargs) -> Dict[str, Any]: ...