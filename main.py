import json

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel
from typing import Any, Optional, Literal
from sqlmodel import Session, select

from executor import run_test_case
from db import create_db_and_tables, engine
from models import TestSuite, TestCase
from seed import seed_demo_data

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_demo_data()


class Assertion(BaseModel):
    type: str
    expected: Any


class RunTestRequest(BaseModel):
    method: HttpMethod
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    assertions: list[Assertion]


class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TestCaseCreate(BaseModel):
    suite_id: int
    name: str
    method: HttpMethod
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    assertions: list[dict[str, Any]]


@app.post("/run-test")
def run_test(test_case: RunTestRequest):
    result = run_test_case(test_case.model_dump())
    return result


@app.post("/suites")
def create_suite(suite: TestSuiteCreate):
    db_suite = TestSuite(name=suite.name, description=suite.description)

    with Session(engine) as session:
        session.add(db_suite)
        session.commit()
        session.refresh(db_suite)

        return db_suite


@app.get("/suites")
def get_suites():
    with Session(engine) as session:
        suites = session.exec(select(TestSuite)).all()
        return suites


@app.post("/cases")
def create_test_case(test_case: TestCaseCreate):
    with Session(engine) as session:
        suite = session.get(TestSuite, test_case.suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        db_case = TestCase(
            suite_id=test_case.suite_id,
            name=test_case.name,
            method=test_case.method,
            url=test_case.url,
            headers_json=json.dumps(test_case.headers) if test_case.headers else None,
            params_json=json.dumps(test_case.params) if test_case.params else None,
            json_body=json.dumps(test_case.json_body) if test_case.json_body else None,
            assertions_json=json.dumps(test_case.assertions),
        )

        session.add(db_case)
        session.commit()
        session.refresh(db_case)

        return db_case


@app.post("/cases/{case_id}/run")
def run_saved_test(case_id: int):
    with Session(engine) as session:
        db_case = session.get(TestCase, case_id)

        if not db_case:
            raise HTTPException(status_code=404, detail="Test case not found")

        test_case_dict = {
            "method": db_case.method,
            "url": db_case.url,
            "headers": json.loads(db_case.headers_json) if db_case.headers_json else None,
            "params": json.loads(db_case.params_json) if db_case.params_json else None,
            "json_body": json.loads(db_case.json_body) if db_case.json_body else None,
            "assertions": json.loads(db_case.assertions_json),
        }

        result = run_test_case(test_case_dict)

        return result


@app.get("/suites/{suite_id}/cases")
def get_test_cases_for_suite(suite_id: int = Path(gt=0)):
    with Session(engine) as session:
        suite = session.get(TestSuite, suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        statement = select(TestCase).where(TestCase.suite_id == suite_id)
        cases = session.exec(statement).all()

        return cases