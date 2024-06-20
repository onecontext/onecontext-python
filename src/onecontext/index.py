from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from onecontext.chunk import Chunk
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

    def list_chunks(
        self, file_names=None, file_ids=None,
        chunk_ids=None, skip=0, limit=200, sort="date_created", metadata_filters=None,
        date_created_gte=None, date_created_lte=None
    ) -> List[Dict[str, Any]]:
        """
        Lists chunks in the knowledge base with various filtering, sorting, and pagination options.

        Parameters
        ----------
        file_names : list[str], optional
            A list of names of the files to filter results (default is None).
        file_ids : list[str], optional
            A list of IDs of the files to filter results (default is None).
        chunk_ids : list[str], optional
            A list of IDs of the chunks to filter results (default is None).
        skip : int, optional
            The number of chunks to skip (default is 0).
        limit : int, optional
            The maximum number of chunks to return (default is 200).
        sort : str, optional
            The field to sort by (default is "date_created").
            Reverse with "-date_created"
        metadata_filters : dict, optional
            A dictionary of metadata fields to filter results (default is None).
        date_created_gte : datetime, optional
            The minimum creation date of chunks to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"
        date_created_lte : datetime, optional
            The maximum creation date of chunks to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"

        Returns
        -------
        List[Chunk]
            A list of Chunk objects that are the result of running the query

        """
        results = self._client.post(
            self._urls.chunks(),
            json={
                "vector_index_names": [self.name],
                "file_names": file_names,
                "file_ids": file_ids,
                "chunk_ids": chunk_ids,
                "skip": skip,
                "limit": limit,
                "sort": sort,
                "metadata_json": metadata_filters,
                "date_created_gte": date_created_gte,
                "date_created_lte": date_created_lte,
            },
        )

        return [Chunk(**document) for document in results]

    def list_files(
        self, skip=0, limit=500, sort="date_created", metadata_filters=None, date_created_gte=None, date_created_lte=None
    ) -> List[Dict[str, Any]]:
        """
        Lists files associated to the chunks in the vecotr index.

        Parameters
        ----------
        skip : int, optional
            The number of files to skip (default is 0).
        limit : int, optional
            The maximum number of files to return (default is 20).
        sort : str, optional
            The field to sort by (default is "date_created").
            Reverse with "-date_created"
        metadata_filters : dict, optional
            A dictionary of metadata fields to filter results (default is None).
        date_created_gte : datetime, optional
            The minimum creation date of files to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"
        date_created_lte : datetime, optional
            The maximum creation date of files to list (default is None).
            ISO 8601 Date Format Example: "2023-01-20T13:01:02Z"

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries, each representing a file with its metadata.

        """
        files: List[Dict[str, Any]] = self._client.post(
            self._urls.files(),
            json={
                "vector_index_names": [self.name],
                "skip": skip,
                "limit": limit,
                "date_created_gte": date_created_gte,
                "date_created_lte": date_created_lte,
                "metadata_json": metadata_filters,
                "sort": sort,
            },
        )
        return files

