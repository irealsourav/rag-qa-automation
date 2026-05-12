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

    # Confluence
    CONFLUENCE_URL: str = os.getenv("CONFLUENCE_URL", "")
    CONFLUENCE_TOKEN: str = os.getenv("CONFLUENCE_TOKEN", "")
    CONFLUENCE_SPACE_KEY: str = os.getenv("CONFLUENCE_SPACE_KEY", "PROD")

    # Paths
    CODEBASE_PATH: str = os.getenv("CODEBASE_PATH", "./tests")
    TEST_RESULTS_PATH: str = os.getenv("TEST_RESULTS_PATH", "./reports")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # LLM
    LLM_MODEL: str = "claude-sonnet-4-5-20251001"
    MAX_TOKENS: int = 2048
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5

config = Config()
