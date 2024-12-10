import os
from typing import List

import pytest
from helpers.utils import wait_for_file_processing
from pydantic import BaseModel, Field

from onecontext.context import Context, StructuredOutputModel
from onecontext.main import OneContext


@pytest.fixture
def context(client: OneContext):
    context_name = f"test_context_{__name__}"

    try:
        context = client.create_context(context_name)
        yield context

    finally:
        client.delete_context(context_name)


@pytest.fixture
def context_with_files(context: Context, file_paths: list):
    metadata = [{"file_tag": "file_1"}, {"file_tag": "file_2"}]
    context.upload_files(file_paths, metadata=metadata, max_chunk_size=200)
    wait_for_file_processing(context)
    yield context
    files = context.list_files()
    assert len(files) > 0


def test_list_files(context_with_files: Context):
    metadata_filters = {"file_tag": {"$eq": "file_1"}}
    files = context_with_files.list_files(metadata_filters=metadata_filters)

    for file in files:
        assert file.metadata_json
        assert file.metadata_json.get("file_tag") == "file_1"

    metadata_filters = {"file_tag": {"$eq": "file_2"}}
    files = context_with_files.list_files(metadata_filters=metadata_filters)

    for file in files:
        assert file.metadata_json
        assert file.metadata_json.get("file_tag") == "file_2"


def test_list_chunks(context_with_files: Context):
    files = context_with_files.list_files()

    file_ids = [file.id for file in files]

    chunks_no_filters = context_with_files.list_chunks(limit=100)

    assert all(chunk.file_id in file_ids for chunk in chunks_no_filters)

    with_chunk_ids = context_with_files.get_chunks_by_ids([chunk.id for chunk in chunks_no_filters])

    assert {chunk.id for chunk in with_chunk_ids} == {chunk.id for chunk in chunks_no_filters}

    specific_chunks_list = context_with_files.list_chunks(file_id=file_ids[0], limit=100)

    all_content = "\n".join([c.content for c in specific_chunks_list])

    assert all(chunk.file_id == file_ids[0] for chunk in specific_chunks_list)

    metadata_filters = {"file_tag": {"$eq": "file_1"}}

    chunks_metadata_filtered_1 = context_with_files.list_chunks(metadata_filters=metadata_filters, limit=100)

    assert chunks_metadata_filtered_1

    for chunk in chunks_metadata_filtered_1:
        assert chunk.metadata_json
        assert chunk.metadata_json.get("file_tag") == "file_1"

    metadata_filters = {"file_tag": {"$eq": "file_2"}}

    chunks_metadata_filtered_2 = context_with_files.list_chunks(metadata_filters=metadata_filters, limit=100)

    assert chunks_metadata_filtered_2
    for chunk in chunks_metadata_filtered_2:
        assert chunk.metadata_json
        assert chunk.metadata_json.get("file_tag") == "file_2"


@pytest.mark.parametrize(
    "query, metadata_filters, expected_count",
    [
        ("sample query", None, 10),
        ("sample query", {"file_tag": {"$eq": "file_1"}}, 7),
        ("sample query", {"file_tag": {"$eq": "file_2"}}, 10),
        ("sample query", {"file_tag": {"$eq": "nonexistent_tag"}}, 0),
    ],
)
def test_search_chunks_parametrized(
    context_with_files: Context, query: str, metadata_filters: dict, expected_count: int
):
    chunks = context_with_files.search(query, top_k=10, metadata_filters=metadata_filters)
    assert len(chunks) == expected_count

    if metadata_filters:
        file_tag = metadata_filters["file_tag"]["$eq"]
        for chunk in chunks:
            assert chunk.metadata_json
            assert chunk.metadata_json.get("file_tag") == file_tag


@pytest.mark.parametrize(
    "query, metadata_filters, expected_count, model",
    [
        ("sample query", None, 10, "gpt-4o-mini"),
        ("sample query", None, 10, "claude-35"),
    ],
)
def test_extract(
    context_with_files: Context, query: str, metadata_filters: dict, expected_count: int, model: StructuredOutputModel
):
    class PaperInfo(BaseModel):
        topics: List[str] = Field(description="the topics of the paper")

    output, chunks = context_with_files.extract_from_search(
        schema=PaperInfo,
        extraction_prompt="OUTPUT only json",
        query=query,
        top_k=10,
        metadata_filters=metadata_filters,
        model=model,
        temperature=0,
    )

    assert len(chunks) == expected_count

    PaperInfo.model_validate(output)

    output, chunks = context_with_files.extract_from_chunks(
        schema=PaperInfo, extraction_prompt="OUTPUT only json", model=model, temperature=0
    )

    PaperInfo.model_validate(output)

    if metadata_filters:
        file_tag = metadata_filters["file_tag"]["$eq"]
        for chunk in chunks:
            assert chunk.metadata_json
            assert chunk.metadata_json.get("file_tag") == file_tag
