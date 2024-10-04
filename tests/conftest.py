import os
import sys

import pytest

from onecontext.main import OneContext
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))


@pytest.fixture
def api_key():
    return os.getenv("ONECONTEXT_API_KEY")


@pytest.fixture
def base_url():
    return os.getenv("ONECONTEXT_BASE_URL", "https://app.onecontext.ai/api/v4/")


@pytest.fixture
def client(api_key, base_url):
    client = OneContext(api_key=api_key, base_url=base_url)
    return client


@pytest.fixture
def test_files_directory() -> str:
    return os.path.join(os.path.dirname(__file__), "files")


@pytest.fixture
def file_paths(test_files_directory) -> list[str]:
    return [
        os.path.join(test_files_directory, f)
        for f in os.listdir(test_files_directory)
        if os.path.isfile(os.path.join(test_files_directory, f))
    ]
