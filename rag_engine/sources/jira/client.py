from typing import Dict, List, Optional

import requests

from rag_engine.config import config


class JiraError(Exception):
    pass


class JiraClient:
    """
    Minimal Jira Cloud REST v3 client.
    Authenticates with Basic auth (account email + API token), which is what Jira Cloud
    API tokens require. Create a token at https://id.atlassian.com/manage-profile/security/api-tokens
    """

    def __init__(self, base_url: str = None, email: str = None, token: str = None):
        self.base_url = (base_url or config.JIRA_URL).rstrip("/")
        email = email or config.JIRA_EMAIL
        token = token or config.JIRA_TOKEN
        if not (self.base_url and email and token):
            raise JiraError("Set JIRA_URL, JIRA_EMAIL and JIRA_TOKEN in .env")
        self.session = requests.Session()
        self.session.auth = (email, token)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        response = self.session.request(method, f"{self.base_url}{path}", timeout=30, **kwargs)
        if not response.ok:
            raise JiraError(f"{method} {path} failed with {response.status_code}: {response.text[:500]}")
        return response.json() if response.content else {}

    def search(self, jql: str, fields: List[str], max_results: int = 200) -> List[Dict]:
        """Runs a JQL search, following nextPageToken until max_results issues are collected."""
        issues: List[Dict] = []
        params = {"jql": jql, "fields": ",".join(fields), "maxResults": min(max_results, 100)}
        while len(issues) < max_results:
            page = self._request("GET", "/rest/api/3/search/jql", params=params)
            issues.extend(page.get("issues", []))
            if page.get("isLast", True) or not page.get("nextPageToken"):
                break
            params["nextPageToken"] = page["nextPageToken"]
        return issues[:max_results]

    def get_issue(self, key: str, fields: List[str]) -> Dict:
        return self._request("GET", f"/rest/api/3/issue/{key}", params={"fields": ",".join(fields)})

    def issue_type_id(self, project_key: str, name: str) -> str:
        page = self._request("GET", f"/rest/api/3/issue/createmeta/{project_key}/issuetypes")
        types = page.get("issueTypes") or page.get("createMetaIssueType") or []
        for issue_type in types:
            if issue_type.get("name", "").lower() == name.lower():
                return issue_type["id"]
        available = ", ".join(t.get("name", "") for t in types)
        raise JiraError(f"Issue type '{name}' not found in {project_key}. Available: {available}")

    def create_issue(self, fields: Dict) -> str:
        """Creates an issue and returns its key, e.g. QA-42."""
        return self._request("POST", "/rest/api/3/issue", json={"fields": fields})["key"]

    def link_issues(self, link_type: str, inward_key: str, outward_key: str):
        self._request("POST", "/rest/api/3/issueLink", json={
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        })

    def browse_url(self, key: str) -> str:
        return f"{self.base_url}/browse/{key}"


# ------------------------------------------------------------ Atlassian Document Format helpers

def adf_text(text: str) -> Dict:
    return {"type": "text", "text": text}


def adf_paragraph(text: str, bold_prefix: Optional[str] = None) -> Dict:
    content = []
    if bold_prefix:
        content.append({"type": "text", "text": bold_prefix, "marks": [{"type": "strong"}]})
    if text:
        content.append(adf_text(text))
    return {"type": "paragraph", "content": content}


def adf_heading(text: str, level: int = 3) -> Dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [adf_text(text)]}


def adf_ordered_list(items: List[str]) -> Dict:
    return {
        "type": "orderedList",
        "content": [{"type": "listItem", "content": [adf_paragraph(item)]} for item in items],
    }


def adf_bullet_list(items: List[str]) -> Dict:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [adf_paragraph(item)]} for item in items],
    }


def adf_doc(*blocks: Dict) -> Dict:
    return {"type": "doc", "version": 1, "content": list(blocks)}
