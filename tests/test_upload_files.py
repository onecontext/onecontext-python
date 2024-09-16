import os
import tempfile

import pytest
import requests
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


def download_file(file_url, local_path):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)


def test_upload_files(context: Context, file_paths: list):
    context.upload_files(file_paths)
    wait_for_file_processing(context)

    files = context.list_files(get_download_urls=True)
    assert len(files) == 2

    file_map = {f.name: f for f in files}

    for original_path in file_paths:
        local_filename = os.path.basename(original_path)
        file_to_download = file_map[local_filename]

        with tempfile.NamedTemporaryFile() as temp_file:
            download_file(file_to_download.download_url, temp_file.name)

            with open(original_path, "rb") as original:
                temp_file.seek(0)
                assert (
                    original.read() == temp_file.read()
                ), f"The downloaded file content for {local_filename} differs from the original."
