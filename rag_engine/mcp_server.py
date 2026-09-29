"""
MCP server: lets an AI client (Claude Code, Claude Desktop, ...) work with Jira through
a small set of tools. The client's AI decides when to call them; this file decides what
they are allowed to do.

    python -m rag_engine.mcp_server     # normally started by the client, see .mcp.json

It talks to the client over stdio, so nothing here may print to stdout (stdout carries
the MCP messages). Errors are raised as ToolError so the AI sees the real reason.
"""
from typing import Dict, List, Optional

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from rag_engine.config import config
from rag_engine.models import TestCase
from rag_engine.sources.jira import writer
from rag_engine.sources.jira.client import JiraClient, JiraError
from rag_engine.sources.jira.loader import JiraLoader

server = MCPServer(
    name="rag-qa-jira",
    instructions=(
        "Tools for the team's Jira. Read issues before changing anything. "
        "Manual test cases are created as separate issues linked to their story."
    ),
)

READ_ONLY = ToolAnnotations(read_only_hint=True)
CREATES_ISSUES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False)


def _client() -> JiraClient:
    # Created per call, so a missing .env setting becomes a clear tool error, not a crash
    try:
        return JiraClient()
    except JiraError as e:
        raise ToolError(str(e))


@server.tool(annotations=READ_ONLY)
def get_issue(issue_key: str) -> Dict:
    """Read one Jira issue: summary, type, status, description, labels and linked issues."""
    client = _client()
    fields = ["summary", "description", "issuetype", "status", "labels", "project", "issuelinks"]
    try:
        issue = client.get_issue(issue_key, fields)
    except JiraError as e:
        raise ToolError(str(e))
    f = issue["fields"]
    return {
        "key": issue_key,
        "url": client.browse_url(issue_key),
        "project": f["project"]["key"],
        "type": f["issuetype"]["name"],
        "status": f["status"]["name"],
        "summary": f.get("summary", ""),
        "description": JiraLoader(client)._extract_text(f.get("description")),
        "labels": f.get("labels", []),
        "links": [_link(link) for link in f.get("issuelinks", [])],
    }


@server.tool(annotations=READ_ONLY)
def search_issues(jql: str, max_results: int = 20) -> List[Dict]:
    """
    Search Jira with JQL. The query must be limited, for example with a project:
    'project = QA AND issuetype = Story ORDER BY created DESC'.
    """
    client = _client()
    try:
        issues = client.search(jql, ["summary", "issuetype", "status"], max_results=max_results)
    except JiraError as e:
        raise ToolError(str(e))
    return [
        {
            "key": i["key"],
            "summary": i["fields"]["summary"],
            "type": i["fields"]["issuetype"]["name"],
            "status": i["fields"]["status"]["name"],
        }
        for i in issues
    ]


@server.tool(annotations=CREATES_ISSUES)
def create_story(
    summary: str,
    description: str,
    acceptance_criteria: List[str],
    project_key: Optional[str] = None,
    labels: Optional[List[str]] = None,
) -> Dict:
    """
    Create a user story. The description should say who wants what and why; each
    acceptance criterion should be one testable statement. Uses JIRA_PROJECT_KEY when no
    project is given. Returns the new issue key and URL.
    """
    client = _client()
    try:
        return writer.create_story(
            client, project_key or config.JIRA_PROJECT_KEY, summary, description,
            acceptance_criteria, labels,
        )
    except JiraError as e:
        raise ToolError(str(e))


@server.tool(annotations=CREATES_ISSUES)
def create_manual_test_cases(story_key: str, test_cases: List[TestCase]) -> List[Dict]:
    """
    Create manual test cases for a story, one issue each, linked to the story. Cover the
    story's acceptance criteria with happy-path, edge-case and negative tests; steps must
    be concrete actions a tester can follow. Returns the new issue keys and URLs.
    """
    if not test_cases:
        raise ToolError("test_cases is empty; nothing to create")
    client = _client()
    try:
        return writer.create_test_cases(client, story_key, test_cases)
    except JiraError as e:
        raise ToolError(str(e))


def _link(link: Dict) -> Dict:
    """A Jira issue link, from the point of view of the issue that was read."""
    if "outwardIssue" in link:
        other, relation = link["outwardIssue"], link["type"]["outward"]
    else:
        other, relation = link["inwardIssue"], link["type"]["inward"]
    return {"relation": relation, "key": other["key"], "summary": other["fields"]["summary"]}


if __name__ == "__main__":
    server.run(transport="stdio")
