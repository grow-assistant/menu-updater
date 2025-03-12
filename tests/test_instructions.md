# Time Period Extraction Testing Instructions

## Overview

This document provides instructions for testing the time period extraction feature that identifies date/time constraints in user queries and extracts them as SQL WHERE clauses.

## What We're Testing

The system should:
1. Detect time period constraints in user queries
2. Convert them to appropriate SQL WHERE clauses
3. Cache them for follow-up questions
4. Identify follow-up questions that refer to previously mentioned time periods

## Test Cases

### Test Case 1: Specific Date Extraction

**Query:**
```
How many orders were completed on 2/21/2025?
```

**Expected Behavior:**
- The system should classify this as an "order_history" query
- It should extract "2/21/2025" and convert it to SQL format: "2025-02-21"
- The resulting time period clause should be: `WHERE updated_at = '2025-02-21'`
- This clause should be cached for follow-up questions

**How to Verify:**
- Examine the logs output, which should show the time period identified
- Look for log entries like: `Time period identified: WHERE updated_at = '2025-02-21'`

### Test Case 2: Follow-up Question

**Query (after Case 1):**
```
What were the most popular items during that time?
```

**Expected Behavior:**
- The system should recognize this as a follow-up question
- It should maintain the previously cached time period (`WHERE updated_at = '2025-02-21'`)
- The logs should indicate that it's using the cached time period

**How to Verify:**
- Examine the logs for a message like: `Using cached time period for follow-up question: WHERE updated_at = '2025-02-21'`

### Test Case 3: Relative Time Period

**Query:**
```
Show me sales from the past week
```

**Expected Behavior:**
- The system should detect the relative time period "past week"
- It should convert this to a SQL clause: `WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)`
- This new time period should replace the previously cached one

**How to Verify:**
- Check the logs for: `Time period identified: WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)`

### Test Case 4: Month-Based Query

**Query:**
```
Show me the total sales for January 2024
```

**Expected Behavior:**
- The system should extract both the month and year
- It should create a clause like: `WHERE YEAR(updated_at) = 2024 AND MONTH(updated_at) = 1`
- This time period should be cached

## How to Run Tests

1. Start the application with verbose logging enabled
2. Open the debug console or log viewer
3. Enter the test queries one by one
4. After each query, check the logs for the expected time period extraction
5. Verify that follow-up questions correctly maintain the time context

## Examining Logs

Look for these key log patterns:
```
Classifying query: 'How many orders were completed on 2/21/2025?'
Query classified as: order_history
Time period identified: WHERE updated_at = '2025-02-21'
```

For follow-up questions:
```
Query classified as: popular_items
Using cached time period for follow-up question: WHERE updated_at = '2025-02-21'
```

## Additional Test Variations

Try testing with different date formats and time references:
- "Orders from December 25th, 2024"
- "Sales data between March and June last year"
- "Customer orders from Q1 2024"
- "Weekend orders in the past month"

## Troubleshooting

If the time period isn't being correctly extracted:
1. Check that the OpenAI API key is valid
2. Verify that the prompt format in the classification service is correct
3. Try using more explicit date formats in your queries
4. Look for any errors in the classification service logs 