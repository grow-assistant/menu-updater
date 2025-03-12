# AI Agent Development Plan - CRITICAL GUIDELINES

## 0. PRIMARY SUCCESS CRITERIA - TEST EFFECTIVENESS
- **Current Goal**: Achieve a passing rate of at least 6 out of 7 test scenarios
- **Definition of Success**: Tests demonstrating proper AI agent functionality with all required criteria met
- **Current Status**: 0/7 tests passing - UNACCEPTABLE
- **Root Cause Analysis**: Investigation indicates the use of mock implementations (FixedSQLExecutor) despite express prohibition
- **Corrective Action Required**: Replace ALL mock implementations with REAL production services immediately
- **Non-negotiable Requirement**: NO mock services allowed under ANY circumstances
- **Verification Process**:
  1. Run full test suite after implementation of real services
  2. Verify responses contain required success condition phrases
  3. Document detailed results of each test scenario
- **MANDATORY SQL VALIDATION**: Every SQL statement result MUST match the corresponding response
  - All SQL query executions must be logged with full details
  - SQL results must be stored for validation and auditing
  - Response content must be traceable to specific SQL query results
  - Discrepancies between SQL results and responses are CRITICAL failures

## 0.A. IMPLEMENTATION COMPLIANCE TRACKING

| Service Component | Current Status | Required Status | Compliance |
|-------------------|----------------|-----------------|------------|
| SQLExecutor       | FixedSQLExecutor (MOCK) | Real SQLExecutor | ❌ NON-COMPLIANT |
| RulesService      | Real Implementation | Real Implementation | ✅ COMPLIANT |
| DatabaseValidator | Real Implementation | Real Implementation | ✅ COMPLIANT |
| CritiqueAgent     | Real Implementation | Real Implementation | ✅ COMPLIANT |
| ResponseGenerator | Real Implementation | Real Implementation | ✅ COMPLIANT |

| Test Scenario       | Current Status | Success Condition Present | Database Validation |
|---------------------|----------------|---------------------------|---------------------|
| ambiguous_request   | Failing        | ❌ Missing                | ❌ Failing          |
| basic_menu_inquiry  | Failing        | ❌ Missing "our menu includes" | ❌ Failing    |
| menu_item_details   | Failing        | ❌ Missing                | ❌ Failing          |
| price_inquiry       | Failing        | ❌ Missing                | ❌ Failing          |
| progressive_order   | Failing        | ❌ Missing                | ❌ Failing          |
| recent_order_inquiry| Failing        | ❌ Missing "your last order" | ❌ Failing       |
| typo_handling       | Failing        | ❌ Missing                | ❌ Failing          |

- **Implementation Verification**:
  - Code review must verify REAL service implementations
  - Runtime verification of service class types must be implemented
  - Configuration audit must confirm production settings
  - Automatic detection and reporting of mock services required

- **Progress Tracking**:
  - Daily updates to compliance tracking table required
  - Test success rate must be documented after each change
  - All implementation deviations must be documented with justification

## 0.B. MANDATORY PYTEST VERIFICATION - ZERO TOLERANCE FOR TEST FAILURES

- **CRITICAL REQUIREMENT**: ALL pytest tests MUST pass after EVERY major update
- **No Exceptions**: Production code is NEVER allowed to be deployed with failing tests
- **Verification Process**:
  1. Run complete pytest test suite after every code change
  2. Document test results with timestamp, version, and pass rate
  3. Blocking issues must be fixed immediately before proceeding with any other work
- **Test Automation Requirements**:
  - CI/CD pipeline must run pytest automatically on every commit
  - Failed builds must trigger immediate notifications to development team
  - Version control systems must prevent merging code with failing tests
  - Build artifacts must include complete test results
- **Test Coverage Enforcement**:
  - Pytest coverage reports must be generated with each test run
  - Minimum 85% test coverage for all production code
  - Critical paths require 100% test coverage
  - New features require tests before acceptance
