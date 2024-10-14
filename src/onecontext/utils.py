import json
import sys


def batch_by_size(items: list, max_size_mb: int):
    size_limit = max_size_mb << 20  # Convert MB to bytes
    batch, cum_size = [], 0
    for item in items:
        item_size = len(json.dumps(item).encode("utf-8"))
        if cum_size + item_size > size_limit and batch:
            yield batch
            batch, cum_size = [], 0
        batch.append(item)
        cum_size += item_size

    if batch:
        yield batch
