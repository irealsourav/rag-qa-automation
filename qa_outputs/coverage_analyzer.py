import anthropic
from typing import List, Dict
from pipeline.vectorstore import VectorStore
from config import config

SYSTEM_PROMPT = """You are a QA coverage analyst.
Compare requirements against existing test coverage and identify gaps.
Be specific — name the exact features or scenarios missing test coverage.
Prioritise gaps by business risk (payments > UI cosmetics)."""


class CoverageAnalyzer:
    """
    Compares requirements against test codebase to identify
    features with missing or insufficient test coverage.
    """

    def __init__(self, vectorstore: VectorStore = None):
        self.vectorstore = vectorstore or VectorStore()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def analyse(self, feature_area: str = None) -> str:
        query = feature_area or "all features and requirements"

        req_docs = self.vectorstore.query(
            query, collection_key="requirements", top_k=8
        )
        test_docs = self.vectorstore.query(
            query, collection_key="codebase", top_k=8
        )

        req_context = self._format_docs(req_docs, "Requirements & User Stories")
        test_context = self._format_docs(test_docs, "Existing Test Coverage")

        prompt = f"""Analyse test coverage gaps for: {query}

{req_context}

{test_context}

Please provide:
1. Coverage summary — what is well tested?
2. Coverage gaps — what requirements have NO test coverage?
3. Partial coverage — what is tested but not thoroughly?
4. Prioritised recommendations — where to add tests first and why?
"""

        response = self.client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def get_untested_stories(self) -> List[str]:
        req_docs = self.vectorstore.query(
            "user story feature requirement", collection_key="requirements", top_k=20
        )
        untested = []
        for req in req_docs:
            title = req["metadata"].get("title", "")
            if not title:
                continue
            test_results = self.vectorstore.query(
                title, collection_key="codebase", top_k=1
            )
            if not test_results or test_results[0]["score"] < 0.5:
                untested.append(title)
        return untested

    def _format_docs(self, docs: List[Dict], label: str) -> str:
        if not docs:
            return f"{label}: None found"
        parts = [f"{label}:"]
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            title = meta.get("title") or meta.get("file_name", "")
            parts.append(f"  [{i}] {title}\n      {doc['content'][:300]}")
        return "\n".join(parts)