- **Test Environment Requirements**:
  - All tests must run against production-like environments
  - Test databases must mirror production schema
  - Environment variables must be properly configured for tests
  - Mock services are strictly prohibited in tests
- **Test-Driven Development Mandate**:
  - All features must have tests written before implementation
  - Regression tests must be added for all bug fixes
  - Test refactoring must happen alongside code refactoring
  - Test documentation must be maintained with the same rigor as code documentation

### Enforcement Mechanisms:

```python
# REQUIRED IMPLEMENTATION: Pre-commit hook example
# Save as: .git/hooks/pre-commit

#!/bin/bash
echo "Running pytest to ensure all tests pass before commit..."
python -m pytest
RESULT=$?

if [ $RESULT -ne 0 ]; then
  echo "❌ COMMIT REJECTED: Tests failed. Fix failing tests before committing."
  echo "This is a CRITICAL requirement per AI_AGENT_DEVELOPMENT_PLAN.md"
  exit 1
else
  echo "✅ All tests passed. Proceeding with commit."
fi
```

```python
# REQUIRED IMPLEMENTATION: Continuous Integration configuration
# GitHub Actions Workflow (.github/workflows/pytest.yml)

name: Mandatory Pytest Verification

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    - name: Test with pytest
      run: |
        pytest --cov=./ --cov-report=xml
    - name: Verify test coverage
      run: |
        coverage_percentage=$(python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); root = tree.getroot(); print(float(root.attrib['line-rate']) * 100)")
        if (( $(echo "$coverage_percentage < 85" | bc -l) )); then
          echo "❌ FAILURE: Test coverage is ${coverage_percentage}%, which is below the required 85%"
          exit 1
        else
          echo "✅ Test coverage is ${coverage_percentage}%, which meets the requirement"
        fi
```

## 0.C. MANDATORY SQL VALIDATION & RESULT STORAGE

- **CRITICAL REQUIREMENT**: 100% validation of SQL results against responses
- **No Exceptions**: Every response must be fully backed by SQL query results
- **SQL-Response Mapping Requirements**:
  1. Each response must directly reference data retrieved via SQL
  2. All facts presented in responses must be traceable to SQL results
  3. No response may contain information not backed by database data
  4. Any calculation or aggregation must match SQL-derived values exactly

- **SQL Result Storage Requirements**:
  - **Persistent Storage**: All SQL query results must be stored in dedicated tables
    ```sql
    CREATE TABLE sql_query_log (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        session_id VARCHAR(64) NOT NULL,
        query_text TEXT NOT NULL,
        execution_time_ms INTEGER NOT NULL,
        result_count INTEGER NOT NULL,
        success BOOLEAN NOT NULL,
        error_message TEXT
    );
    
    CREATE TABLE sql_query_results (
        id SERIAL PRIMARY KEY,
        query_log_id INTEGER REFERENCES sql_query_log(id),
        result_data JSONB NOT NULL,
        response_text TEXT NOT NULL,
        validation_status BOOLEAN NOT NULL,
        validation_details TEXT
    );
    
    CREATE INDEX idx_query_log_session ON sql_query_log(session_id);
    CREATE INDEX idx_query_log_timestamp ON sql_query_log(timestamp);
    ```
  
  - **Result Retention Policy**:
    - Production: Minimum 90 days retention for all SQL results
    - Testing: Full retention of all test SQL results
    - Audit: Special flagging for SQL results used in compliance verification
  
  - **SQL Validation Procedure**:
    1. Execute SQL query and capture complete result set
    2. Generate response using retrieved data
    3. Store both SQL results and generated response
    4. Perform automated validation of response against SQL data
    5. Flag any discrepancies for immediate remediation
    6. Log validation status with detailed comparison results

