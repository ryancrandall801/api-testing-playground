def evaluate_assertions(response, duration_ms, assertions):
    results = []

    for assertion in assertions:

        if assertion["type"] == "status_code_equals":
            expected = assertion["expected"]
            actual = response.status_code
            passed = actual == expected

        elif assertion["type"] == "response_time_lt":
            expected = assertion["expected"]
            actual = duration_ms
            passed = actual < expected

        elif assertion["type"] == "body_contains":
            expected = assertion["expected"]
            actual = response.text
            passed = expected in actual

        else:
            passed = False
            actual = None

        results.append({
            "type": assertion["type"],
            "passed": passed,
            "actual": actual
        })

    return results