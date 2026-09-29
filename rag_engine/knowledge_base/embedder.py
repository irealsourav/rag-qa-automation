from typing import List
from sentence_transformers import SentenceTransformer


class Embedder:
    """
    Wraps sentence-transformers for local, free embedding generation.
    No API key needed. Works offline after first download.

    Model: all-MiniLM-L6-v2
    - 384 dimensions
    - Fast and good quality for semantic search
    - ~80MB download on first use
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"[Embedder] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"[Embedder] Ready. Embedding dimension: {self.dimension}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]
