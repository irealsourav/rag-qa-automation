import requests
from typing import List, Dict
from config import config


class JiraLoader:
    """
    Fetches issues from Jira via REST API v3.
    Pulls stories, bugs, epics and their acceptance criteria.
    """

    def __init__(self):
        self.base_url = config.JIRA_URL
        self.headers = {
            "Authorization": f"Bearer {config.JIRA_TOKEN}",
            "Accept": "application/json",
        }

    def fetch_issues(
        self,
        project_key: str = None,
        issue_types: List[str] = None,
        max_results: int = 200,
    ) -> List[Dict]:
        project = project_key or config.JIRA_PROJECT_KEY
        types = ", ".join(issue_types or ["Story", "Bug", "Epic", "Task"])
        jql = f'project={project} AND issuetype in ({types}) AND status != Done'

        url = f"{self.base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": [
                "summary",
                "description",
                "issuetype",
                "status",
                "labels",
                "priority",
                "customfield_10016",  # story points
                "comment",
            ],
        }

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        issues = response.json().get("issues", [])
        return [self._parse_issue(i) for i in issues]

    def _parse_issue(self, issue: Dict) -> Dict:
        fields = issue.get("fields", {})
        description = self._extract_text(fields.get("description"))
        comments = self._extract_comments(fields.get("comment", {}).get("comments", []))

        return {
            "id": issue["key"],
            "source": "jira",
            "type": fields.get("issuetype", {}).get("name", "Unknown"),
            "title": fields.get("summary", ""),
            "description": description,
            "status": fields.get("status", {}).get("name", ""),
            "labels": fields.get("labels", []),
            "priority": fields.get("priority", {}).get("name", "Medium"),
            "comments": comments,
            "content": self._build_content(fields),
        }

    def _build_content(self, fields: Dict) -> str:
        parts = []
        parts.append(f"Title: {fields.get('summary', '')}")
        parts.append(f"Type: {fields.get('issuetype', {}).get('name', '')}")
        parts.append(f"Priority: {fields.get('priority', {}).get('name', '')}")
        desc = self._extract_text(fields.get("description"))
        if desc:
            parts.append(f"Description: {desc}")
        return "\n".join(parts)

    def _extract_text(self, adf_content) -> str:
        """Extract plain text from Atlassian Document Format (ADF)."""
        if not adf_content:
            return ""
        if isinstance(adf_content, str):
            return adf_content
        texts = []
        self._traverse_adf(adf_content, texts)
        return " ".join(texts).strip()

    def _traverse_adf(self, node: Dict, texts: List[str]):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                self._traverse_adf(child, texts)
        elif isinstance(node, list):
            for item in node:
                self._traverse_adf(item, texts)

    def _extract_comments(self, comments: List[Dict]) -> str:
        texts = []
        for comment in comments[:5]:
            body = self._extract_text(comment.get("body"))
            if body:
                texts.append(body)
        return " | ".join(texts)
