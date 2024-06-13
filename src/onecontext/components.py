from dataclasses import dataclass


@dataclass
class Step:
    name: str
    inputs: list[str] = []


class KnowledgeBaseFilesStep(Step):
    type: ClassVar[str] = "KnowledgeBaseFiles"
    user_id: str | None = None
    knowledgebase_names: list[str] = []


class PreprocessorStep(Step):
    type: ClassVar[str] = "Preprocessor"

    # TODO : make these astully do the thing
    remove_empty_lines: bool = True
    remove_non_asci_chars: bool = False
    add_punctuation: bool = False


class ChunkerStep(Step):
    type: ClassVar[str] = "Chunker"
    chunk_size_words: int | None = None
    chunk_size_tokens: int | None = None
    chunk_overlap: int = 10
    tokeniser: str = "gpt-3.5-turbo"


class SentenceTransformerEmbedderStep(Step):
    type: ClassVar[str] = "SentenceTransformerEmbedder"
    model_name: str


class RetrieverStep(Step):
    type: ClassVar[str] = "Retriever"
    model_name: str
    vector_index_name: str
    query: str | None = None
    metadata_json: dict[str, Any] | None = None
    top_k: int
    user_id: str | None = None
    return_embeddings: bool = False


class RerankerStep(Step):
    type: ClassVar[str] = "Reranker"
    model_name: str | None = None
    query: str | None = None
    top_k: int | None = None
