# Note that ingestion.yaml and query.yaml are required to run this example
# copy from the examples directory or
# clone this repo & `cd example`
# You will alos need an api key
# you can get one here: https://onecontext.ai/

from onecontext import OneContext

# ONECONTEXT_API_KEY env variable is used when not provied in arguments
oc = OneContext()

# A knowledge base is a collection of files.
knowledgebase = oc.create_knowledgebase(name="my_kb")

# A vector index is a collection of chunks with embeddings
# specify the model at creation to configure the vector index
oc.create_index("my_vector_index", model="BAAI/bge-base-en-v1.5")

# deploy an ingesiton pipeline that watches the knowledge base we just ceated
oc.deploy_pipeline("my_ingestion_pipeline", pipeline_yaml_path="./ingestion.yaml")

# deploy a two-step query  pipeline to query the index
query_pipeline = oc.deploy_pipeline("basic_query", "./query.yaml")

# upload a file to an existing knowledgebase like so:
knowledgebase = oc.KnowledgeBase(name="my_kb")
knowledgebase.upload_file("babbage.pdf")

# this kicks of a run for every connected pipeline:
# list runs to see the current state of each run
print(oc.list_runs())

# once the ingestion_pipeline run is complete we can query the index for relevant chunks
query = "What are consequences of inventing a computer?"
retreiver_top_k = 50
top_k = 5

# overide the step_args for the two steps of the query pipeline by
# passing dict in the form {step_name: step_args_dict}
override_args = {
    "retriever": {
        "top_k": retreiver_top_k,
        "query": query,
    },
    "reranker": {"top_k": top_k, "query": query},
}

query_pipeline = oc.Pipeline("basic_query")

chunks = query_pipeline.run(override_args)

print(chunks[0].content)
