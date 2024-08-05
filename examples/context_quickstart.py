from onecontext import OneContext

oc = OneContext()
context_name = "test_0"

context = oc.create_context(context_name)

context.upload_file("./examples/babbage.pdf")

# this kicks of a run for every connected pipeline:
# list runs to see the current state of each run
print(oc.list_runs())

context.list_files()

# once the ingestion_pipeline run is complete we can query the index for relevant chunks
query = "What are consequences of inventing a computer?"
retriever_top_k = 50
top_k = 5

# overide the step_args for the two steps of the query pipeline by
# passing dict in the form {step_name: step_args_dict}
override_args = {
    "query_embedder": {"query": query},
    "retriever": {
        "top_k": retriever_top_k,
    },
    "reranker": {"top_k": top_k, "query": query},
}

chunks = context.query(override_args)

oc.delete_context(context_name)
