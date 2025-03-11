# Follow-up Question Processing Issues in SWOOP AI

## Overview

The SWOOP AI system is currently failing to properly recognize and process follow-up questions. In the example scenario, when a user asks "who placed those orders?" after a previous question "How many orders were completed on 2/21/2025?", the system fails to maintain context and generates an incorrect SQL query.

## Observed Behavior

From the logs, we can observe the following issues:

1. The system classifies the follow-up question as "general" instead of "order_history"
2. The SQL generator attempts to access a non-existent "customers" table
3. The date filter from the previous query is not properly carried over
4. The reference to "those orders" is not resolved to the orders from the previous query

## Root Issues Identified

### 1. Classification System Failure

The query classifier is not considering the conversation history when classifying follow-up questions. It's treating "who placed those orders?" as a standalone query instead of analyzing it in the context of the previous question.

```
2025-03-11 06:36:24,014 - services.orchestrator.orchestrator - INFO - Query classified as: general
```

**Expected Behavior**: The system should recognize this as an "order_history" query based on the previous context.

### 2. Context Utilization Gap

While the context information is being stored correctly:

```
'session_history': [{'timestamp': datetime.datetime(2025, 3, 11, 6, 36, 18, 443231), 'query': 'How many orders were completed on 2/21/2025?', ...}]
```

This context is not being effectively utilized by the SQL generator when creating queries for follow-up questions.

**Expected Behavior**: The SQL generator should extract relevant filters (date, status, etc.) from the previous query's context and apply them to the new query.

### 3. Reference Resolution Failure

The Entity Resolution Service is not correctly identifying pronouns and references like "those orders" and connecting them to entities in previous queries.

**Expected Behavior**: When encountering "those orders," the system should resolve this to "orders completed on 2/21/2025" from the previous query.

### 4. SQL Schema Knowledge Issues

The SQL generator is attempting to use tables that don't exist in the database schema:

```
relation "customers" does not exist
LINE 3: FROM customers c
```

**Expected Behavior**: The SQL generator should have knowledge of the actual database schema and use the correct tables for queries.

## Integration Breakdown

Though individual components have been implemented according to the development plan, their integration is not functioning correctly:

1. The Context Manager is not effectively communicating with the Query Classifier
2. The Entity Resolution Service is not being properly triggered for pronouns
3. The SQL Generator is not receiving or using context from previous queries
4. Schema information is not being properly provided to the SQL Generator

## Recommended Fixes

### 1. Enhance Query Classification to Consider Context

```python
# Current approach (simplified)
def classify_query(query_text):
    return classifier.predict(query_text)

# Recommended approach
def classify_query(query_text, context):
    previous_queries = context.get('session_history', [])
    previous_categories = [q.get('category') for q in previous_queries]
    
    # Check for follow-up indicators
    follow_up_indicators = ['they', 'them', 'those', 'that', 'it', 'this']
    is_likely_followup = any(indicator in query_text.lower() for indicator in follow_up_indicators)
    
    # If likely a follow-up, bias toward previous category
    if is_likely_followup and previous_categories:
        # Use ensemble approach combining standalone classification with context
        standalone_classification = classifier.predict(query_text)
        
        if standalone_classification.confidence < 0.8 and previous_categories:
            # Lower confidence standalone prediction + previous context suggests follow-up
            return previous_categories[-1]  # Use the most recent category
            
    return classifier.predict(query_text)
```

### 2. Improve Context Utilization in SQL Generation

```python
# Current approach (simplified)
def generate_sql(query, category):
    # Generate SQL based only on current query
    return sql_generator.generate(query, category)

# Recommended approach
def generate_sql(query, category, context):
    previous_queries = context.get('session_history', [])
    
    # Extract previous filters, entities, and time periods
    previous_filters = {}
    previous_time_periods = {}
    
    for prev_query in previous_queries:
        if 'sql_query' in prev_query and prev_query['sql_query']:
            # Extract filters from previous SQL
            extracted_filters = extract_filters_from_sql(prev_query['sql_query'])
            previous_filters.update(extracted_filters)
            
            # Extract time periods from previous SQL
            time_periods = extract_time_periods_from_sql(prev_query['sql_query'])
            previous_time_periods.update(time_periods)
    
    # Generate SQL with context awareness
    return sql_generator.generate_with_context(
        query, 
        category, 
        previous_filters, 
        previous_time_periods
    )
```

### 3. Enhance Reference Resolution

```python
# Current approach (simplified)
def resolve_references(query):
    # Simple entity extraction
    return entity_extractor.extract(query)

# Recommended approach
def resolve_references(query, context):
    # Check for pronouns and references
    references = identify_references(query)
    
    if references:
        previous_entities = extract_entities_from_context(context)
        resolved_references = {}
        
        for reference in references:
            if reference.type == 'pronoun':
                # Resolve pronouns like "those orders"
                resolved = resolve_pronoun(reference, previous_entities)
                resolved_references[reference.text] = resolved
                
        # Replace references in query with resolved entities
        enhanced_query = replace_references(query, resolved_references)
        return enhanced_query
    
    return query
```

### 4. Improve SQL Schema Knowledge

```python
# Current approach (simplified)
def generate_sql_query(query, category):
    # Generate SQL without schema validation
    return sql_generator.generate(query, category)

# Recommended approach
def generate_sql_query(query, category):
    # Generate SQL
    sql = sql_generator.generate(query, category)
    
    # Validate SQL against schema
    validation_result = schema_validator.validate(sql)
    
    if not validation_result.is_valid:
        # Regenerate with schema information
        sql = sql_generator.generate_with_schema_hints(
            query, 
            category,
            validation_result.schema_hints
        )
    
    return sql
```

## Implementation Priority

1. Reference Resolution Enhancement (Highest Priority)
2. Query Classification with Context Consideration
3. SQL Context Utilization
4. SQL Schema Knowledge Improvement

## Testing Strategy

For each fix:

1. Create test cases with follow-up questions
2. Verify that references are correctly resolved
3. Ensure SQL queries include context from previous queries
4. Validate SQL queries against the actual schema

## Conclusion

The core issue appears to be integration between components rather than missing functionality. The individual services have been implemented, but they're not effectively communicating with each other in the case of follow-up questions. By enhancing the integration points between these services, the system should be able to properly handle follow-up queries. 