from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

from executor import run_test_case

app = FastAPI()


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


@app.post("/run-test")
def run_test(test_case: TestCase):
    result = run_test_case(test_case.model_dump())
    return result