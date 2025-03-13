# Test Runner

A comprehensive test runner for validating and diagnosing service functionality.

## Overview

This test runner is designed to execute test scenarios against a set of services, validate the results, and generate detailed reports. It provides a modular, extensible framework for testing service functionality, diagnosing issues, and ensuring compliance with requirements.

## Features

- **Scenario-based Testing**: Run individual test scenarios or all available scenarios at once.
- **Service Diagnostics**: Detailed diagnostics for each service to identify issues.
- **Compliance Reporting**: Generate compliance reports with pass/fail status.
- **HTML Reports**: Generate user-friendly HTML reports for easy viewing.
- **Root Cause Analysis**: Identify root causes of failures and suggest improvements.
- **Schema Validation**: Validate SQL queries against database schema.
- **Response Validation**: Validate responses against expected content.

## Directory Structure

```
test_runner/
├── utils/               # Utility functions
│   ├── logging_setup.py    # Logging setup utilities
│   ├── config_loader.py    # Configuration loading utilities
│   └── schema_extractor.py # Schema extraction utilities
├── services/            # Service-related code
│   ├── service_setup.py       # Service setup utilities
│   └── service_diagnostics.py # Service diagnostics utilities
├── tests/               # Test-related code
│   ├── test_context.py    # Test context building utilities
│   ├── test_executor.py   # Test execution utilities
│   └── test_validator.py  # Test validation utilities
├── reporting/           # Reporting-related code
│   ├── report_generator.py    # Report generation utilities
│   ├── compliance_report.py   # Compliance report generation utilities
│   └── diagnostics_report.py  # Diagnostics report generation utilities
├── test_runner.py       # Main test runner module
└── README.md            # This README file
```

## Usage

### Command-Line Arguments

```
usage: test_runner.py [-h] (--all | --scenario SCENARIO) [--config CONFIG]
                       [--schema SCHEMA] [--log-dir LOG_DIR]
                       [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                       [--report] [--output OUTPUT] [--threshold THRESHOLD]
                       [--enforce-threshold]

Test runner for services and agents.

options:
  -h, --help            show this help message and exit
  --all                 Run all test scenarios
  --scenario SCENARIO   Run a specific test scenario by name
  --config CONFIG       Path to configuration file
  --schema SCHEMA       Path to schema file
  --log-dir LOG_DIR     Directory for log files
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level
  --report              Generate test reports
  --output OUTPUT       Output path for test report
  --threshold THRESHOLD
                        Minimum passing percentage threshold (0.0-1.0)
  --enforce-threshold   Enforce passing threshold (exit with error if not met)
```

### Examples

Run a specific test scenario:

```bash
python -m test_runner.test_runner --scenario menu_status_inquiry
```

Run all test scenarios and generate reports:

```bash
python -m test_runner.test_runner --all --report
```

Run all test scenarios with a custom threshold and enforce it:

```bash
python -m test_runner.test_runner --all --threshold 0.95 --enforce-threshold
```

## Test Scenarios

Test scenarios are defined in JSON files located in the `test_scenarios` directory. Each scenario file should have a `.json` extension and contain the following fields:

```json
{
  "query": "What items are on the menu today?",
  "intent": "menu_inquiry",
  "entities": ["menu", "today"],
  "expected_tables": ["menu_items", "daily_specials"],
  "expected_sql_pattern": ["SELECT.*FROM.*menu_items", "SELECT.*FROM.*daily_specials"],
  "expected_response_contains": ["menu", "items", "today"],
  "expected_response_type": "information",
  "is_ambiguous": false
}
```

## Report Types

### Test Report

The test report contains detailed information about each test scenario, including:

- SQL executed
- SQL results
- Response generated
- Follow-up questions
- Critique
- SQL validation
- Response validation
- Errors and issues

### Compliance Report

The compliance report summarizes the compliance status of the test results, including:

- Overall passing percentage
- Compliance status (pass/fail)
- Service diagnostics
- Failed tests
- Recommendations

### Diagnostics Report

The diagnostics report provides detailed diagnostics information, including:

- Service health assessment
- Error patterns
- Root cause analysis
- Priority recommendations

## Customization

The test runner is designed to be modular and extensible. You can customize it by:

1. Adding new test scenarios in the `test_scenarios` directory
2. Extending the service diagnostics in `services/service_diagnostics.py`
3. Adding new validation rules in `tests/test_validator.py`
4. Customizing the report generation in `reporting/`

## Requirements

- Python 3.7 or higher
- Required dependencies (see requirements.txt)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/test-runner.git

# Install dependencies
pip install -r requirements.txt
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 