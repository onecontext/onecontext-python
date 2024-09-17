import os

import pytest
from utils import wait_for_file_processing

from onecontext.context import Context
from onecontext.main import OneContext


@pytest.fixture
def context(client: OneContext):
    context_name = "test_context"
    current_file_name = os.path.splitext(os.path.basename(__file__))[0]
    context_name += "_" + current_file_name
    context = client.create_context(context_name)
    yield context
    client.delete_context(context_name)


@pytest.fixture
def context_with_files(context: Context, file_paths: list):
    metadata = [{"file_tag": "file_1"}, {"file_tag": "file_2"}]
    context.upload_files(file_paths, metadata=metadata)
    wait_for_file_processing(context)
    yield context
    files = context.list_files()
    assert len(files) > 0


def test_list_chunks(context_with_files: Context):
    files = context_with_files.list_files()

    file_ids = [file.id for file in files]

    chunks_no_filters = context_with_files.list_chunks(limit=100)
    assert all(chunk.file_id in file_ids for chunk in chunks_no_filters)

    specific_chunks_list = context_with_files.list_chunks(file_id=file_ids[0], limit=100)
    assert all(chunk.file_id == file_ids[0] for chunk in specific_chunks_list)

    metadata_filters = {"file_tag": {"$eq": "file_1"}}

    chunks_metadata_filtered = context_with_files.list_chunks(metadata_filters=metadata_filters, limit=100)

    for chunk in chunks_metadata_filtered:
        assert chunk.metadata_json
        assert chunk.metadata_json.get("file_tag") == "file_1":

@pytest.mark.parametrize(
    "query, metadata_filters, expected_count",
    [
        ("sample query", None, 10),
        ("sample query", {"file_tag": {"$eq": "file_1"}}, 10),
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
            assert chunk.metadata_json.get("file_tag") == file_tag
