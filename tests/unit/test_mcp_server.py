"""
Tests the MCP server the way an AI client uses it: a real MCP Client connects to the
server in memory and calls its tools. Jira is faked (tests/unit/jira_fakes.py).
"""
import asyncio
import json

from mcp import Client

from rag_engine import mcp_server
from rag_engine.sources.jira.client import JiraError
from tests.unit.jira_fakes import make_client

STORY_ISSUE = {"fields": {
    "summary": "Password reset by email", "project": {"key": "QA"},
    "issuetype": {"name": "Story"}, "status": {"name": "To Do"}, "labels": ["auth"],
    "description": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Users can reset a forgotten password."}]}]},
    "issuelinks": [{"type": {"inward": "relates to", "outward": "relates to"},
                    "outwardIssue": {"key": "QA-21", "fields": {"summary": "[Test] Reset link expires"}}}],
}}

TEST_CASE = {
    "title": "Reset link works once",
    "category": "edge_case",
    "preconditions": "User requested a reset email",
    "steps": ["Open the reset link", "Set a new password", "Open the same link again"],
    "expected_result": "The second visit says the link has already been used",
}


def use_fake_jira(monkeypatch, routes):
    client = make_client(routes)
    monkeypatch.setattr(mcp_server, "_client", lambda: client)
    return client


def call(tool, arguments):
    """Calls one tool through an in-memory MCP client and returns (is_error, result)."""
    async def run():
        async with Client(mcp_server.server) as client:
            return await client.call_tool(tool, arguments)
    result = asyncio.run(run())
    if result.is_error:
        return True, result.content[0].text
    # List results come as one content block per item, plus a structured copy under "result"
    if result.structured_content is not None:
        return False, result.structured_content.get("result", result.structured_content)
    return False, json.loads(result.content[0].text)


def test_lists_the_four_jira_tools():
    async def run():
        async with Client(mcp_server.server) as client:
            return (await client.list_tools()).tools
    tools = {t.name: t for t in asyncio.run(run())}

    assert set(tools) == {"get_issue", "search_issues", "create_story", "create_manual_test_cases"}
    assert tools["get_issue"].annotations.read_only_hint is True
    assert tools["create_story"].annotations.read_only_hint is False
    # The AI client sees the TestCase fields it has to fill in
    schema = json.dumps(tools["create_manual_test_cases"].input_schema)
    assert all(field in schema for field in ["preconditions", "steps", "expected_result", "edge_case"])


def test_create_story_with_acceptance_criteria(monkeypatch):
    jira = use_fake_jira(monkeypatch, [
        ("GET", "/createmeta/QA/issuetypes", {"issueTypes": [{"id": "10001", "name": "Story"}]}),
        ("POST", "/rest/api/3/issue", {"key": "QA-20"}),
    ])
    is_error, result = call("create_story", {
        "summary": "Password reset by email",
        "description": "As a user I want to reset my password so that I can sign in again.",
        "acceptance_criteria": ["A reset email is sent", "The link works once"],
        "project_key": "QA",
    })

    assert not is_error
    assert result == {"key": "QA-20", "url": "https://example.atlassian.net/browse/QA-20"}
    fields = jira.session.calls[1][2]["json"]["fields"]
    assert fields["issuetype"] == {"id": "10001"}
    criteria = fields["description"]["content"][-1]
    assert criteria["type"] == "bulletList" and len(criteria["content"]) == 2


def test_create_manual_test_cases_links_them_to_the_story(monkeypatch):
    jira = use_fake_jira(monkeypatch, [
        ("GET", "/rest/api/3/issue/QA-20", {"fields": {"project": {"key": "QA"}}}),
        ("GET", "/createmeta/QA/issuetypes", {"issueTypes": [{"id": "10002", "name": "Task"}]}),
        ("POST", "/rest/api/3/issue", {"key": "QA-22"}),
        ("POST", "/rest/api/3/issueLink", None),
    ])
    is_error, result = call("create_manual_test_cases", {"story_key": "QA-20", "test_cases": [TEST_CASE]})

    assert not is_error
    assert [r["key"] for r in result] == ["QA-22"]
    created = jira.session.calls[2][2]["json"]["fields"]
    assert created["summary"] == "[Test] Reset link works once"
    assert created["labels"] == ["ai-generated-test", "edge-case"]
    link = jira.session.calls[3][2]["json"]
    assert link["inwardIssue"] == {"key": "QA-20"} and link["outwardIssue"] == {"key": "QA-22"}


def test_get_issue_returns_plain_text_and_links(monkeypatch):
    use_fake_jira(monkeypatch, [("GET", "/rest/api/3/issue/QA-20", STORY_ISSUE)])
    is_error, result = call("get_issue", {"issue_key": "QA-20"})

    assert not is_error
    assert result["description"] == "Users can reset a forgotten password."
    assert result["links"] == [{"relation": "relates to", "key": "QA-21", "summary": "[Test] Reset link expires"}]


def test_empty_test_case_list_is_rejected(monkeypatch):
    use_fake_jira(monkeypatch, [])
    is_error, message = call("create_manual_test_cases", {"story_key": "QA-20", "test_cases": []})
    assert is_error and "nothing to create" in message


def test_jira_errors_reach_the_ai_client(monkeypatch):
    use_fake_jira(monkeypatch, [])  # no routes: every request gets a 404
    is_error, message = call("get_issue", {"issue_key": "QA-999"})
    assert is_error and "404" in message


def test_missing_credentials_give_a_clear_message(monkeypatch):
    def no_credentials():
        raise JiraError("Set JIRA_URL, JIRA_EMAIL and JIRA_TOKEN in .env")
    monkeypatch.setattr(mcp_server, "JiraClient", no_credentials)
    is_error, message = call("search_issues", {"jql": "project = QA"})
    assert is_error and "Set JIRA_URL" in message
