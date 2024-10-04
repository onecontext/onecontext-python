import os

import pytest

from onecontext.main import OneContext


@pytest.fixture
def context_name(client: OneContext):
    context_name = f"test_context_{__name__}"
    try:
        yield context_name
    finally:
        client.delete_context(context_name)


def test_create_delete_context(client: OneContext, context_name: str):
    client.create_context(context_name)
    contexts = client.list_contexts()
    assert any(context.name == context_name for context in contexts)
    client.delete_context(context_name)
    contexts = client.list_contexts()
    assert all(context.name != context_name for context in contexts)
