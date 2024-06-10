# OneContext

[![PyPI - Version](https://img.shields.io/pypi/v/onecontext.svg)](https://pypi.org/project/onecontext)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/onecontext.svg)](https://pypi.org/project/onecontext)

-----
**Table of Contents**
- [LLM Context as a Service](#llm-context-as-a-service)
- [Quick Start](#quick-start)
- [License](#license)

-----

## LLM Context as a Service

OneContext makes it really easy and fast to augment your LLM application with your own data
in a few API calls. Upload your data to a `Knowledge Base` query with natural language to retrieve relevant context for your LLM application.

We manage the full document processing and retrieval pipeline so that you don't have to:

- document ingestion, chunking and cleaning
- efficient vector embeddings at scale using state of the art open source models
- low latency multi stage query pipeline to provide the most relevant context
for your LLM application

We keep up with the latest research to provide an accurate and fast retrieval pipeline
based on model evalution and best practice heuristics.

### Multi stage query pipeline out of the box:
- Fast base-model retrieves a large pool of documents
- Cross-encoder reranks the retrieved documents to provide the precise
results relevant to the query.

### Use Cases:
- Question Answering over a large knowledge base
- Long term memory for chatbots
- Runtime context for instruction following agents
- Prevent and detect hallucinations based on custom data


## Quick Start

Install the package with `pip`:

```shell
pip install onecontext
```

> **Note:**
> If you prefer to jump right in the full example code is in [`quickstart.py`](examples/quickstart.py)


``` python

from onecontext import OneContext

# if api_key is omitted, ONECONTEXT_API_KEY env variable is used
oc = OneContext(api_key="<ONECONTEXT_API_KEY>")
```

You can get an api key [here](https://onecontext.ai/).

### Create your first knowledge base

A knowledge base is a collection of files. To create a knowledge base:

``` python
knowledgebase = oc.create_knowledgebase(name="my_kb")
```

### Create a Vector Index

We want to chunk and embed the files in our knowledebase but first we need
somewhere to store our vectors. We create a vector index and specify the
embedding model that the vector index should expect:


``` py
oc.create_index("my_vector_index", model="BAAI/bge-base-en-v1.5")
```

By specifying the model we create a vector index of appropriate dimensions and
also ensure that we never write embeddings from a different model to this index.



### Create an ingestion Pipeline

We are ready to deploy our first ingestion pipeline.

Create a [`ingestion.yaml`](examples/ingestion.yaml) with the following content:

```yaml
steps:
  - step: KnowledgeBaseFiles
    name: input
    step_args:
      # specify the source knowledgebases to watch
      knowledgebase_names: ["my_kb"]
    inputs: []

  - step: Preprocessor
    name: preprocessor
    step_args: {}
    inputs: [input]

  - step: Chunker
    name: simple_chunker
    step_args:
      chunk_size_words: 320
      chunk_overlap: 30
    inputs: [preprocessor]

  - step: SentenceTransformerEmbedder
    name: sentence-transformers
    step_args:
      model_name: BAAI/bge-base-en-v1.5
    inputs: [ simple_chunker ]

  - step: ChunkWriter
    name: save
    step_args:
      vector_index_name: my_vector_index
    inputs: [sentence-transformers]
```

Then deploy like so:

```python
oc.deploy_pipeline("my_ingestion_pipeline", pipeline_yaml_path="./ingestion.yaml")
```

### Create a query Pipeline

To query the vector index we need to define a query pipeline.

Create a [`query.yaml`](examples/query.yaml) with the following content:

```yaml
steps:
  - step: Retriever
    name: retriever
    step_args:
      query: "placeholder"
      model_name: BAAI/bge-base-en-v1.5
      vector_index_name: my_vector_index
      top_k: 100
      metadata_filters: { }
    inputs: [ ]


  - step: Reranker
    name: reranker
    step_args:
      query: "placeholder"
      model_name: BAAI/bge-reranker-base
      top_k: 5
      metadata_filters: { }
    inputs: [ retriever ]

```

Here we create a simple two-step query pipeline.

- The `Retriever` step embeds the query and performs a similarity search against
    the index we defined earlier. This step has a high recall and is great to
    retrieve many candidate vectors.
- The `Reranker` step uses cross-encoder model to further narrow down the results
only to the most relevant chunks.


``` py

query_pipeline = oc.deploy_pipeline("basic_query", "./query.yaml")

```

### Uploading Files:

Upload files to an existing knowledge base:

```python
knowledgebase = oc.KnowledgeBase(name="my_kb")
knowledgebase.upload_file("babbage.pdf")
```

When a file is uploaded any pipelines connected to the KnowledgeBase will be
triggered to run.

List runs to see the current state of each run:


```python
oc.list_runs()
```


### Run the query Pipeline

Once the ingestion pipeline run is complete we can query the index for relevant chunks
using the query pipeline we created earlier.

We can run the query pipeline and override any of default the step arguments defined in our pipeline at runtime by passing
a dictionary of the form:

    `{step_name : {step_arg: step_arg_value}}`.


``` py
query = "What are consequences of inventing a computer?"
retriever_top_k = 50
top_k = 5

override_args = {
    "retriever": {
        "top_k": retriever_top_k,
        "query": query,
    },
    "reranker": {"top_k": top_k, "query": query},
}

chunks = query_pipeline.run(override_args)
```


## License

`onecontext` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
