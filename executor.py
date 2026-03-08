import httpx
import time
from assertions import evaluate_assertions


def run_test_case(test_case):
    method = test_case["method"]
    url = test_case["url"]
    assertions = test_case["assertions"]

    headers = test_case.get("headers")
    params = test_case.get("params")
    json_body = test_case.get("json_body")

    start = time.time()

    response = httpx.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=10.0,
    )

    duration_ms = int((time.time() - start) * 1000)

    results = evaluate_assertions(response, duration_ms, assertions)

    passed = all(r["passed"] for r in results)

    return {
        "status": "passed" if passed else "failed",
        "response_status": response.status_code,
        "response_time_ms": duration_ms,
        "assertion_results": results,
        "response_body": response.text,
    }