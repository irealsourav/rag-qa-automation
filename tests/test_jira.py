import pytest

from ingest.jira_loader import JiraLoader
from integrations.jira import JiraClient, JiraError
from qa_outputs.jira_publisher import JiraTestPublisher
from qa_outputs.test_generator import TestCase, TestCaseGenerator


class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status
        self.ok = status < 400
        self.content = b"x" if body is not None else b""
        self.text = str(body)

    def json(self):
        return self.body


class FakeSession:
    """Records requests and answers from a list of (method, path suffix, body) routes."""

    def __init__(self, routes):
        self.routes, self.calls = list(routes), []

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append((method, url, kwargs))
        for i, (m, suffix, body) in enumerate(self.routes):
            if m == method and url.endswith(suffix):
                self.routes.pop(i)
                return FakeResponse(body)
        return FakeResponse({"errorMessages": ["no route"]}, status=404)


def make_client(routes):
    client = JiraClient("https://example.atlassian.net/", "me@example.com", "token")
    client.session = FakeSession(routes)
    return client


CASE = TestCase(
    title="Login with valid credentials",
    category="happy_path",
    preconditions="User exists",
    steps=["Open /login", "Submit valid email and password"],
    expected_result="User lands on the home page",
)


class FakeGenerator:
    def __init__(self):
        self.prompts = []

    def generate_cases(self, feature, framework="Cypress", count=5):
        self.prompts.append(feature)
        return [CASE] * count


class TestJiraClient:
    def test_requires_credentials(self, monkeypatch):
        monkeypatch.setattr("integrations.jira.config.JIRA_URL", "")
        with pytest.raises(JiraError):
            JiraClient(email="", token="")

    def test_search_uses_new_endpoint_and_follows_pages(self):
        client = make_client([
            ("GET", "/rest/api/3/search/jql", {"issues": [{"key": "QA-1"}], "nextPageToken": "abc", "isLast": False}),
            ("GET", "/rest/api/3/search/jql", {"issues": [{"key": "QA-2"}], "isLast": True}),
        ])
        issues = client.search("project = QA", ["summary", "status"])
        assert [i["key"] for i in issues] == ["QA-1", "QA-2"]
        first, second = client.session.calls
        assert first[2]["params"]["fields"] == "summary,status"
        assert second[2]["params"]["nextPageToken"] == "abc"

    def test_errors_include_status_and_body(self):
        client = make_client([])
        with pytest.raises(JiraError, match="404"):
            client.get_issue("QA-9", ["summary"])

    def test_issue_type_lookup_lists_available_types(self):
        client = make_client([("GET", "/issuetypes", {"issueTypes": [{"id": "1", "name": "Story"}]})])
        with pytest.raises(JiraError, match="Available: Story"):
            client.issue_type_id("QA", "Task")


class TestJiraLoader:
    def test_jql_skips_generated_tests(self):
        client = make_client([("GET", "/search/jql", {"issues": [], "isLast": True})])
        JiraLoader(client).fetch_issues(project_key="QA")
        jql = client.session.calls[0][2]["params"]["jql"]
        assert 'project = "QA"' in jql
        assert 'labels != "ai-generated-test"' in jql

    def test_parses_issue_with_empty_priority(self):
        fields = {"summary": "Checkout", "priority": None,
                  "issuetype": {"name": "Story"}, "status": {"name": "To Do"}}
        issue = {"key": "QA-3", "fields": fields}
        doc = JiraLoader(make_client([]))._parse_issue(issue)
        assert doc["priority"] == "Medium"
        assert "Title: Checkout" in doc["content"]


class TestJiraTestPublisher:
    STORY = {"fields": {"summary": "User login", "project": {"key": "QA"}, "description": {
        "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Users sign in with email."}]}]}}}

    def test_creates_linked_issues(self):
        client = make_client([
            ("GET", "/rest/api/3/issue/QA-7", self.STORY),
            ("GET", "/createmeta/QA/issuetypes", {"issueTypes": [{"id": "10002", "name": "Task"}]}),
            ("POST", "/rest/api/3/issue", {"key": "QA-8"}),
            ("POST", "/rest/api/3/issueLink", None),
            ("POST", "/rest/api/3/issue", {"key": "QA-9"}),
            ("POST", "/rest/api/3/issueLink", None),
        ])
        generator = FakeGenerator()
        created = JiraTestPublisher(generator=generator, client=client).publish("QA-7", count=2)

        assert [c["key"] for c in created] == ["QA-8", "QA-9"]
        assert created[0]["url"] == "https://example.atlassian.net/browse/QA-8"
        assert "Users sign in with email." in generator.prompts[0]

        fields = client.session.calls[2][2]["json"]["fields"]
        assert fields["issuetype"] == {"id": "10002"}
        assert fields["summary"] == "[Test] Login with valid credentials"
        assert fields["labels"] == ["ai-generated-test", "happy-path"]
        link = client.session.calls[3][2]["json"]
        assert link == {"type": {"name": "Relates"}, "inwardIssue": {"key": "QA-7"}, "outwardIssue": {"key": "QA-8"}}

    def test_dry_run_creates_nothing(self):
        client = make_client([("GET", "/rest/api/3/issue/QA-7", self.STORY)])
        created = JiraTestPublisher(generator=FakeGenerator(), client=client).publish("QA-7", count=3, dry_run=True)
        assert len(created) == 3 and all(c["key"] is None for c in created)
        assert [m for m, _, _ in client.session.calls] == ["GET"]

    def test_description_is_valid_adf(self):
        doc = JiraTestPublisher.description(CASE, "QA-7")
        assert doc["type"] == "doc" and doc["version"] == 1
        steps = next(b for b in doc["content"] if b["type"] == "orderedList")
        assert len(steps["content"]) == 2


def test_markdown_rendering():
    text = TestCaseGenerator.to_markdown([CASE, CASE])
    assert text.startswith("TC-1: Login with valid credentials")
    assert "TC-2:" in text
    assert "  2. Submit valid email and password" in text
