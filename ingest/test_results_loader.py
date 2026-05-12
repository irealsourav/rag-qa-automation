import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
from config import config


class TestResultsLoader:
    """
    Parses JUnit XML / Allure XML test result reports.
    Extracts pass/fail patterns, flaky indicators and error messages.
    """

    def __init__(self, results_path: str = None):
        self.path = Path(results_path or config.TEST_RESULTS_PATH)

    def load_all(self) -> List[Dict]:
        docs = []
        if not self.path.exists():
            print(f"[TestResultsLoader] Path not found: {self.path}")
            return docs

        for xml_file in self.path.rglob("*.xml"):
            results = self._parse_junit_xml(xml_file)
            docs.extend(results)
        return docs

    def _parse_junit_xml(self, file_path: Path) -> List[Dict]:
        docs = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            suites = root.findall(".//testsuite") or [root]

            for suite in suites:
                suite_name = suite.get("name", "Unknown Suite")
                for case in suite.findall("testcase"):
                    doc = self._parse_testcase(case, suite_name, str(file_path))
                    docs.append(doc)
        except Exception as e:
            print(f"[TestResultsLoader] Failed to parse {file_path}: {e}")
        return docs

    def _parse_testcase(self, case: ET.Element, suite_name: str, file_path: str) -> Dict:
        name = case.get("name", "unknown")
        classname = case.get("classname", "")
        time = float(case.get("time", 0))

        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")

        if failure is not None:
            status = "FAILED"
            message = failure.get("message", failure.text or "")
        elif error is not None:
            status = "ERROR"
            message = error.get("message", error.text or "")
        elif skipped is not None:
            status = "SKIPPED"
            message = skipped.get("message", "")
        else:
            status = "PASSED"
            message = ""

        content = (
            f"Test: {name}\n"
            f"Suite: {suite_name}\n"
            f"Class: {classname}\n"
            f"Status: {status}\n"
            f"Duration: {time:.2f}s\n"
        )
        if message:
            content += f"Message: {message}\n"

        return {
            "id": f"{suite_name}::{name}",
            "source": "test_results",
            "test_name": name,
            "suite": suite_name,
            "classname": classname,
            "status": status,
            "duration": time,
            "message": message,
            "file": file_path,
            "content": content,
        }

    def get_flaky_candidates(self, min_runs: int = 2) -> List[Dict]:
        """
        Identify tests that appear multiple times with mixed statuses —
        a strong signal for flakiness.
        """
        all_results = self.load_all()
        test_map: Dict[str, List[str]] = {}
        for r in all_results:
            key = r["test_name"]
            test_map.setdefault(key, []).append(r["status"])

        flaky = []
        for name, statuses in test_map.items():
            if len(statuses) >= min_runs:
                unique = set(statuses)
                if "PASSED" in unique and ("FAILED" in unique or "ERROR" in unique):
                    flaky.append({
                        "test_name": name,
                        "statuses": statuses,
                        "flaky_score": statuses.count("FAILED") / len(statuses),
                    })

        return sorted(flaky, key=lambda x: x["flaky_score"], reverse=True)
