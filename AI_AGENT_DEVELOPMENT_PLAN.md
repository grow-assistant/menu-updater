# AI Agent Development Plan – Critical Guidelines

## 1. Purpose

This document defines the development, testing, and production standards required to build a reliable, production-ready AI agent. Our focus includes rigorous SQL validation, real-service integration, automated testing, and auditability to ensure responses are accurate, timely, and fully traceable to production data.

## 2. Development Principles

1. **Zero Tolerance for Mock Services**  
   - All services (e.g., SQLExecutor, RulesService) must be implemented using real, production-ready code.  
   - Use of mocks, stubs, or temporary implementations is strictly prohibited; any exceptions must be formally approved with a documented remediation plan.

2. **Mandatory Test Success**  
   - Every major update must achieve a minimum passing rate of 90% across all test scenarios.  
   - Automated tests (e.g., via pytest) integrated into CI/CD pipelines will block commits and deployments if any tests fail.

3. **100% SQL Validation**  
   - Every response must be fully supported by and directly traceable to SQL query results.  
   - Any discrepancy between the SQL result and response content constitutes a critical failure that must be immediately remediated.

4. **SQL Result Storage and Auditing**  
   - Store all SQL query results in secure logs with a minimum retention period of 90 days in production.  
   - Logs must capture the SQL text, execution time, result sets, and validation status for audit purposes.

5. **Real Database Integration**  
   - Use production credentials, connection pooling, and schema mirroring for both testing and live operations.  
   - Validate database connections at startup. No simulated or mock database implementations are allowed.

6. **Response Format Compliance**  
   - All responses must adhere to the required format and include mandated phrases (e.g., “our current menu includes”).  
   - Data such as prices and items must match the corresponding database values exactly.

7. **Validation Enforcement**  
   - Implement automated post-generation validation that compares response content with SQL query results.  
   - In production, any response that fails validation must be blocked from delivery, and a weekly audit report should summarize pass rates and issues for remediation.

8. **Implementation Verification**  
   - Verify that all services, database connections, and configurations are production-ready via code reviews, runtime checks, and startup validations.  
   - Document any deviations along with their remediation plans in a compliance tracking log.

## 3. Test Scenarios and Acceptance Criteria

Each test scenario below specifies the user inputs, required SQL operations, success conditions, SQL validation rules, and performance targets.

1. **Ambiguous Request**  
   - **Input:** “How are we doing?”  
   - **Required SQL:** Query sales summaries, inventory status, and staff performance metrics.  
   - **Success Criteria:** The response must recognize the ambiguity and ask for clarification on the specific business area.  
   - **SQL Validation:** Ensure clarification options directly correspond to existing data categories.  
   - **Response Time:** < 500 ms.

2. **Menu Status Inquiry**  
   - **Input:** “What's our current active menu?”  
   - **Required SQL:** Retrieve active menu items with their status and availability.  
   - **Success Criteria:** The response must include the phrase “our current menu includes” and display menu items that exactly match the database.  
   - **Response Time:** < 800 ms.

3. **Category Performance Analysis**  
   - **Input:** “How are our appetizers performing?”  
   - **Required SQL:** Query sales data and profit margins filtered by the selected category.  
   - **Success Criteria:** Include clear performance metrics and trends for the specified category.  
   - **Response Time:** < 600 ms.

4. **Comparative Analysis**  
   - **Input:** “Compare dinner sales this week versus last week” followed by “Break it down by category”.  
   - **Required SQL:** Query sales data for the two periods, then group results by category.  
   - **Success Criteria:** The response must confirm the compared time periods and show accurate percentage changes.  
   - **Response Time:** Combined < 1000 ms.

5. **Historical Performance**  
   - **Input:** “What were our busiest days last month?”  
   - **Required SQL:** Query daily sales history for the specified period.  
   - **Success Criteria:** The response must include the phrase “your busiest days were” and present correct dates and sales figures.  
   - **Response Time:** < 700 ms.

## 4. Compliance Tracking

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

## 5. Follow-Up Agent

The Follow-Up Agent is responsible for extending the conversation flow by analyzing completed primary responses and generating contextually relevant follow-up questions.

- **Responsibilities:**
  - Analyze Swoop's completed responses for additional inquiry opportunities.
  - Generate context-aware follow-up questions to enhance user engagement.
  - Maintain conversation history to avoid redundancy and ensure relevance.
  - Seamlessly integrate follow-up queries without interrupting the primary response flow.

- **Example Workflow:**
  1. **User Input:** "What were our sales last week?"
  2. **Primary Response:** "Your total sales last week were $24,580, which is 5% higher than the previous week."
  3. **Follow-Up Agent Analysis:** Identifies opportunity for additional details on sales breakdown.
  4. **Follow-Up Question:** "Would you like to see how these sales break down by menu category?"

## 6. Critique Agent

The Critique Agent serves as an independent quality controller that analyzes each response before delivery to ensure compliance with SQL and business rules.

- **Responsibilities:**
  - Compare response content with SQL query results to validate factual accuracy.
  - Verify that the response thoroughly addresses all aspects of the user's query.
  - Enforce the inclusion of required phrases and data integrity.
  - Provide detailed feedback on any discrepancies and block responses that do not meet quality standards.

- **Example Workflow:**
  1. **Primary Response:** "Your appetizer sales increased by 12% this month."
  2. **Validation Check:** Compare the percentage with the actual SQL result (e.g., 12.3% rounded to 12%).
  3. **Decision:** Approve the response if the values are within acceptable tolerance or block it and trigger remediation if not.

By clearly defining these guidelines and enforcing strict validation at each stage, we can ensure that the AI agent is both reliable in production and compliant with business-critical requirements.

