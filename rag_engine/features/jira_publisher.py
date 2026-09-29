from typing import Dict, List

from rag_engine.sources.jira.client import JiraClient
from rag_engine.sources.jira.loader import JiraLoader
from rag_engine.sources.jira.writer import create_test_cases
from rag_engine.features.test_generator import TestCaseGenerator


class JiraTestPublisher:
    """
    Generates test cases for a Jira story with RAG + Claude, then creates each one as an
    issue linked back to the story (the Jira part is in sources/jira/writer.py).
    """

    def __init__(self, generator: TestCaseGenerator = None, client: JiraClient = None):
        self.client = client or JiraClient()
        self.generator = generator or TestCaseGenerator()

    def story_text(self, story_key: str) -> Dict:
        issue = self.client.get_issue(story_key, ["summary", "description", "project"])
        fields = issue["fields"]
        description = JiraLoader(self.client)._extract_text(fields.get("description"))
        return {
            "project": fields["project"]["key"],
            "summary": fields.get("summary", ""),
            "text": f"{story_key}: {fields.get('summary', '')}\n\n{description}".strip(),
        }

    def publish(
        self,
        story_key: str,
        count: int = 5,
        framework: str = "Cypress",
        dry_run: bool = False,
    ) -> List[Dict]:
        story = self.story_text(story_key)
        cases = self.generator.generate_cases(story["text"], framework=framework, count=count)
        if dry_run:
            return [{"key": None, "url": None, "title": c.title, "category": c.category} for c in cases]
        return create_test_cases(self.client, story_key, cases, project_key=story["project"])
