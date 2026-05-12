import anthropic
from typing import List, Dict, Optional
from pipeline.vectorstore import VectorStore
from config import config

SYSTEM_PROMPT = """You are a Senior QA Automation Engineer. 
Your job is to generate high-quality, specific test cases based on requirements, user stories and existing test patterns.

Rules:
- Each test case must have: ID, title, preconditions, steps, expected result
- Cover happy path, edge cases and negative scenarios
- Be specific — no vague steps like "verify the page works"
- Match the style of any existing test code provided in the context
- Output in clean structured format"""


class TestCaseGenerator:
    """
    Generates test cases from requirements using RAG + Claude.
    Retrieves relevant requirements, existing tests and generates new test cases.
    """

    def __init__(self, vectorstore: VectorStore = None):
        self.vectorstore = vectorstore or VectorStore()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate(
        self,
        feature: str,
        framework: str = "Cypress",
        count: int = 5,
        include_negative: bool = True,
    ) -> str:
        context_docs = self.vectorstore.query_all_collections(feature, top_k=5)
        context = self._build_context(context_docs)

        prompt = f"""Generate {count} test cases for the following feature:
Feature: {feature}
Test Framework: {framework}
Include negative tests: {include_negative}

Context from requirements and existing tests:
{context}

Generate structured test cases covering:
1. Happy path scenarios
2. Edge cases
3. {"Negative/error scenarios" if include_negative else ""}

Format each test case as:
TC-[N]: [Title]
Preconditions: ...
Steps:
  1. ...
  2. ...
Expected Result: ...
"""

        response = self.client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

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

    def _build_context(self, docs: List[Dict]) -> str:
        if not docs:
            return "No relevant context found."
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("metadata", {}).get("source", "unknown")
            parts.append(f"[{i}] Source: {source}\n{doc['content'][:400]}")
        return "\n\n---\n\n".join(parts)
