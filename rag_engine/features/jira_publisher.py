from typing import Dict, List

from rag_engine.config import config
from rag_engine.sources.jira.client import (
    JiraClient, adf_doc, adf_heading, adf_ordered_list, adf_paragraph,
)
from rag_engine.sources.jira.loader import JiraLoader
from rag_engine.features.test_generator import TestCase, TestCaseGenerator


class JiraTestPublisher:
    """
    Generates test cases for a Jira story and creates each one as an issue in the
    story's project, linked back to the story. Works on plain Jira Cloud (no test
    management plugin): the issue type, label and link type come from config.
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

        issue_type_id = self.client.issue_type_id(story["project"], config.JIRA_TEST_ISSUE_TYPE)
        created = []
        for case in cases:
            key = self.client.create_issue({
                "project": {"key": story["project"]},
                "issuetype": {"id": issue_type_id},
                "summary": f"[Test] {case.title}"[:255],
                "description": self.description(case, story_key),
                "labels": [config.JIRA_TEST_LABEL, case.category.replace("_", "-")],
            })
            # "Relates" reads the same both ways; for directional types the story is inward
            self.client.link_issues(config.JIRA_LINK_TYPE, story_key, key)
            created.append({
                "key": key,
                "url": self.client.browse_url(key),
                "title": case.title,
                "category": case.category,
            })
        return created

    @staticmethod
    def description(case: TestCase, story_key: str) -> Dict:
        return adf_doc(
            adf_paragraph(f"Generated from {story_key} by rag-qa-automation."),
            adf_paragraph(case.category.replace("_", " "), bold_prefix="Category: "),
            adf_paragraph(case.preconditions, bold_prefix="Preconditions: "),
            adf_heading("Steps"),
            adf_ordered_list(case.steps),
            adf_paragraph(case.expected_result, bold_prefix="Expected result: "),
        )
