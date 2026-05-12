import anthropic
from typing import List, Dict
from pipeline.vectorstore import VectorStore
from config import config

SYSTEM_PROMPT = """You are a QA Automation expert with deep knowledge of test frameworks.
Answer questions about the provided test codebase clearly and specifically.
If you reference specific code, quote it directly from the context.
If the answer is not in the context, say so honestly — do not make things up."""


class CodebaseQA:
    """
    Answers natural language questions about the test codebase.
    Examples:
      - "Where are the login tests?"
      - "How is the API mocking set up?"
      - "Which tests cover the invoice feature?"
      - "What fixtures are available in pytest?"
    """

    def __init__(self, vectorstore: VectorStore = None):
        self.vectorstore = vectorstore or VectorStore()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.history: List[Dict] = []

    def ask(self, question: str, use_history: bool = True) -> str:
        context_docs = self.vectorstore.query(
            question, collection_key="codebase", top_k=config.TOP_K_RESULTS
        )
        context = self._build_context(context_docs)

        user_message = f"""Question: {question}

Relevant test code from the codebase:
{context}"""

        messages = []
        if use_history and self.history:
            messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text

        if use_history:
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": answer})

        return answer

    def reset_history(self):
        self.history = []

    def _build_context(self, docs: List[Dict]) -> str:
        if not docs:
            return "No relevant test code found in the codebase."
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            file_name = meta.get("file_name", "unknown")
            score = doc.get("score", 0)
            parts.append(
                f"[{i}] File: {file_name} (relevance: {score:.2f})\n"
                f"```\n{doc['content'][:600]}\n```"
            )
        return "\n\n".join(parts)
