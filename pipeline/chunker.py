from typing import List, Dict
from config import config


class TextChunker:
    """
    Splits documents into overlapping chunks suitable for embedding.
    Uses a simple recursive character splitter strategy.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        chunks = []
        for doc in documents:
            doc_chunks = self._split_text(doc.get("content", ""))
            for i, chunk_text in enumerate(doc_chunks):
                chunk = {
                    **doc,
                    "chunk_index": i,
                    "chunk_id": f"{doc.get('id', 'unknown')}__chunk_{i}",
                    "content": chunk_text,
                    "original_id": doc.get("id"),
                }
                chunks.append(chunk)
        return chunks

    def _split_text(self, text: str) -> List[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        self._recursive_split(text, self.separators, chunks)
        return chunks

    def _recursive_split(self, text: str, separators: List[str], result: List[str]):
        separator = separators[0] if separators else ""
        remaining_seps = separators[1:]

        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        current = ""
        for split in splits:
            candidate = current + (separator if current else "") + split
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current.strip())
                    overlap_start = max(0, len(current) - self.chunk_overlap)
                    current = current[overlap_start:] + (separator if current else "") + split
                else:
                    if len(split) <= self.chunk_size:
                        current = split
                    elif remaining_seps:
                        self._recursive_split(split, remaining_seps, result)
                    else:
                        for i in range(0, len(split), self.chunk_size - self.chunk_overlap):
                            result.append(split[i:i + self.chunk_size].strip())

        if current.strip():
            result.append(current.strip())
