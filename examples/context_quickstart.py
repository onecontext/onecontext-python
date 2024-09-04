# Import the OneContext client
from onecontext import Chunk, OneContext

# Initialize the OneContext client with your API key
# If the API key is not passed as an argument, it will look for ONECONTEXT_API_KEY environment variable
oc = OneContext()

# Create a new context called 'my_context'
context = oc.create_context(name="cs_papers")

# Alternatively, initialize an existing context object
# context = oc.Context(name="my_context")

# # Upload individual files to the context
# context.upload_files(["path_to_file_1.pdf", "path_to_file_2.pdf"], max_chunk_size=400)

# Or upload a whole directory of files to the context
context.upload_from_directory("./examples/example_files")

# List all files in the context and print their names,
files = context.list_files()

print("List of files in the context:")
for file in files:
    print(file)

# List all available contexts
all_contexts = oc.list_contexts()
print("List of available contexts:")
for ctx in all_contexts:
    print(ctx)

# Delete a context if necessary
# oc.delete_context("my_context")

# Search within the context using a query
context = oc.Context("cs_papers")

chunks: list[Chunk] = context.query(query="What are the consequences of the invention", top_k=5)

# Print search results
print("Search Results:")
for chunk in chunks:
    print(chunk.content)
