import os

import pytest

from onecontext.main import OneContext

def test_create_delete_context(client: OneContext):
    context_name = "test_context"
    client.create_context(context_name)
    contexts = client.list_contexts()
    assert any(context.name == context_name for context in contexts)
    client.delete_context(context_name)
    contexts = client.list_contexts()
    assert all(context.name != context_name for context in contexts)
