import json

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Optional, Literal
from sqlmodel import Session, select

from executor import run_test_case
from db import create_db_and_tables, engine
from models import TestSuite, TestCase, TestRun
from seed import seed_demo_data

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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


def build_test_case_dict(db_case: TestCase) -> dict:
    return {
        "method": db_case.method,
        "url": db_case.url,
        "headers": json.loads(db_case.headers_json) if db_case.headers_json else None,
        "params": json.loads(db_case.params_json) if db_case.params_json else None,
        "json_body": json.loads(db_case.json_body) if db_case.json_body else None,
        "assertions": json.loads(db_case.assertions_json),
    }


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
def run_saved_test(case_id: int = Path(gt=0)):
    with Session(engine) as session:
        db_case = session.get(TestCase, case_id)

        if not db_case:
            raise HTTPException(status_code=404, detail="Test case not found")

        result = run_test_case(build_test_case_dict(db_case))

        test_run = TestRun(
            test_case_id=db_case.id,
            status=result["status"],
            response_status=result["response_status"],
            response_time_ms=result["response_time_ms"],
            response_body=result.get("response_body"),
            assertion_results_json=json.dumps(result["assertion_results"]),
        )

        session.add(test_run)
        session.commit()
        session.refresh(test_run)

        return {
            "test_run_id": test_run.id,
            "result": result,
        }


@app.get("/suites/{suite_id}/cases")
def get_test_cases_for_suite(suite_id: int = Path(gt=0)):
    with Session(engine) as session:
        suite = session.get(TestSuite, suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        statement = select(TestCase).where(TestCase.suite_id == suite_id)
        cases = session.exec(statement).all()

        return cases


@app.post("/suites/{suite_id}/run")
def run_test_suite(suite_id: int = Path(gt=0)):
    with Session(engine) as session:
        suite = session.get(TestSuite, suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        statement = select(TestCase).where(TestCase.suite_id == suite_id)
        db_cases = session.exec(statement).all()

        if not db_cases:
            raise HTTPException(status_code=404, detail="No test cases found for this suite")

        results = []

        for db_case in db_cases:
            run_result = run_test_case(build_test_case_dict(db_case))

            test_run = TestRun(
                test_case_id=db_case.id,
                status=run_result["status"],
                response_status=run_result["response_status"],
                response_time_ms=run_result["response_time_ms"],
                response_body=run_result.get("response_body"),
                assertion_results_json=json.dumps(run_result["assertion_results"]),
            )

            session.add(test_run)
            session.commit()
            session.refresh(test_run)

            results.append({
                "case_id": db_case.id,
                "case_name": db_case.name,
                "test_run_id": test_run.id,
                "result": run_result,
            })

        total_tests = len(results)
        passed = sum(1 for r in results if r["result"]["status"] == "passed")
        failed = total_tests - passed

        return {
            "suite_id": suite.id,
            "suite_name": suite.name,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "results": results,
        }


@app.get("/cases/{case_id}/runs")
def get_test_run_history(case_id: int = Path(gt=0)):
    with Session(engine) as session:
        db_case = session.get(TestCase, case_id)

        if not db_case:
            raise HTTPException(status_code=404, detail="Test case not found")

        statement = (
            select(TestRun)
            .where(TestRun.test_case_id == case_id)
            .order_by(TestRun.created_at.desc())
        )
        runs = session.exec(statement).all()

        return runs


@app.get("/runs/{run_id}")
def get_test_run(run_id: int = Path(gt=0)):
    with Session(engine) as session:
        test_run = session.get(TestRun, run_id)

        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        return test_run


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    with Session(engine) as session:
        suites = session.exec(select(TestSuite)).all()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "suites": suites,
            },
        )


@app.get("/ui/suites/{suite_id}", response_class=HTMLResponse)
def suite_detail(request: Request, suite_id: int = Path(gt=0)):
    with Session(engine) as session:
        suite = session.get(TestSuite, suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        statement = select(TestCase).where(TestCase.suite_id == suite_id)
        cases = session.exec(statement).all()

        return templates.TemplateResponse(
            "suite_detail.html",
            {
                "request": request,
                "suite": suite,
                "cases": cases,
            },
        )


@app.get("/ui/cases/{case_id}/runs", response_class=HTMLResponse)
def case_run_history(request: Request, case_id: int = Path(gt=0)):
    with Session(engine) as session:
        db_case = session.get(TestCase, case_id)

        if not db_case:
            raise HTTPException(status_code=404, detail="Test case not found")

        statement = (
            select(TestRun)
            .where(TestRun.test_case_id == case_id)
            .order_by(TestRun.created_at.desc())
        )
        runs = session.exec(statement).all()

        return templates.TemplateResponse(
            "case_runs.html",
            {
                "request": request,
                "test_case": db_case,
                "runs": runs,
            },
        )


@app.post("/ui/cases/{case_id}/run", response_class=HTMLResponse)
def run_saved_test_ui(request: Request, case_id: int = Path(gt=0)):
    with Session(engine) as session:
        db_case = session.get(TestCase, case_id)

        if not db_case:
            raise HTTPException(status_code=404, detail="Test case not found")

        result = run_test_case(build_test_case_dict(db_case))

        test_run = TestRun(
            test_case_id=db_case.id,
            status=result["status"],
            response_status=result["response_status"],
            response_time_ms=result["response_time_ms"],
            response_body=result.get("response_body"),
            assertion_results_json=json.dumps(result["assertion_results"]),
        )

        session.add(test_run)
        session.commit()
        session.refresh(test_run)

        return templates.TemplateResponse(
            "case_result.html",
            {
                "request": request,
                "test_case": db_case,
                "test_run": test_run,
                "result": result,
            },
        )


@app.post("/ui/suites/{suite_id}/run", response_class=HTMLResponse)
def run_test_suite_ui(request: Request, suite_id: int = Path(gt=0)):
    with Session(engine) as session:
        suite = session.get(TestSuite, suite_id)

        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        statement = select(TestCase).where(TestCase.suite_id == suite_id)
        db_cases = session.exec(statement).all()

        if not db_cases:
            raise HTTPException(status_code=404, detail="No test cases found for this suite")

        results = []

        for db_case in db_cases:
            run_result = run_test_case(build_test_case_dict(db_case))

            test_run = TestRun(
                test_case_id=db_case.id,
                status=run_result["status"],
                response_status=run_result["response_status"],
                response_time_ms=run_result["response_time_ms"],
                response_body=run_result.get("response_body"),
                assertion_results_json=json.dumps(run_result["assertion_results"]),
            )

            session.add(test_run)
            session.commit()
            session.refresh(test_run)

            results.append({
                "case": db_case,
                "test_run": test_run,
                "result": run_result,
            })

        total_tests = len(results)
        passed = sum(1 for r in results if r["result"]["status"] == "passed")
        failed = total_tests - passed

        return templates.TemplateResponse(
            "suite_result.html",
            {
                "request": request,
                "suite": suite,
                "results": results,
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
            },
        )


@app.get("/ui/runs/{run_id}", response_class=HTMLResponse)
def test_run_detail(request: Request, run_id: int = Path(gt=0)):
    with Session(engine) as session:
        test_run = session.get(TestRun, run_id)

        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        test_case = session.get(TestCase, test_run.test_case_id)

        assertion_results = json.loads(test_run.assertion_results_json)

        return templates.TemplateResponse(
            "run_detail.html",
            {
                "request": request,
                "test_run": test_run,
                "test_case": test_case,
                "assertion_results": assertion_results,
            },
        )