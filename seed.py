import json

from sqlmodel import Session, select

from db import engine
from models import TestSuite, TestCase


def seed_demo_data():
    with Session(engine) as session:
        existing_suite = session.exec(
            select(TestSuite).where(TestSuite.name == "User API Smoke Tests")
        ).first()

        if existing_suite:
            return

        suite = TestSuite(
            name="User API Smoke Tests",
            description="Basic validation tests for user endpoints",
        )
        session.add(suite)
        session.commit()
        session.refresh(suite)

        case = TestCase(
            suite_id=suite.id,
            name="Get user 1",
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1",
            headers_json=None,
            params_json=None,
            json_body=None,
            assertions_json=json.dumps([
                {"type": "status_code_equals", "expected": 200},
                {"type": "json_path_exists", "expected": "email"},
                {"type": "json_path_exists", "expected": "address.city"},
            ]),
        )

        session.add(case)
        session.commit()