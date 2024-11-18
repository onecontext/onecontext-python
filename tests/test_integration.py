import os

import pytest
from helpers.utils import wait_for_file_processing

from onecontext.context import Context
from onecontext.main import OneContext


@pytest.fixture
def context(client: OneContext):
    context_name = "test_context"
    current_file_name = os.path.splitext(os.path.basename(__file__))[0]
    context_name += "_" + current_file_name

    try:
        context = client.create_context(context_name)
        yield context

    finally:
        client.delete_context(context_name)


def test_integration(context: Context, test_files_directory: str):
    file_ids = context.upload_from_directory(test_files_directory)
    wait_for_file_processing(context)
    files = context.list_files()
    assert {file.id for file in files} == set(file_ids)
    assert len(files) == 3
    chunks = context.search("sample query", top_k=10)
    assert len(chunks) == 10
