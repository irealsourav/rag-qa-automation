import anthropic
from typing import List, Dict
from ingest.test_results_loader import TestResultsLoader
from pipeline.vectorstore import VectorStore
from config import config

SYSTEM_PROMPT = """You are a Senior QA Engineer specialising in test reliability.
Analyse flaky test patterns and provide specific, actionable fixes.
Always explain WHY the test is likely flaky and HOW to fix it."""


class FlakyTestDetector:
    """
    Detects flaky tests from execution reports and suggests root-cause fixes
    by cross-referencing the actual test code via RAG.
    """

    def __init__(self, vectorstore: VectorStore = None, results_path: str = None):
        self.vectorstore = vectorstore or VectorStore()
        self.results_loader = TestResultsLoader(results_path)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def detect_and_fix(self, top_n: int = 10) -> List[Dict]:
        flaky_candidates = self.results_loader.get_flaky_candidates()
        if not flaky_candidates:
            return []

        results = []
        for candidate in flaky_candidates[:top_n]:
            analysis = self._analyse_flaky_test(candidate)
            results.append({**candidate, "analysis": analysis})
        return results

    def analyse_single(self, test_name: str, error_message: str = "") -> str:
        code_docs = self.vectorstore.query(
            test_name, collection_key="codebase", top_k=3
        )
        result_docs = self.vectorstore.query(
            test_name, collection_key="test_results", top_k=3
        )

        code_context = self._format_docs(code_docs, "Test code")
        result_context = self._format_docs(result_docs, "Execution history")

        prompt = f"""Analyse this potentially flaky test and suggest fixes:

Test name: {test_name}
Error message: {error_message or "Various intermittent failures"}

{code_context}

{result_context}

Please provide:
1. Root cause analysis — why is this test likely flaky?
2. Specific code fix (with before/after example)
3. Prevention strategy for similar issues
"""

        response = self.client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _analyse_flaky_test(self, candidate: Dict) -> str:
        return self.analyse_single(
            test_name=candidate["test_name"],
            error_message=str(candidate.get("statuses", [])),
        )

    def _format_docs(self, docs: List[Dict], label: str) -> str:
        if not docs:
            return f"{label}: Not found"
        parts = [f"{label}:"]
        for doc in docs:
            parts.append(f"  {doc['content'][:400]}")
        return "\n".join(parts)
