import json

from rag_engine.sources.jira.index import load_sample_tickets, ticket_to_document
from tests.evals.eval_retrieval import DATASET, reciprocal_rank

TICKET = {
    "id": "QA-102", "type": "Story", "feature": "auth", "created": "2026-01-05",
    "title": "Login with wrong password",
    "description": "Sign-in is rejected.",
    "acceptance_criteria": ["The API responds with 401", "The error is shown"],
}


def test_one_ticket_becomes_one_chunk_with_criteria():
    doc = ticket_to_document(TICKET)
    assert doc.page_content.startswith("Login with wrong password\n\nSign-in is rejected.")
    assert "Acceptance criteria:\n- The API responds with 401\n- The error is shown" in doc.page_content


def test_metadata_is_filterable_and_chroma_safe():
    doc = ticket_to_document({**TICKET, "created": None})
    assert doc.metadata == {
        "source": "jira", "ticket_id": "QA-102", "type": "Story", "feature": "auth", "created": "",
    }


def test_ticket_without_criteria():
    doc = ticket_to_document({"id": "QA-1", "title": "T", "description": "D"})
    assert doc.page_content == "T\n\nD"


def test_every_eval_case_points_at_a_real_ticket():
    ids = {t["id"] for t in load_sample_tickets()}
    with open(DATASET) as f:
        cases = json.load(f)
    assert cases and all(c["expected_ticket"] in ids for c in cases)


def test_reciprocal_rank():
    assert reciprocal_rank("A", ["A", "B", "C"]) == 1.0
    assert reciprocal_rank("B", ["A", "B", "C"]) == 0.5
    assert reciprocal_rank("Z", ["A", "B", "C"]) == 0.0
