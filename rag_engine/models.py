"""
Shared data shapes. Plain Pydantic models with no heavy imports, so any part of the
engine (sources, features, the MCP server) can use them.
"""
from typing import List, Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """One manual test case."""
    __test__ = False  # not a pytest test class

    title: str = Field(description="Short name of what is being tested")
    category: Literal["happy_path", "edge_case", "negative"]
    preconditions: str = Field(description="What must be true before the test starts")
    steps: List[str] = Field(description="The actions to perform, in order")
    expected_result: str = Field(description="What should happen if the feature works")


class TestSuite(BaseModel):
    __test__ = False  # not a pytest test class

    test_cases: List[TestCase]
