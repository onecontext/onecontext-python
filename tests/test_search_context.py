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
    context.upload_files(file_paths)
    wait_for_file_processing(context)
    yield context
    files = context.list_files()
    assert len(files) > 0


def test_query(context_with_files: Context):
    chunks = context_with_files.query("sample query", top_k=10)
    assert len(chunks) == 10
