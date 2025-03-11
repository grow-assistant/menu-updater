# Scenario Tests Framework

This directory contains scenario-based tests for the AI Menu Updater application. These tests simulate complete interaction sequences with the application, testing end-to-end functionality with multi-turn conversations.

## Overview

Scenario tests are designed to verify that the application correctly handles complete user interactions, particularly focusing on maintaining context between related queries. Unlike unit or integration tests that focus on individual components, scenario tests validate the entire application flow.

## Structure

- `__init__.py` - Package initialization file
- `test_utils.py` - Core utilities for running scenario tests including mock implementations
- `test_order_queries.py` - Tests for order-related query scenarios
- `standalone_test_runner.py` - Command-line tool for running scenario tests

## Running Tests

You can run all scenario tests using:

```bash
python -m tests.scenarios.standalone_test_runner
```

To see available tests:

```bash
python -m tests.scenarios.standalone_test_runner --list
```

To run specific tests:

```bash
python -m tests.scenarios.standalone_test_runner --tests TestOrderQueries.test_order_completion_date_and_customer
```

## Creating New Test Scenarios

To create a new scenario test:

1. Create a new test file or add to an existing one, following the pattern in `test_order_queries.py`
2. Create a test class that inherits from `unittest.TestCase`
3. Implement test methods that use the `run_test` function from `test_utils`
4. Add validation functions to verify the expected behavior of each query
5. Import your new test module in `standalone_test_runner.py`
6. Add your test class to the `get_all_test_cases()` function

Example template for a new test:

```python
from typing import Dict, Any
import unittest
from tests.scenarios.test_utils import run_test, logger

class TestNewScenario(unittest.TestCase):
    def test_my_scenario(self):
        """
        Description of your multi-turn scenario
        """
        # Define query sequence
        queries = [
            "First query",
            "Follow-up query"
        ]
        
        # Define validation functions
        def validate_first_response(response: Dict[str, Any]) -> bool:
            # Validate first response
            return True
            
        def validate_second_response(response: Dict[str, Any]) -> bool:
            # Validate second response
            return True
            
        # Run the test
        results = run_test(
            test_name="My new scenario",
            queries=queries,
            validators=[validate_first_response, validate_second_response]
        )
        
        # Optional: Log results
        for i, result in enumerate(results):
            logger.info(f"Query {i+1} summary: {result.get('response_text')}")
```

## Extending the Mock Implementation

The scenario tests use a mock implementation to simulate the application's behavior. To extend this for new scenarios:

1. Open `test_utils.py`
2. Enhance the `MockQueryResult` class to handle your new query types
3. Add appropriate mock SQL queries in `_generate_mock_sql`
4. Add mock result data in `_generate_mock_results`
5. Add mock text responses in `_generate_mock_response`
6. Update the `run_scenario` method to track any necessary context between queries

## Best Practices

1. **Test complete conversations**: Each test should simulate a complete user interaction flow
2. **Maintain clear context**: Ensure follow-up queries properly reference previous queries
3. **Validate comprehensively**: Check SQL generation, response text, and appropriate context preservation
4. **Mock realistically**: Mock responses should closely match what the real system would produce
5. **Document expectations**: Use clear docstrings to document what each test is verifying

## FAQ

**Q: Why not use the real implementation?**
A: Using mocks allows tests to run quickly and reliably without external dependencies. For full end-to-end testing with the real implementation, integration tests are more appropriate.

**Q: How do I simulate a complex multi-turn conversation?**
A: Add more queries to the `queries` list and corresponding validators to verify each response.

**Q: How can I test error handling?**
A: Create scenarios that would trigger errors and update the MockQueryResult class to simulate appropriate error responses. 