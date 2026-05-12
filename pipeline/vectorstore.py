import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from pipeline.embedder import Embedder
from config import config


class VectorStore:
    """
    ChromaDB-backed vector store.
    Persists to disk so you don't re-index on every run.
    """

    COLLECTIONS = {
        "requirements": "jira_confluence_docs",
        "codebase":     "test_codebase",
        "test_results": "test_execution_results",
    }

    def __init__(self, db_path: str = None):
        path = db_path or config.CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(path=path)
        self.embedder = Embedder()
        self._collections: Dict[str, chromadb.Collection] = {}

    def _get_collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def upsert(self, documents: List[Dict], collection_key: str = "requirements"):
        if not documents:
            return

        collection_name = self.COLLECTIONS.get(collection_key, collection_key)
        collection = self._get_collection(collection_name)

        ids, texts, metadatas = [], [], []
        for doc in documents:
            doc_id = str(doc.get("chunk_id") or doc.get("id") or f"doc_{len(ids)}")
            content = doc.get("content", "")
            if not content.strip():
                continue
            ids.append(doc_id)
            texts.append(content)
            metadatas.append({
                "source":    str(doc.get("source", "")),
                "original_id": str(doc.get("original_id") or doc.get("id", "")),
                "file_name": str(doc.get("file_name", "")),
                "type":      str(doc.get("type", "")),
                "title":     str(doc.get("title", "")),
            })

        embeddings = self.embedder.embed(texts)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"[VectorStore] Upserted {len(ids)} chunks → {collection_name}")

    def query(
        self,
        query_text: str,
        collection_key: str = "requirements",
        top_k: int = None,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        collection_name = self.COLLECTIONS.get(collection_key, collection_key)
        collection = self._get_collection(collection_name)
        k = top_k or config.TOP_K_RESULTS

        query_embedding = self.embedder.embed_single(query_text)
        kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "content":  doc,
                "metadata": results["metadatas"][0][i],
                "score":    1 - results["distances"][0][i],
            })
        return output

    def query_all_collections(self, query_text: str, top_k: int = 3) -> List[Dict]:
        all_results = []
        for key in self.COLLECTIONS:
            try:
                results = self.query(query_text, collection_key=key, top_k=top_k)
                all_results.extend(results)
            except Exception:
                pass
        return sorted(all_results, key=lambda x: x["score"], reverse=True)

    def count(self, collection_key: str = "requirements") -> int:
        collection_name = self.COLLECTIONS.get(collection_key, collection_key)
        return self._get_collection(collection_name).count()
