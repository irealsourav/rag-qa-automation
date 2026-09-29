"""
A fake Jira for unit tests: answers HTTP calls from a list of routes, so tests never
need network access or a real Jira account.
"""
from rag_engine.sources.jira.client import JiraClient


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
