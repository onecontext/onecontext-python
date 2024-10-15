import os
import sys

import pytest

# import all the env variables in .env and add them to the environment
from dotenv import load_dotenv

from onecontext.main import OneContext

load_dotenv()


@pytest.fixture
def api_key():
    return os.getenv("ONECONTEXT_API_KEY")


@pytest.fixture
def base_url():
    return os.getenv("ONECONTEXT_BASE_URL", "https://app.onecontext.ai/api/v5/")


@pytest.fixture
def bypass():
    return os.getenv("BYPASS")


@pytest.fixture
def client(api_key, base_url, bypass):
    extra_headers = {"x-vercel-protection-bypass": bypass}
    client = OneContext(api_key=api_key, base_url=base_url, extra_headers=extra_headers)
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
