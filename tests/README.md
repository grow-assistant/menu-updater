# Test Documentation

## Test Organization

This test suite is organized into three main directories:

- **unit/**: Tests that verify individual components in isolation with mocked dependencies
- **integration/**: Tests that verify interactions between multiple components
- **performance/**: Tests that verify performance characteristics and timing

## Test Coverage

Current test coverage for key components:

| Module | Coverage | Description |
|--------|----------|-------------|
| orchestrator | 41% | Main workflow coordination |
| sql_generator | 60% | Database query generation |
| sql_executor | 64% | Database query execution |
| result_formatter | 92% | Query result formatting |
| sql_execution_layer | 81% | Database connection management |
| response_generator | 48% | Natural language response generation |
| rules_service | 44% | Business rules management |
| classifier | 95% | Query classification |

## Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run performance tests only
pytest tests/performance/

# Run tests with coverage
pytest --cov=services --cov-report=html

# Run tests by marker
pytest -m unit
pytest -m "not slow"
pytest -m "integration and not slow"
```

## Available Markers

- `unit`: Unit tests for individual components
- `integration`: Tests for component interactions
- `slow`: Tests that take longer than 1 second
- `fast`: Tests that run quickly (less than 1 second)
- `api`: Tests that interact with external APIs
- `db`: Tests that require database connections
- `smoke`: Basic tests to verify code is runnable

## Test Fixtures

### Configuration Fixtures

- `test_config`: Provides test configuration values
- `mock_settings`: Mocked Settings object with test configuration

### Service Mock Fixtures

- `mock_classifier`: Mocked ClassificationService
- `mock_sql_generator`: Mocked SQLGenerator 
- `mock_execution_service`: Mocked SQLExecutionLayer
- `mock_response_generator`: Mocked ResponseGenerator
- `mock_rules_manager`: Mocked RulesManager
- `mock_orchestrator`: Mocked OrchestratorService with all dependencies

### External API Mock Fixtures

- `mock_openai_client`: Mocked OpenAI client
- `mock_gemini_client`: Mocked Google Gemini client

## Adding New Tests

When adding new tests:

1. **Add appropriate markers**
   ```python
   @pytest.mark.unit
   class TestMyComponent:
       ...
   ```

2. **Include detailed docstrings**
   ```python
   def test_my_function(self):
       """
       Test that my_function behaves correctly.
       
       This test verifies:
       1. Function returns expected results with valid input
       2. Function handles edge cases appropriately
       
       Edge cases covered:
       - Empty input
       - Maximum size input
       - Invalid input types
       """
   ```

3. **Use proper fixtures**
   - Use existing fixtures when possible
   - Create new fixtures only when necessary
   - Document fixture dependencies

4. **Follow naming conventions**
   - Test classes: `TestComponentName`
   - Test functions: `test_method_name_scenario`
   - Fixture names: `mock_component_name` or `fixture_purpose`

5. **Test in isolation**
   - Mock external dependencies
   - Avoid reliance on global state
   - Reset state between tests

## Test File Structure

Each test file should follow this structure:

```python
"""
Unit tests for the [Component] module.

Tests the functionality of the [Component] class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Fixtures (if not using shared fixtures from conftest.py)
@pytest.fixture
def test_specific_fixture():
    """Fixture description."""
    ...

# Test class
@pytest.mark.unit  # or appropriate marker
class TestComponentName:
    """Test cases for the Component."""
    
    def test_initialization(self, fixture1, fixture2):
        """Test that the component initializes correctly."""
        ...
    
    def test_main_functionality(self, fixture1):
        """Test the main functionality of the component."""
        ...
    
    # More test methods...
```

## Troubleshooting Tests

Common issues:

1. **Async test failures**: Ensure you're using `@pytest.mark.asyncio` for async tests and the function is defined with `async def`.

2. **Import errors**: Check that your import paths match the project structure. Use project root imports (e.g., `from services.module import Component`).

3. **Fixture errors**: Verify that fixture dependencies are available and correctly ordered.

4. **Mocking issues**: 
   - Use `AsyncMock` for async methods
   - Use `side_effect` for complex return behavior
   - Patch at the correct path/module level 