import anthropic
from typing import List, Dict, Literal
from pydantic import BaseModel
from pipeline.vectorstore import VectorStore
from config import config

SYSTEM_PROMPT = """You are a Senior QA Automation Engineer.
Your job is to generate high-quality, specific test cases based on requirements, user stories and existing test patterns.

Rules:
- Each test case has a title, preconditions, steps and one expected result
- Cover happy path, edge cases and negative scenarios
- Be specific — no vague steps like "verify the page works"
- Match the style of any existing test code provided in the context"""


class TestCase(BaseModel):
    __test__ = False  # not a pytest test class

    title: str
    category: Literal["happy_path", "edge_case", "negative"]
    preconditions: str
    steps: List[str]
    expected_result: str


class TestSuite(BaseModel):
    __test__ = False  # not a pytest test class

    test_cases: List[TestCase]


class TestCaseGenerator:
    __test__ = False  # not a pytest test class

    """
    Generates test cases from requirements using RAG + Claude.
    Retrieves relevant requirements, existing tests and generates new test cases.
    Claude returns them as structured data (TestCase), so they can be rendered as
    markdown or pushed to Jira without parsing free text.
    """

    def __init__(self, vectorstore: VectorStore = None):
        self.vectorstore = vectorstore or VectorStore()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate_cases(
        self,
        feature: str,
        framework: str = "Cypress",
        count: int = 5,
        include_negative: bool = True,
    ) -> List[TestCase]:
        context_docs = self.vectorstore.query_all_collections(feature, top_k=5)
        context = self._build_context(context_docs)
        categories = "happy path, edge case and negative" if include_negative else "happy path and edge case"

        prompt = f"""Generate exactly {count} test cases for the following feature.
Feature: {feature}
Test Framework: {framework}
Cover {categories} scenarios.

Context from requirements and existing tests:
{context}"""

        response = self.client.messages.parse(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=TestSuite,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise RuntimeError(f"Claude did not return test cases (stop reason: {response.stop_reason})")
        return response.parsed_output.test_cases

    def generate(
        self,
        feature: str,
        framework: str = "Cypress",
        count: int = 5,
        include_negative: bool = True,
    ) -> str:
        return self.to_markdown(self.generate_cases(feature, framework, count, include_negative))

    def generate_from_story(self, story_id: str) -> str:
        results = self.vectorstore.query(
            story_id,
            collection_key="requirements",
            where={"original_id": story_id},
        )
        if not results:
            return f"Story {story_id} not found in the knowledge base."

        story_content = results[0]["content"]
        return self.generate(feature=story_content)

    @staticmethod
    def to_markdown(cases: List[TestCase]) -> str:
        blocks = []
        for i, case in enumerate(cases, 1):
            steps = "\n".join(f"  {n}. {step}" for n, step in enumerate(case.steps, 1))
            blocks.append(
                f"TC-{i}: {case.title}\n"
                f"Category: {case.category.replace('_', ' ')}\n"
                f"Preconditions: {case.preconditions}\n"
                f"Steps:\n{steps}\n"
                f"Expected Result: {case.expected_result}"
            )
        return "\n\n".join(blocks)

    def _build_context(self, docs: List[Dict]) -> str:
        if not docs:
            return "No relevant context found."
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("metadata", {}).get("source", "unknown")
            parts.append(f"[{i}] Source: {source}\n{doc['content'][:400]}")
        return "\n\n---\n\n".join(parts)
