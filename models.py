from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TestSuite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TestCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    suite_id: int = Field(foreign_key="testsuite.id")
    name: str
    method: str
    url: str
    headers_json: str | None = None
    params_json: str | None = None
    json_body: str | None = None
    assertions_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TestRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    test_case_id: int = Field(foreign_key="testcase.id")
    status: str
    response_status: int
    response_time_ms: int
    response_body: str | None = None
    assertion_results_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)