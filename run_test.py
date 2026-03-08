from executor import run_test_case

test_case = {
    "method": "GET",
    "url": "https://jsonplaceholder.typicode.com/users/1",
    "assertions": [
        {"type": "status_code_equals", "expected": 200},
        {"type": "response_time_lt", "expected": 1000},
        {"type": "body_contains", "expected": "Leanne"}
    ]
}

result = run_test_case(test_case)

print("\nTest result:")
print(result)