- **Validation Logging Format**:
  ```json
  {
    "validation_id": "uuid-string",
    "timestamp": "ISO-timestamp",
    "sql_query": "SELECT statement text",
    "sql_results": [
      {"column1": "value1", "column2": "value2", ...},
      ...
    ],
    "response_text": "Generated response text",
    "validation_status": true/false,
    "validation_details": {
      "matched_data_points": 5,
      "missing_data_points": 0,
      "mismatched_data_points": 0,
      "data_point_matches": [
        {"response_fragment": "text", "sql_data": {"column": "value"}, "matched": true},
        ...
      ]
    }
  }
  ```

- **Validation Enforcement**:
  - Automatic validation runs after every response generation
  - Failed validations must block response delivery in production
  - Test scenarios must include validation criteria for SQL results
  - Remediation of SQL-response mismatches takes priority over all other tasks
  - Weekly validation audit reports required for all production systems

## 1. REAL SERVICES IMPLEMENTATION - ZERO TOLERANCE FOR MOCKS
- **Mandatory production implementations**: All services must be implemented as production-ready components
- **Strictly prohibited**: Mock services, stub services, or any temporary implementations 
- **CRITICAL VIOLATION**: Using FixedSQLExecutor instead of real SQLExecutor constitutes a severe infraction
- **Immediate remediation required**: Replace ALL instances of mock implementations with real services
- **Service instance requirements**:
  - RulesService: Fully functional with complete rule validation capabilities
  - SQLExecutor: Production-grade with transaction support and connection pooling (NOT FixedSQLExecutor)
  - DatabaseValidator: Complete schema validation and data integrity checks
  - CritiqueAgent: Full analytical capabilities with advanced feedback mechanisms
  - All supporting services: Production implementations with comprehensive error handling
- **Service Communication**: Implement robust inter-service communication with retry logic
- **Dependency Injection**: Use proper DI patterns for service composition
- **No Exceptions Policy**: Any deviations MUST be approved through formal change management process 
  - Such approvals should be considered EXTRAORDINARY
  - Full documentation of reason, scope, and timeline for resolution required
  - Temporary exceptions must include concrete plan to replace with real implementations

## 1.A. TEST FAILURE REMEDIATION PLAN
- **Current Failing Tests**:
  1. ambiguous_request
  2. basic_menu_inquiry
  3. menu_item_details
  4. price_inquiry
  5. progressive_order
  6. recent_order_inquiry
  7. typo_handling

- **Required Implementation Changes**:
  1. Replace ALL instances of FixedSQLExecutor with real SQLExecutor
  2. Implement proper database connection handling with production credentials
  3. Ensure response templates contain required phrases for success conditions:
     - basic_menu_inquiry: Include "our menu includes" in responses
     - menu_item_details: Provide complete details with required response format
     - price_inquiry: Include price information in specified format
     - recent_order_inquiry: Reference "your last order" in responses
  4. Implement MANDATORY SQL validation system to verify responses:
     - Ensure SQL query results are properly stored in dedicated tables
     - Validate that every response element matches SQL data
     - Add validation logging to verify SQL-response consistency
     - Create traceability from each response element to source SQL data

- **Response Format Compliance**:
  - Responses MUST include the exact phrases specified in success_conditions
  - Each scenario has specific required phrases that must be present in responses
  - All responses must adhere to the business requirements in each test
  - Typo handling must demonstrate proper error correction capabilities
  - **SQL Verification**: Each test must pass SQL validation checks:
    - Menu items mentioned must exist in database with exact names and prices
    - Customer order history must match database records exactly
    - Any numerical values must match database values precisely 
    - Dates and times must be accurate reflections of database timestamps

- **Systematic Testing Approach**:
  1. Fix service implementations first (replace all mocks)
  2. Verify database connections with actual production data
  3. Update response templates to include required success phrases
  4. Implement SQL validation capture and storage
  5. Run tests individually with detailed logging
  6. Verify SQL-response validation for each test
  7. Address remaining issues one by one until 6/7 tests pass
  
