# OneContext

[![PyPI - Version](https://img.shields.io/pypi/v/onecontext.svg)](https://pypi.org/project/onecontext)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/onecontext.svg)](https://pypi.org/project/onecontext)



# Official OneContext Python SDK

This is the official Python SDK for the OneContext platform. Use this SDK to connect your backend applications, interactive notebooks, or command-line tools to OneContext's platform.

## What is OneContext?

OneContext is a platform that enables software engineers to compose and deploy custom RAG (Reading comprehension, Answer generation, and Generative) pipelines on state-of-the-art infrastructure, all without any hassle. Just create a context and add files to it. You can then search your context using vector search, hybrid search, etc. OneContext takes care of all the infrastructure details behind the scenes (SSL intents, DNS, Kubernetes clusters, embedding models, GPUs, auto-scaling, load balancing, etc).


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

Note you may need to set the OPENAI_API_KEY on the settings page if using OPENAI embeddigns.


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
#### To upload strings directly use the upload_texts method

```python
context.upload_texts(['Hi Bob!', 'Oh hey Mark!'])
```

#### You can also add a full directory of files

```python
context.upload_from_directory("path_to_your_directory")
```
In the above code, replace `"path_to_your_directory"` with the actual path to your directory.

#### You can add metadata to files at upload time

```python
file_paths = ['path_to_file_1.pdf', 'path_to_file_2.pdf']
files_metadata = [{"tag": "file_1_tag"}, {"tag": "file_2_tag"}]
context.upload_files(file_paths,metadata=files_metadata)
```
You can use this metadata to filter searches against your context.
For more details, see the [OneContext Structured Query Language](#onecontext-structured-query-language) section.

#### List files available in a context

```python
files = context.list_files()
for file in files:
    print(file)
```

You can also generate a download link for a file using the file_id:

```python
import requests
files = context.list_files()
file = files[0]
file_url = context.get_download_url(file_id=file.id)
response = requests.get(file_url)
path = f"./local_folder/{file.name}"
with open(path, "wb") as f:
    f.write(response.content)
```

> **Note:**
Download urls will be valid for 5 minutes after they have been generated.

#### List the chunks available in a context

```python
chunks = context.list_chunks(limit=50)
```

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

The following piece of code will execute a query and search across all
chunks present in the context which have matchin metadata:


```python
context = oc.Context("my_context")
chunks = context.search(
    query="query_string_to_search",
    semantic_weight=0.7,
    full_text_weight=0.3,
    top_k=5,
    rrf_k=50,
    metadata_filters = {"tag" : {"$eq" : "file_1_tag"}}
)
```
More details on the arguments for this method:
- `query`: Query string that will be embedded used for the search.
- `top_k`: The maximum number of "chunks" that will be retrieved.
- `semantic_weight`: A value representing the weight of the relevance of the
semantic similarity of the data in your context.
- `full_text_weight`: A weight value for the relevance of the actual words in
the context using key word search.
- `rrfK`: quite a technical parameter which determines how we merge the scores
for semantic, and fullText weights. For more see
[here](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)
- `metadata_filters`: A dictionary of criteria used to filter results based on
metadata. See the OneContext Structured Query Language section below for the
syntax details

### Extract Structured Output from your Context

You can get structured output directly from your context by providing a json schema
or a pydantic (v2) `BaseModel`:

```python

from pydantic import BaseModel, Field

class RockBandInfo(BaseModel):
    title: str = Field(description="a title of a 1970s rockband")
    lyrics: str = Field(description="lyrics to their absolute banger of a song")

context = oc.Context("my_context")


output_dict, chunks = context.extract_from_search(
    query="tell me about rockbands",
    schema=RockBandInfo, # you can pass a pydantic (v2) model or a json schema dict
    extraction_prompt="Output only JSON matching the provided schema about the rockbands",
)

rock_band = RockBandInfo.model_validate(output_dict)
```
`extract_from_search` works just like search but returns the structured output
as a dictionary as well as the reference chunks.

Note that `pydantic` is not a dependency of `onecontext`; you an pass a json schema
definition directly to the extract methods instead of a `BaseModel`.

You can also extract structured output directly from chunks without performing as search:

```python
output_dict, chunks = context.extract_from_chunks(
    schema=RockBandInfo, # you can pass a pydantic model or a json schema dict
    extraction_prompt="Output only JSON matching the provided schema about the rockbands",
    metadata_filters = {"tag" : {"$eq" : "rockband"}}
)

rock_band = RockBandInfo.model_validate(output_dict)
```

# OneContext Structured Query Language

OneContext allows you to use a custom "Structured Query Language" to filter
the chunks in your context.

The syntax is quite similar to what you might find in no-SQL databases like
MongoDB, even though it operates on a SQL database at its core.

The syntax is based around the application of `operators`. There are _two_
levels of operators. You can interpret the two levels as "aggregators" and
"comparators".

### Aggregators
The aggregator operators you can use are:

| Key          | Value Description                                                                                                                                           |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `$and`       | Returns True i.f.f. _all_ of the conditions in this block return True.
| `$or`        | Returns True if _any_ of the conditions in this block return True.

### Comparators
The comparator operators you can use are:

| Key          | Value Description                                                                   | Supplied Value Type | Returned Value Type          |
|--------------|-------------------------------------------------------------------------------------|---------------------|------------------------------|
| `$eq`        | Returns True if the value returned from the DB is equal to the supplied value.      | `string             | int | float`       | `string | int | float`       |
| `$neq`        | Returns True if the value returned from the DB is not equal to the supplied value.      | `string             | int | float`       | `string | int | float`       |
| `$gt`        | Returns True if the value returned from the DB is greater than the supplied value.  | `int                | float`                | `int | float`                |
| `$lt`        | Returns True if the value returned from the DB is less than the supplied value.     | `int                | float`                | `int | float`                |
| `$in`        | Returns True if the value returned from the DB is contained by the supplied array.  | `array<string>`      | int | float>`| `string | int | float`       |
| `$contains`  | Returns True if the array value returned from the DB contains the supplied value.   | `string             | int | float`       | `array<string | int | float>`|


## Putting it all together

Using the above building blocks, it's pretty simple to put together quite an advanced composite filter across your embeddings at runtime.

For example in Python you could define some metadata filters like the below:

``` python
metadata_filters = { "$and": [
  {"$or": [
    {"department": {"$eq":"accounts"}},
    {"department": { "$in": ["finance", "compliance"}}
  ]},
  {"tag": {"$eq": "test"}},
  {"my_score": {"$gt" : 0.5}},
  {"my_other_score" : {"$gt" :0.4}}
]}

context = oc.Context("my_context")
chunks = context.search(
    query="query_string_to_search",
    metadata_filters = metadata_filters,
)

```


## License

`onecontext` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
