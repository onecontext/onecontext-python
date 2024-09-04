# OneContext

[![PyPI - Version](https://img.shields.io/pypi/v/onecontext.svg)](https://pypi.org/project/onecontext)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/onecontext.svg)](https://pypi.org/project/onecontext)



# Official OneContext Python SDK

This is the official Python SDK for the OneContext platform. Use this SDK to connect your backend applications, interactive notebooks, or command-line tools to OneContext's platform.

## What is OneContext?

OneContext is a platform that enables software engineers to compose and deploy custom RAG (Reading comprehension, Answer generation, and Generative) pipelines on state-of-the-art infrastructure, all without any hassle. Just create a context and add files to it. You can then query your context using vector search, hybrid search, etc. OneContext takes care of all the infrastructure details behind the scenes (SSL intents, DNS, Kubernetes clusters, embedding models, GPUs, auto-scaling, load balancing, etc).


## Quick Start

Install the package with `pip`:

```shell
pip install onecontext
```

```python

from onecontext import OneContext

# if api_key is omitted, ONECONTEXT_API_KEY env variable is used
oc = OneContext(api_key="<ONECONTEXT_API_KEY>")
```

You can get an api key [here](https://app.onecontext.ai/settings/account).

Note you mayu need to set the OPENAI_API_KEY on the settings page if using OPENAI embeddigns.


### Create a Context

A `Context` is where you store your data. It represents a sort of a "File Store", a "Knowledge Base", a "Second Brain", etc.

To create a context:

```python
context = oc.create_context(name="my_context")
```

To initilise an existing context object:

```python
context = oc.Context(name="my_context")
```

### Upload files

Now you can enrich your context with knowledge. You can make your context an expert in anything, just add files.

If you're on the free plan, you can have just one context, with up to 10 files (of less than 50 pages each). If you're
on the pro plan, you can have up to 5,000 contexts, each with up to 5,000 files.


#### You can add individual files

```python
context.upload_files(['path_to_file_1.pdf', 'path_to_file_2.pdf'], max_chunk_size=400)
```

#### You can also add a full directory of files

```python
context.upload_from_directory(“path_to_your_directory")
```
In the above code, replace `"path_to_your_directory"` with the actual path to your directory.

#### List files available in a context

```python
files = context.list_files()
for file in files:
    print(file)
```
This piece of code will print all files available in the specific context.

#### List all the contexts

```python
all_contexts = oc.list_contexts()
```
These lines of code will provide a list of all contexts available to you.

#### Deleting contexts

If you wish to delete any context, you can do so with:

```python
oc.delete_context("my_context")
```

### Search through your Context

The following piece of code will execute a query and search across all documents present in the context:

```python
context = oc.Context("my_context")
results = context.query(
    query="query_string_to_search",
    semantic_weight=0.7,
    full_text_weight=0.3,
    top_k=5,
    rrf_k=50,
)
```
More details on the arguments for this method:
- `query`: Query string that will be embedded used for the search.
- `top_k`: The maximum number of "chunks" that will be retrieved.
- `semantic_weight`: A value representing the weight of the relevance of the semantic similarity of the data in your context.
- `full_text_weight`: A weight value for the relevance of the actual words in the context using key word search.
- `rrfK`: quite a technical parameter which determines how we merge the scores
for semantic, and fullText weights. For more see
[here](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)

## License

`onecontext` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
