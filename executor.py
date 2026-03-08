import httpx
import time
from assertions import evaluate_assertions


def run_test_case(test_case):
    method = test_case["method"]
    url = test_case["url"]
    assertions = test_case["assertions"]

    start = time.time()

    response = httpx.request(method, url)

    duration_ms = int((time.time() - start) * 1000)

    results = evaluate_assertions(response, duration_ms, assertions)

    passed = all(r["passed"] for r in results)

    return {
        "status": "passed" if passed else "failed",
        "response_status": response.status_code,
        "response_time_ms": duration_ms,
        "assertion_results": results,
    }