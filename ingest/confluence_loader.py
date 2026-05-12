import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from config import config


class ConfluenceLoader:
    """
    Fetches pages from Confluence via REST API.
    Strips HTML and returns clean plain text.
    """

    def __init__(self):
        self.base_url = config.CONFLUENCE_URL
        self.headers = {
            "Authorization": f"Bearer {config.CONFLUENCE_TOKEN}",
            "Accept": "application/json",
        }

    def fetch_pages(
        self,
        space_key: str = None,
        max_results: int = 100,
        labels: List[str] = None,
    ) -> List[Dict]:
        space = space_key or config.CONFLUENCE_SPACE_KEY
        url = f"{self.base_url}/rest/api/content"
        params = {
            "spaceKey": space,
            "expand": "body.storage,version,ancestors",
            "limit": max_results,
            "type": "page",
        }
        if labels:
            params["label"] = ",".join(labels)

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        pages = response.json().get("results", [])
        return [self._parse_page(p) for p in pages]

    def fetch_page_by_title(self, title: str, space_key: str = None) -> Dict:
        space = space_key or config.CONFLUENCE_SPACE_KEY
        url = f"{self.base_url}/rest/api/content"
        params = {
            "title": title,
            "spaceKey": space,
            "expand": "body.storage",
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return self._parse_page(results[0])
        return {}

    def _parse_page(self, page: Dict) -> Dict:
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        plain_text = self._html_to_text(html_body)
        ancestors = [a.get("title", "") for a in page.get("ancestors", [])]

        return {
            "id": page.get("id"),
            "source": "confluence",
            "title": page.get("title", ""),
            "space": page.get("space", {}).get("key", ""),
            "url": f"{self.base_url}/wiki{page.get('_links', {}).get('webui', '')}",
            "breadcrumb": " > ".join(ancestors + [page.get("title", "")]),
            "content": f"Title: {page.get('title', '')}\n\n{plain_text}",
            "version": page.get("version", {}).get("number", 1),
        }

    def _html_to_text(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "ac:structured-macro"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
