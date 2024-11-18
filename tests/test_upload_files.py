import os
import tempfile

import pytest
import requests
from helpers.utils import wait_for_file_processing

from onecontext.context import Context
from onecontext.main import OneContext


@pytest.fixture(scope="function")
def context(client: OneContext, request):
    context_name = f"test_context_{request.node.name}"
    try:
        client.delete_context(context_name)
        context = client.create_context(context_name)
        yield context
    finally:
        client.delete_context(context_name)


def download_file(file_url, local_path):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)


def test_upload_files(client: OneContext, context: Context, file_paths: list):
    metadata = [{"file_tag": "file_1"}, {"file_tag": "file_2"}]

    # file_paths = [file_paths[0]]
    # metadata = [metadata[0]]
    file_ids = context.upload_files(file_paths, metadata=metadata)

    wait_for_file_processing(context)

    files = context.list_files()

    file_names_and_meta = {os.path.basename(file_path): meta for file_path, meta in zip(file_paths, metadata)}

    assert file_ids

    assert {file.id for file in files} == set(file_ids)

    for file in files:
        assert file_names_and_meta[file.name] == file.metadata_json

    assert len(files) == 2

    file_map = {f.name: f for f in files}
    for original_path in file_paths:
        local_filename = os.path.basename(original_path)
        file_to_download = file_map[local_filename]

        with tempfile.NamedTemporaryFile() as temp_file:
            download_file(context.get_download_url(file_to_download.id), temp_file.name)

            with open(original_path, "rb") as original:
                temp_file.seek(0)
                assert (
                    original.read() == temp_file.read()
                ), f"The downloaded file content for {local_filename} differs from the original."


def test_upload_texts(client: OneContext, context: Context):
    contents = ["Sample text content 1", "Sample text content 2"]
    file_names = ["test_file_1.txt", "test_file_2.txt"]
    metadata = [{"author": "Author 1"}, {"author": "Author 2"}]

    context.upload_texts(contents, file_names=file_names, metadata=metadata)

    wait_for_file_processing(context)

    files = context.list_files()

    file_names_and_meta = {name: meta for name, meta in zip(file_names, metadata)}

    for file in files:
        assert (
            file_names_and_meta[file.name]["author"] == file.metadata_json["author"]
        ), f"Metadata for {file.name} does not match."

    assert len(files) == len(contents)

    file_map = {f.name: f for f in files}
    for content, file_name in zip(contents, file_names):
        file_to_download = file_map[file_name]
        with tempfile.NamedTemporaryFile(mode="r", encoding="utf-8") as temp_file:
            download_file(context.get_download_url(file_to_download.id), temp_file.name)

            temp_file.seek(0)
            assert (
                content == temp_file.read()
            ), f"The downloaded file content for {file_name} differs from the uploaded content."
