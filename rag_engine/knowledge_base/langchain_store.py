"""
Shared LangChain vector store, used by every source that has its own collection
(sources/jira/ today; cypress/, api/ and others later).

Writing (a source's index.py) and reading (its retriever.py) must use the same embedding
model, otherwise queries are compared against vectors made by a different model. Keeping
the model here means every source uses the same one.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from rag_engine.config import config

# Same local model as the rest of the repo: 384-dimension vectors, no API key needed
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    # Loading the model takes a few seconds, so it is loaded once and reused.
    # Normalised vectors make cosine similarity a plain dot product.
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def get_store(collection_name: str, persist_directory: str = None) -> Chroma:
    """One collection per source (docs/rag-design.md, section 4), e.g. get_store("jira")."""
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        # Chroma saves to this folder automatically; there is no persist() call any more
        persist_directory=persist_directory or config.CHROMA_DB_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )
