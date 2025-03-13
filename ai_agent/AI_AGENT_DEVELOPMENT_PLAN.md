# AI Agent Development Plan – Critical Guidelines

## 1. Purpose

This document outlines the standards for developing, testing, and deploying a reliable, production-ready AI agent. The plan emphasizes rigorous SQL validation, real-service integration, automated testing, and auditability, with a central focus on a circular feedback mechanism powered by the Critique Agent. This ensures responses are accurate, timely, and traceable to production data, while continuously improving through actionable feedback.

## 2. Development Principles

The following principles underpin the development process, ensuring a robust and dependable AI agent:

### Zero Tolerance for Mock Services
- All services (e.g., SQLExecutor, RulesService) must use real, production-ready code.
- Mocks, stubs, or temporary implementations are prohibited unless formally approved with a remediation plan.

### Mandatory Test Success
- Major updates must pass at least 90% of test scenarios.
- Automated tests (e.g., via pytest) in the CI/CD pipeline block commits and deployments if any test fails.

### 100% SQL Validation
- Every response must be fully supported by and traceable to SQL query results.
- Discrepancies between SQL results and response content are critical failures requiring immediate remediation.

### SQL Result Storage and Auditing
- Secure logs must retain SQL query results for at least 90 days in production.
- Logs include SQL text, execution time, result sets, and validation status for auditability.

### Real Database Integration
- Use production credentials, connection pooling, and schema mirroring for testing and live operations.
- Validate database connections at startup; no mock databases are permitted.

### Response Format Compliance
- Responses must follow a strict format, including phrases like "our current menu includes."
- Data (e.g., prices, items) must exactly match database values.

### Validation Enforcement
- Automated post-generation validation compares responses to SQL results.
- In production, failed responses are blocked, with weekly audit reports summarizing pass rates and issues.

### Implementation Verification
- Production-readiness is verified via code reviews, runtime checks, and startup validations.
- Deviations are documented in a compliance tracking log with remediation plans.

## 3. Circular Feedback Mechanism – The Core of Continuous Improvement

The Critique Agent drives a circular feedback loop, ensuring response quality and feeding insights back into development. Here's how it works:

### Response Generation
The AI agent generates a response using real services and SQL query results based on user input.

### Critique Agent Validation
Before delivery, the Critique Agent:
- Compares response content to SQL results for factual accuracy.
- Verifies all query aspects are addressed.
- Ensures required phrases and data integrity are maintained.
If the response passes, it's delivered; if it fails, it's blocked.

### Feedback Generation
- For failed responses, the Critique Agent provides detailed feedback (e.g., "Sales figure of $500 mismatches SQL result of $510").
- This feedback is logged and transformed into todo list items (e.g., "Fix rounding error in sales calculation").

### Development Lifecycle Integration
- Todo items are prioritized in the development backlog.
- Developers address issues, update the system, and redeploy, closing the loop as the improved agent generates better responses.

### Example Workflow:
1. User Input: "How much did appetizers earn this week?"
2. Primary Response: "Appetizer earnings this week were $1,200."
3. Critique Agent Check: SQL result shows $1,250; response fails validation.
4. Feedback: "Response underreported earnings by $50; adjust calculation logic."
5. Todo Item: "Update earnings computation in response_service.py to match SQL."
6. Outcome: Code is fixed, retested, and redeployed, improving future responses.

This mechanism ensures the AI agent evolves through real-time quality control and systematic remediation.

## 4. FollowUp Agent – Driving Engagement

The FollowUp Agent enhances user interaction by generating contextually relevant follow-up questions, complementing the Critique Agent's quality focus:

### Responsibilities:
- Analyzes primary responses for additional inquiry opportunities.
- Generates follow-up questions to deepen user engagement.
- Maintains conversation history to avoid redundancy.

### Integration with Circular Feedback:
- The FollowUp Agent operates after the Critique Agent approves the primary response.
- Its questions are validated separately by the Critique Agent, ensuring accuracy and relevance.

### Example Workflow:
1. User Input: "What were our sales last week?"
2. Primary Response: "Your total sales last week were $24,580, up 5% from the prior week."
3. Critique Agent: Validates accuracy against SQL; approves response.
4. FollowUp Agent: "Would you like to see how these sales break down by menu category?"
5. Critique Agent: Validates follow-up question's relevance; approves delivery.

This ensures a seamless, engaging conversation while maintaining the feedback loop's integrity.

## 5. Test Scenarios and Acceptance Criteria

These scenarios validate the agent's functionality, with SQL validation and feedback loops enforced:

### Ambiguous Request
- Input: "How are we doing?"
- SQL: Query sales, inventory, and staff metrics.
- Success: Asks for clarification (e.g., "Do you mean sales or inventory?").
- Validation: Options match data categories.
- Time: < 500 ms.

### Menu Status Inquiry
- Input: "What's our current active menu?"
- SQL: Retrieve active menu items.
- Success: Includes "our current menu includes" with exact database matches.
- Time: < 800 ms.

### Category Performance Analysis
- Input: "How are our appetizers performing?"
- SQL: Query sales and profit margins by category.
- Success: Provides metrics and trends.
- Time: < 600 ms.

### Comparative Analysis
- Input: "Compare dinner sales this week versus last week," then "Break it down by category."
- SQL: Query sales for both periods, grouped by category.
- Success: Confirms periods, shows accurate percentage changes.
- Time: < 1000 ms combined.

### Historical Performance
- Input: "What were our busiest days last month?"
- SQL: Query daily sales history.
- Success: Includes "your busiest days were" with correct dates and figures.
- Time: < 700 ms.

Feedback Integration: The Critique Agent flags any scenario failures (e.g., missing data) and creates todo items for resolution.

## 6. Compliance Tracking

All components and scenarios are monitored for compliance:

### Service Component Status

| Service Component    | Current Status         | Required Status         | Compliance |
|----------------------|------------------------|-------------------------|------------|
| SQLExecutor          | Real SQLExecutor       | Real SQLExecutor        | ✓          |
| RulesService         | Real Implementation    | Real Implementation     | ✓          |
| DatabaseValidator    | Real Implementation    | Real Implementation     | ✓          |
| CritiqueAgent        | Real Implementation    | Real Implementation     | ✓          |
| ResponseGenerator    | Real Implementation    | Real Implementation     | ✓          |

### Test Scenario Verification

| Test Scenario            | Current Status | Success Criteria Met | SQL Validation |
|--------------------------|----------------|----------------------|----------------|
| Ambiguous Request        | Passing        | ✓                    | ✓              |
| Menu Status Inquiry      | Passing        | ✓                    | ✓              |
| Category Performance     | Passing        | ✓                    | ✓              |
| Comparative Analysis     | Passing        | ✓                    | ✓              |
| Historical Performance   | Passing        | ✓                    | ✓              |

## 7. Required Codebase Components

Leverage existing components for consistency:

### Services (/services):
- query_processor.py, response_service.py, context_manager.py, etc.
- Extend, don't replace, these components.

### Test Runner (/test_runner):
- test_runner.py, critique_agent.py, scenario_library.py, etc.
- Use for all testing and validation.

## 8. DO NOT IMPLEMENT

Performance monitoring, error reporting, and deployment strategies are out of scope for now.

## 9. Todo Items Management

A dedicated todo list is maintained in the `todo_items/critique_agent_todos.json` file to track critical issues with the Critique Agent and circular feedback mechanism. This document:

- Must be kept up-to-date with all identified issues during testing
- Serves as the primary source of development tasks for the feedback mechanism
- Should be reviewed in each sprint planning session
- Contains severity ratings that determine development priority

All critical issues in this todo list must be addressed before the system can be considered production-ready. Testing should continue even as these items are being fixed, with updates to the todo list as new issues are discovered.

**No deployment should proceed until all HIGH and CRITICAL severity items in this list are resolved.**

## Conclusion

This plan centers on the Critique Agent's circular feedback mechanism, which validates responses, identifies issues, and feeds actionable todo items back into development for continuous improvement. The FollowUp Agent drives engagement with relevant follow-up questions, validated separately to maintain quality. By adhering to these guidelines, using real services, and enforcing rigorous SQL validation, we ensure a production-ready AI agent that's accurate, reliable, and auditable.