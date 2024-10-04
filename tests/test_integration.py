import os

import pytest
from helpers.utils import wait_for_file_processing

from onecontext.context import Context
from onecontext.main import OneContext


@pytest.fixture
def context(client: OneContext):
    context_name = f"test_context_{__name__}"

    try:
        context = client.create_context(context_name)
        yield context

    finally:
        client.delete_context(context_name)


def test_integration(context: Context, test_files_directory: str):
    context.upload_from_directory(test_files_directory)
    wait_for_file_processing(context)
    files = context.list_files()
    assert len(files) == 3
    chunks = context.search("sample query", top_k=10)
    assert len(chunks) == 10
