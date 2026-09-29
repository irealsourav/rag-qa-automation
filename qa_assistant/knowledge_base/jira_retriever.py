"""
Path A, step 2: the R in RAG. Finds the Jira tickets most similar in meaning to a question.

    python -m qa_assistant.knowledge_base.jira_retriever "how is a failed login handled?"
"""
import sys
from typing import List, Tuple

from langchain_core.vectorstores import VectorStoreRetriever

from qa_assistant.knowledge_base.jira_store import get_jira_store


def get_jira_retriever(k: int = 3, feature: str = None) -> VectorStoreRetriever:
    search_kwargs = {"k": k}
    if feature:
        # Metadata filter: only tickets whose "feature" matches, e.g. "auth"
        search_kwargs["filter"] = {"feature": feature}
    return get_jira_store().as_retriever(search_kwargs=search_kwargs)


def retrieve(query: str, k: int = 3, feature: str = None) -> List[Tuple[str, str]]:
    """Returns up to k (ticket text, ticket id) pairs, most similar first."""
    documents = get_jira_retriever(k, feature).invoke(query)
    return [(doc.page_content, doc.metadata["ticket_id"]) for doc in documents]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "how is a failed login handled?"
    print(f"Query: {question}\n")
    for text, ticket_id in retrieve(question):
        title = text.splitlines()[0]
        print(f"[{ticket_id}] {title}")
