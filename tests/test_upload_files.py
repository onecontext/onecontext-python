import os
import tempfile

import pytest
import requests
from utils import wait_for_file_processing

from onecontext.context import Context
from onecontext.main import OneContext


@pytest.fixture
def context(client: OneContext):
    context_name = "test_context_"
    current_file_name = os.path.splitext(os.path.basename(__file__))[0]
    context_name += "-" + current_file_name
    context = client.create_context(context_name)
    yield context
    client.delete_context(context_name)


def test_upload_files(context: Context, file_paths: list):
    context.upload_files(file_paths)
    wait_for_file_processing(context)
    files = context.list_files()
    assert len(files) == 2