- **Test Success Requirements**:
  - Each test must meet ALL success conditions defined in scenario
  - Minimal response time requirements must be met
  - No fallback responses unless explicitly allowed
  - All database validations must pass
  - Complete SQL validation logs must be available for inspection
  - SQL-response validation must show 100% match for critical data points

## 2. Database Implementation & Management
- **Production database requirements**:
  ```
  DB_HOST=<production_host>
  DB_PORT=<production_port>
  DB_NAME=<production_db>
  DB_USER=<production_user>
  DB_PASSWORD=<production_password>
  DB_CONNECTION_TIMEOUT=<timeout_in_seconds>
  DB_MAX_CONNECTIONS=<max_connection_pool_size>
  DB_SSL_MODE=<ssl_mode>
  ```
- **Connection validation checklist**:
  1. Verify database accessibility before initializing any services
  2. Validate database schema version compatibility
  3. Check user permissions against required operations
  4. Test read/write capabilities before full operation
- **Connection management**:
  - Implement connection pooling with optimal sizing
  - Monitor connection status with heartbeat checks
  - Handle connection timeouts and reconnection logic
  - Log all connection-related events with proper context

### 2.A. SQL STATEMENT TRACKING AND VALIDATION

- **SQL Execution Logging**:
  - Every SQL statement must be logged with exact execution parameters
  - Execution timestamps must be recorded with millisecond precision
  - Execution context (user, session, operation) must be captured
  - Result sets must be stored in full for validation

- **Validation Table Schema**:
  ```sql
  -- Additional validation tracking tables
  CREATE TABLE sql_validation_metrics (
      validation_id VARCHAR(64) PRIMARY KEY,
      query_log_id INTEGER REFERENCES sql_query_log(id),
      response_id VARCHAR(64) NOT NULL,
      match_percentage DECIMAL(5,2) NOT NULL,
      validation_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      validation_pass BOOLEAN NOT NULL,
      critical_fields_match BOOLEAN NOT NULL,
      validator_version VARCHAR(32) NOT NULL
  );
  
  CREATE TABLE sql_validation_issues (
      id SERIAL PRIMARY KEY,
      validation_id VARCHAR(64) REFERENCES sql_validation_metrics(validation_id),
      issue_type VARCHAR(32) NOT NULL,
      expected_value TEXT NOT NULL,
      actual_value TEXT NOT NULL,
      field_name VARCHAR(128) NOT NULL,
      severity VARCHAR(16) NOT NULL,
      remediation_status VARCHAR(32) DEFAULT 'OPEN',
      resolved_timestamp TIMESTAMP
  );
  ```

- **SQL Result Reconciliation Process**:
  1. Capture complete SQL query results before response generation
  2. Extract all factual elements from generated response
  3. Map each response fact to source SQL data
  4. Compute match percentage for factual accuracy
  5. Identify and log any discrepancies
  6. Trigger alerts for critical mismatches
  7. Store validation results for audit and improvement

- **Database Validator Service Requirements**:
  - Implement DatabaseValidator as a real production service
  - Validator must have full access to SQL result history
  - Implement natural language parsing for response fact extraction
  - Support validation of numerical values, dates, names, and relationships
  - Maintain validation metrics for quality trending

- **SQL Validation Reports**:
  - Daily validation summary reports required
  - Detail views must show validation issues by severity
  - Trend analysis for validation pass rates
  - Integration with monitoring dashboards
  - Escalation procedures for critical validation failures

## 3. Service Configuration & Resource Management
- **Production configuration paths**:
  ```
  rules_path: /c:/Python/GIT/swoop-ai/services/rules
  resources_dir: /c:/Python/GIT/swoop-ai/resources
  sql_files_path: /c:/Python/GIT/swoop-ai/services/sql_generator/sql_files
  models_path: /c:/Python/GIT/swoop-ai/services/models
  cache_dir: /c:/Python/GIT/swoop-ai/cache
  logs_dir: /c:/Python/GIT/swoop-ai/logs
  ```