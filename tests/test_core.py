from pipeline.chunker import TextChunker
from ingest.test_results_loader import TestResultsLoader
from ingest.codebase_loader import CodebaseLoader


class TestChunker:
    def setup_method(self):
        self.chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    def test_short_text_not_split(self):
        text = "Short text that fits in one chunk."
        chunks = self.chunker._split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split(self):
        text = " ".join(["word"] * 200)
        chunks = self.chunker._split_text(text)
        assert len(chunks) > 1

    def test_empty_text_returns_empty(self):
        chunks = self.chunker._split_text("")
        assert chunks == []

    def test_chunk_documents_adds_chunk_id(self):
        docs = [{"id": "TEST-1", "content": "Some test content here."}]
        chunks = self.chunker.chunk_documents(docs)
        assert len(chunks) >= 1
        assert "chunk_id" in chunks[0]
        assert "chunk_index" in chunks[0]
        assert chunks[0]["original_id"] == "TEST-1"


class TestTestResultsLoader:
    def test_get_flaky_candidates_empty(self, tmp_path):
        loader = TestResultsLoader(str(tmp_path))
        flaky = loader.get_flaky_candidates()
        assert flaky == []

    def test_parse_junit_xml(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="LoginTests" tests="2" failures="1">
  <testcase name="test_login_success" classname="LoginTests" time="0.5"/>
  <testcase name="test_login_fail" classname="LoginTests" time="0.3">
    <failure message="AssertionError">Expected 200 got 401</failure>
  </testcase>
</testsuite>"""
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)
        loader = TestResultsLoader(str(tmp_path))
        results = loader.load_all()
        assert len(results) == 2
        statuses = [r["status"] for r in results]
        assert "PASSED" in statuses
        assert "FAILED" in statuses


class TestCodebaseLoader:
    def test_detect_cypress_file(self, tmp_path):
        test_file = tmp_path / "login.cy.js"
        test_file.write_text("describe('Login', () => { it('works', () => {}) })")
        loader = CodebaseLoader(str(tmp_path))
        docs = loader.load_all()
        assert len(docs) == 1
        assert docs[0]["framework"] == "Cypress"

    def test_detect_pytest_file(self, tmp_path):
        test_file = tmp_path / "test_login.py"
        test_file.write_text("def test_login(): assert True")
        loader = CodebaseLoader(str(tmp_path))
        docs = loader.load_all()
        assert len(docs) == 1
        assert docs[0]["framework"] == "pytest"

    def test_non_test_file_ignored(self, tmp_path):
        non_test = tmp_path / "utils.py"
        non_test.write_text("def helper(): pass")
        loader = CodebaseLoader(str(tmp_path))
        docs = loader.load_all()
        assert len(docs) == 0
