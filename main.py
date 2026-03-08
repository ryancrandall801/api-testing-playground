from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional
from sqlmodel import Session, select

from executor import run_test_case

from db import create_db_and_tables, engine
from models import TestSuite

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


class Assertion(BaseModel):
    type: str
    expected: Any


class TestCase(BaseModel):
    method: str
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    assertions: list[Assertion]


class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None


@app.post("/run-test")
def run_test(test_case: TestCase):
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