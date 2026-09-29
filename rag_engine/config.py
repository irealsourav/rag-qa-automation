from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Jira
    JIRA_URL: str = os.getenv("JIRA_URL", "")
    JIRA_TOKEN: str = os.getenv("JIRA_TOKEN", "")
    JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
    JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "QA")
    # Issue type used when creating stories (e.g. through the MCP server)
    JIRA_STORY_ISSUE_TYPE: str = os.getenv("JIRA_STORY_ISSUE_TYPE", "Story")
    # How generated test cases are created in Jira
    JIRA_TEST_ISSUE_TYPE: str = os.getenv("JIRA_TEST_ISSUE_TYPE", "Task")
    JIRA_TEST_LABEL: str = os.getenv("JIRA_TEST_LABEL", "ai-generated-test")
    JIRA_LINK_TYPE: str = os.getenv("JIRA_LINK_TYPE", "Relates")

    # Confluence
    CONFLUENCE_URL: str = os.getenv("CONFLUENCE_URL", "")
    CONFLUENCE_TOKEN: str = os.getenv("CONFLUENCE_TOKEN", "")
    # Same Atlassian account as Jira unless set separately
    CONFLUENCE_EMAIL: str = os.getenv("CONFLUENCE_EMAIL", os.getenv("JIRA_EMAIL", ""))
    CONFLUENCE_SPACE_KEY: str = os.getenv("CONFLUENCE_SPACE_KEY", "PROD")

    # Paths
    CODEBASE_PATH: str = os.getenv("CODEBASE_PATH", "./tests")
    TEST_RESULTS_PATH: str = os.getenv("TEST_RESULTS_PATH", "./reports")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # LLM
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-5")
    # Sonnet 5 thinks before answering and thinking tokens count toward this limit
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "16000"))
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5


config = Config()
