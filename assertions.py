def get_json_value(data, path):
    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None

    return value


def check_status_code_equals(response, duration_ms, assertion):
    expected = assertion["expected"]
    actual = response.status_code
    passed = actual == expected

    return {
        "type": assertion["type"],
        "passed": passed,
        "actual": actual,
        "message": f"Expected status code {expected}, got {actual}",
    }


def check_response_time_lt(response, duration_ms, assertion):
    expected = assertion["expected"]
    actual = duration_ms
    passed = actual < expected

    return {
        "type": assertion["type"],
        "passed": passed,
        "actual": actual,
        "message": f"Expected response time < {expected}ms, got {actual}ms",
    }


def check_body_contains(response, duration_ms, assertion):
    expected = assertion["expected"]
    actual = response.text
    passed = expected in actual

    return {
        "type": assertion["type"],
        "passed": passed,
        "actual": expected if passed else response.text[:200],
        "message": f'Expected response body to contain "{expected}"',
    }


def check_json_path_exists(response, duration_ms, assertion):
    path = assertion["expected"]

    try:
        json_data = response.json()
        value = get_json_value(json_data, path)
        passed = value is not None

        return {
            "type": assertion["type"],
            "passed": passed,
            "actual": value,
            "message": f"Expected JSON path '{path}' to exist",
        }
    except Exception:
        return {
            "type": assertion["type"],
            "passed": False,
            "actual": None,
            "message": "Response was not valid JSON",
        }


ASSERTION_HANDLERS = {
    "status_code_equals": check_status_code_equals,
    "response_time_lt": check_response_time_lt,
    "body_contains": check_body_contains,
    "json_path_exists": check_json_path_exists,
}


def evaluate_assertions(response, duration_ms, assertions):
    results = []

    for assertion in assertions:
        assertion_type = assertion["type"]
        handler = ASSERTION_HANDLERS.get(assertion_type)

        if handler:
            result = handler(response, duration_ms, assertion)
        else:
            result = {
                "type": assertion_type,
                "passed": False,
                "actual": None,
                "message": f"Unknown assertion type: {assertion_type}",
            }

        results.append(result)

    return results