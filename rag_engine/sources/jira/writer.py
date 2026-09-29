"""
Writes to Jira: creates stories and manual test cases.

Used by the MCP server (rag_engine/mcp_server.py) and by features/jira_publisher.py.
Works on plain Jira Cloud (no test-management plugin): issue types, the test label and the
link type come from config (.env).
"""
from typing import Dict, List

from rag_engine.config import config
from rag_engine.models import TestCase
from rag_engine.sources.jira.client import (
    JiraClient, adf_bullet_list, adf_doc, adf_heading, adf_ordered_list, adf_paragraph,
)


def create_story(
    client: JiraClient,
    project_key: str,
    summary: str,
    description: str,
    acceptance_criteria: List[str],
    labels: List[str] = None,
) -> Dict:
    """Creates a story and returns its key and URL."""
    issue_type_id = client.issue_type_id(project_key, config.JIRA_STORY_ISSUE_TYPE)
    key = client.create_issue({
        "project": {"key": project_key},
        "issuetype": {"id": issue_type_id},
        "summary": summary[:255],  # Jira's limit for summaries
        "description": describe_story(description, acceptance_criteria),
        "labels": labels or [],
    })
    return {"key": key, "url": client.browse_url(key)}


def create_test_cases(
    client: JiraClient,
    story_key: str,
    cases: List[TestCase],
    project_key: str = None,
) -> List[Dict]:
    """
    Creates one issue per test case in the story's project and links each one to the
    story. Returns the created keys and URLs.
    """
    if project_key is None:
        # Reading the story first also checks that it exists before anything is created
        project_key = client.get_issue(story_key, ["project"])["fields"]["project"]["key"]
    issue_type_id = client.issue_type_id(project_key, config.JIRA_TEST_ISSUE_TYPE)

    created = []
    for case in cases:
        key = client.create_issue({
            "project": {"key": project_key},
            "issuetype": {"id": issue_type_id},
            "summary": f"[Test] {case.title}"[:255],
            "description": describe_test_case(case, story_key),
            "labels": [config.JIRA_TEST_LABEL, case.category.replace("_", "-")],
        })
        # "Relates" reads the same both ways; for directional types the story is inward
        client.link_issues(config.JIRA_LINK_TYPE, story_key, key)
        created.append({
            "key": key,
            "url": client.browse_url(key),
            "title": case.title,
            "category": case.category,
        })
    return created


def describe_story(description: str, acceptance_criteria: List[str]) -> Dict:
    blocks = [adf_paragraph(description)]
    if acceptance_criteria:
        blocks += [adf_heading("Acceptance criteria"), adf_bullet_list(acceptance_criteria)]
    return adf_doc(*blocks)


def describe_test_case(case: TestCase, story_key: str) -> Dict:
    return adf_doc(
        adf_paragraph(f"Test case for {story_key}, created by rag-qa-automation."),
        adf_paragraph(case.category.replace("_", " "), bold_prefix="Category: "),
        adf_paragraph(case.preconditions, bold_prefix="Preconditions: "),
        adf_heading("Steps"),
        adf_ordered_list(case.steps),
        adf_paragraph(case.expected_result, bold_prefix="Expected result: "),
    )
