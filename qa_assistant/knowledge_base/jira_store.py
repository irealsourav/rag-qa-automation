"""
Shared settings for the Jira collection.

build_index.py (writing) and jira_retriever.py (reading) must use the same collection
and the same embedding model, otherwise queries are compared against vectors made by a
different model. Keeping both here means they can't drift apart.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from qa_assistant.config import config

# One collection per knowledge source (docs/rag-design.md, section 4)
JIRA_COLLECTION = "jira"

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


def get_jira_store(persist_directory: str = None) -> Chroma:
    return Chroma(
        collection_name=JIRA_COLLECTION,
        embedding_function=get_embeddings(),
        # Chroma saves to this folder automatically; there is no persist() call any more
        persist_directory=persist_directory or config.CHROMA_DB_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )
