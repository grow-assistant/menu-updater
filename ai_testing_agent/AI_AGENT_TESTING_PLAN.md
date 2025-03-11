# AI Testing Agent Testing Plan

## 1. Test Execution
- **Initial Testing**: 
  - Run basic configuration tests with the main testing script:
    ```
    python run_modified_tests.py
    ```
  - Access test scenarios from the `test_scenarios/` directory, which contains:
    - basic_menu_inquiry.json
    - menu_item_details.json
    - price_inquiry.json
    - recent_order_inquiry.json
    - ambiguous_request.json
    - typo_handling.json
    - progressive_order.json
  - Test with different personas, error handling, and concurrency settings
- **Extended Testing**:
  - Run end-to-end scenarios, category-specific tests, and stress tests
  - Use `run_modified_tests.py` with additional test scenarios as needed
  - Consider implementing additional test scenarios for edge cases

## 2. Test Results Review
- **Automated Analysis**:
  - Generate summary reports using the analysis script:
    ```
    python analyze_test_results.py
    ```
  - Logs are stored in `logs/` directory
  - Test outputs are stored in `text_files/test_output_{timestamp}.txt`
  - Categorize results (passed, failed, anomalous)
  - Process critique agent feedback from CritiqueAgent
- **Database Validation**:
  - Verify factual accuracy of responses against database records using DatabaseValidator
  - Configuration settings in `config/config.yaml` control database connections
  - Review SQL validation logs 
  - Analyze discrepancy reports and validation failures
  - Check numerical accuracy in responses (prices, quantities, dates)
- **Review**:
  - Review JSON results, focusing on failures
  - Analyze test output for patterns and trends
  - Verify factual accuracy, conversation flow, and error handling
  - Document findings in standardized format

## 3. System Updates
- Categorize issues by severity (critical, high, medium, low)
- Prioritize fixes based on impact, UX, complexity, and frequency
- Create issue tickets and implement fixes in priority order
- Improve test agent (AIUserSimulator), enhance scenarios, and optimize testing tools
- **Current Priority Tasks**:
  - Reference the prioritized items in TODO_LIST.md for the most up-to-date task list
  - Address Critical priority items first:
    - Fix 'immutabledict is not a sequence' SQL execution errors
    - Enhance error handling in SQL executor
  - Follow with High priority items:
    - Optimize response generation pipeline
    - Implement caching for common responses
    - Improve fact checking mechanism
    - Enhance database results validation
  - Then address Medium and Low priority items as resources allow

## 4. Retesting Procedure
- **Verification Testing**: Retest specific fixes and verify no new issues
  - Run targeted scenario tests:
    ```
    python run_modified_tests.py --scenarios [scenario_name]
    ```
- **Regression Testing**: Execute complete test suite after significant changes
- **Continuous Testing**: Schedule regular tests and integrate with CI/CD

## 5. Documentation and Reporting
- Maintain test scenario documentation in the test_scenarios/ directory
- Keep historical records of test results and logs
- Reference existing documentation in files like:
  - AI_TESTING_AGENT_IMPLEMENTATION_PLAN.md
  - implementation_plan.md
  - test_instructions.md

## 6. Special Considerations
- Maintain test environment with regular updates
- Clean up test artifacts periodically
- Ensure environment variables in .env file are properly set:
  - OPENAI_API_KEY
  - DB_CONNECTION_STRING and other DB parameters
  - Other API keys as needed

## 7. Test Review Checklist
- Review failed scenarios, conversation flows, and performance metrics
- Evaluate critique feedback and check data validation
- Analyze error patterns and compare against previous runs
- Check edge cases, security concerns, and overall UX
- **Database Validation Review**:
  - Confirm that all fact-based responses match actual database records
  - Analyze validation templates for different response categories
  - Review factual discrepancies by severity and frequency
  - Verify schema awareness in validation queries is up-to-date
  - Check numerical accuracy validation for prices, quantities, and dates
  - Ensure proper reporting of validation failures with clear explanations

## 8. Continuous Improvement Cycle
- After each test run and review, maintain a todo list log in TODO_LIST.md
- Reference and work through items in AI_TODO_LIST.md:
  - Check off completed items with [x] syntax
  - Prioritize Visualization Tools first, then work through the Additional Enhancements backlog
  - Document progress and completion dates for accountability
  - Add new items to the list as they are identified during testing
- Address items on the todo list, prioritizing by severity and impact:
  - Critical: Items that prevent core functionality or cause system failures
  - High: Items that significantly impact response quality or performance
  - Medium: Items that enhance system reliability and robustness
  - Low: Items that optimize or extend system capabilities
- Run pytest to verify fixes and improvements
- Document resolution and outcomes
- Update TODO_LIST.md after each improvement cycle:
  - Mark completed items with [x]
  - Add new items discovered during testing
  - Re-prioritize existing items based on latest findings
- Repeat the cycle for continuous improvement

## 9. AI Agent Performance Review
- **Testing Agent Evaluation**:
  - Review AIUserSimulator performance in generating realistic user interactions
  - Assess accuracy of issue detection and reporting
  - Evaluate efficiency of test execution strategy
  - Analyze adaptability to different testing scenarios
  - Identify opportunities for improved edge case handling

- **Critique Agent Analysis**:
  - Evaluate quality and actionability of feedback from CritiqueAgent
  - Assess consistency of critique standards
  - Review false positive/negative rates in issue identification
  - Analyze depth of conversational understanding
  - Identify opportunities for more nuanced feedback

- Document improvement suggestions for both agents after each major test cycle
- Implement incremental enhancements to agent prompts, rules, and evaluation criteria
- Maintain version history of agent configurations to correlate with test results