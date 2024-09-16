import os

import pytest

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


def test_list_files(context: Context, file_paths: list):
    context.upload_files(file_paths)
    files = context.list_files()
    assert len(files) == len(file_paths)
