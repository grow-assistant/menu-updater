# Time Period Extraction Implementation Summary

## Overview
This implementation enhances the AI Menu Updater system to identify time period constraints in user queries, extract them as SQL WHERE clauses, and cache them for follow-up questions - all determined by OpenAI.

## Changes Made

### 1. Classification Service (`services/classification/classifier.py`)
- Updated the `classify()` method to return the time period clause as part of the classification result
- Modified the `parse_classification_response()` method to extract time period clauses from the model's JSON response
- Added support for JSON-structured responses from OpenAI
- Added `time_period_clause` field to cached classification results
- Updated error handling to properly handle the time period clause

### 2. Classification Prompt Builder (`services/classification/prompt_builder.py`)
- Created an enhanced prompt that instructs the OpenAI model to:
  - Identify time period information in user queries
  - Convert the time period to a SQL WHERE clause
  - Return both the query classification and the time period clause in JSON format
- Added detailed examples of time period expressions and their SQL equivalents
- Updated the prompt format to request structured JSON responses

### 3. Orchestrator Service (`services/orchestrator/orchestrator.py`)
- Added a `time_period_context` attribute to store time period clauses
- Modified the `process_query()` method to extract and cache time period clauses
- Added logic to detect potential follow-up questions that might refer to the previous time period
- Added a `get_time_period_context()` method to retrieve the cached time period
- Removed the time period clause from the SQL generation context to avoid duplication

## How It Works

1. When a user submits a query like "Show me sales from last week", the ClassificationService sends it to OpenAI
2. OpenAI analyzes the query and returns both a classification and a time period WHERE clause:
   ```json
   {
     "query_type": "order_history",
     "time_period_clause": "WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
   }
   ```
3. The Orchestrator extracts and caches this time period clause
4. For follow-up questions like "Show me the top sellers in that period", the system detects it as a follow-up and can use the cached time period

## Benefits

- More accurate time-based queries without relying on the SQL Generator to interpret time periods
- Consistent handling of time references across related queries
- Improved conversation continuity by maintaining time context
- Time period constraints determined solely by OpenAI in a structured format 