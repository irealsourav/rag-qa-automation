"""
Path A, step 1: load Jira tickets, make one Document per ticket, embed them and store
them in the "jira" collection.

    python -m rag_engine.sources.jira.index               # sample tickets in sample_data/jira/
    python -m rag_engine.sources.jira.index --from-jira   # real tickets (JIRA_* settings in .env)
"""
import argparse
import json
from typing import Dict, List

from langchain_core.documents import Document

from rag_engine.knowledge_base.langchain_store import get_store

# This source's own collection in ChromaDB (one collection per source)
COLLECTION = "jira"

SAMPLE_TICKETS = "sample_data/jira/tickets.json"


def load_sample_tickets(path: str = SAMPLE_TICKETS) -> List[Dict]:
    with open(path) as f:
        return json.load(f)


def load_jira_tickets(project_key: str = None) -> List[Dict]:
    """Reads tickets from Jira Cloud and converts them to the same shape as the sample file."""
    from rag_engine.sources.jira.loader import JiraLoader

    tickets = []
    for issue in JiraLoader().fetch_issues(project_key=project_key):
        tickets.append({
            "id": issue["id"],
            "type": issue["type"],
            "feature": issue["labels"][0] if issue["labels"] else "",
            "created": "",
            "title": issue["title"],
            # Plain Jira has no separate acceptance-criteria field; teams usually
            # write them inside the description, so they are indexed as part of it.
            "description": issue["description"],
            "acceptance_criteria": [],
        })
    return tickets


def ticket_to_document(ticket: Dict) -> Document:
    """One ticket = one chunk: title + description + acceptance criteria stay together."""
    text = f"{ticket['title']}\n\n{ticket['description']}"
    criteria = ticket.get("acceptance_criteria") or []
    if criteria:
        text += "\n\nAcceptance criteria:\n" + "\n".join(f"- {c}" for c in criteria)

    # Metadata allows filtering later, e.g. only bugs, or only the "auth" feature.
    # Chroma only stores str/int/float/bool values, so missing values become "".
    metadata = {
        "source": "jira",
        "ticket_id": ticket["id"],
        "type": ticket.get("type") or "",
        "feature": ticket.get("feature") or "",
        "created": ticket.get("created") or "",
    }
    return Document(page_content=text, metadata=metadata)


def build_index(tickets: List[Dict], persist_directory: str = None) -> int:
    store = get_store(COLLECTION, persist_directory)
    # Start from an empty collection so a rebuild never leaves deleted or duplicate tickets behind
    store.reset_collection()
    documents = [ticket_to_document(t) for t in tickets]
    store.add_documents(documents, ids=[t["id"] for t in tickets])
    return len(documents)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Jira collection in ChromaDB")
    parser.add_argument("--from-jira", action="store_true", help="read tickets from Jira instead of the sample file")
    parser.add_argument("--project", help="Jira project key (defaults to JIRA_PROJECT_KEY)")
    args = parser.parse_args()

    tickets = load_jira_tickets(args.project) if args.from_jira else load_sample_tickets()
    count = build_index(tickets)
    print(f"Indexed {count} Jira tickets.")
