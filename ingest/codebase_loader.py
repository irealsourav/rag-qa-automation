import os
from pathlib import Path
from typing import List, Dict
from config import config

SUPPORTED_EXTENSIONS = {
    ".cy.js", ".cy.ts",   # Cypress
    ".spec.js", ".spec.ts",
    ".test.js", ".test.ts",
    ".py",                 # pytest
    ".java",               # JUnit / TestNG
}


class CodebaseLoader:
    """
    Walks the test codebase directory and loads test files.
    Supports Cypress (JS/TS), pytest (Python) and JUnit/TestNG (Java).
    """

    def __init__(self, codebase_path: str = None):
        self.path = Path(codebase_path or config.CODEBASE_PATH)

    def load_all(self) -> List[Dict]:
        documents = []
        if not self.path.exists():
            print(f"[CodebaseLoader] Path not found: {self.path}")
            return documents

        for root, _, files in os.walk(self.path):
            for file in files:
                file_path = Path(root) / file
                if self._is_test_file(file_path):
                    doc = self._load_file(file_path)
                    if doc:
                        documents.append(doc)
        return documents

    def load_file(self, file_path: str) -> Dict:
        return self._load_file(Path(file_path))

    def _is_test_file(self, path: Path) -> bool:
        name = path.name.lower()
        suffix = path.suffix.lower()
        if suffix == ".py" and ("test_" in name or "_test" in name):
            return True
        if suffix == ".java" and "test" in name.lower():
            return True
        for ext in [".cy.js", ".cy.ts", ".spec.js", ".spec.ts", ".test.js", ".test.ts"]:
            if name.endswith(ext):
                return True
        return False

    def _load_file(self, path: Path) -> Dict:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            framework = self._detect_framework(path, content)
            return {
                "id": str(path),
                "source": "codebase",
                "framework": framework,
                "file_path": str(path),
                "file_name": path.name,
                "content": (
                    f"File: {path.name}\n"
                    f"Framework: {framework}\n"
                    f"Path: {path}\n\n"
                    f"{content}"
                ),
            }
        except Exception as e:
            print(f"[CodebaseLoader] Failed to load {path}: {e}")
            return {}

    def _detect_framework(self, path: Path, content: str) -> str:
        name = path.name.lower()
        if ".cy." in name or "cypress" in content.lower():
            return "Cypress"
        if path.suffix == ".py":
            if "pytest" in content or "def test_" in content:
                return "pytest"
        if path.suffix == ".java":
            if "@Test" in content and "org.junit" in content:
                return "JUnit"
            if "@Test" in content and "testng" in content.lower():
                return "TestNG"
        return "Unknown"
