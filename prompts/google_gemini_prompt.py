import json

def create_gemini_prompt(user_query, context_files, location_id, conversation_history=None, previous_sql=None, date_context=None):
    """Create an optimized prompt for Google Gemini with full business context
    
    Args:
        user_query (str): The user's original query
        context_files (dict): Dictionary containing business rules, schema, and example queries
        location_id (int): The location ID to filter data.
        conversation_history (list, optional): List of previous query exchanges. Defaults to None.
        previous_sql (str, optional): The SQL query from the previous interaction. Defaults to None.
        date_context (str, optional): Explicit date filtering context. Defaults to None.
        
    Returns:
        str: The optimized prompt for SQL generation
    """
    # Extract context files with error handling
    business_rules = context_files.get('business_rules', 'Business rules unavailable')
    
    # When business_rules is a dictionary, update the time_period_guidance to use the current location_id
    if isinstance(business_rules, dict) and 'time_period_guidance' in business_rules:
        for key, value in business_rules['time_period_guidance'].items():
            if isinstance(value, str) and '[LOCATION_ID]' in value:
                business_rules['time_period_guidance'][key] = value.replace('[LOCATION_ID]', str(location_id))
    # If it's a string, replace placeholders directly
    elif isinstance(business_rules, str):
        business_rules = business_rules.replace('[LOCATION_ID]', str(location_id))
    
    database_schema = context_files.get('database_schema', 'Database schema unavailable')
    example_queries = context_files.get('example_queries', 'Example queries unavailable')
    
    # Format user query for better processing - strip whitespace and ensure question ends with ?
    formatted_query = user_query.strip().rstrip('?') + '?'
    
    # Extract previous conversation context if available
    previous_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent conversation
        last_exchange = conversation_history[-1]
        previous_context = f"""
PREVIOUS QUERY CONTEXT:
Previous Question: "{last_exchange.get('query', '')}"
Previous SQL: "{last_exchange.get('sql', '')}"
Previous Results: {len(last_exchange.get('results', []))} rows returned

When generating SQL for this query, maintain context from the previous query (especially date filters, 
location filters, and other constraints) unless the new query explicitly overrides them.
"""
    
    # Add order detail requirements if needed
    order_detail_section = ""
    if any(term in user_query.lower() for term in ["order detail", "order history", "order info", "customer order", "order lookup", "find order", "show order", "get order", "specific order", "order number"]):
        order_detail_section = """
ORDER DETAIL REQUIREMENTS:
MUST INCLUDE THESE EXACT FIELDS:
- Customer: full_name (u.first_name || ' ' || u.last_name AS full_name), email (u.email), phone_number (u.phone)
- Order: order_id (o.id), total (o.total), tip (o.tip), updated_at (o.updated_at)
- Discount: discount_amount (d.amount) - NOT o.discount which doesn't exist
MUST USE THESE JOINS:
- INNER JOIN users u ON o.customer_id = u.id
- INNER JOIN locations l ON o.location_id = l.id
- LEFT JOIN discounts d ON d.order_id = o.id
"""
    
    # Create a comprehensive prompt with all context files and specific guidelines
    return f"""You are an expert SQL developer specializing in restaurant order systems. Your task is to generate precise SQL queries for a restaurant management system.

USER QUESTION: {formatted_query}

{date_context or 'No explicit date filter context provided'}
{previous_context}
{order_detail_section}

DATABASE SCHEMA:
{database_schema}

BUSINESS RULES:
{json.dumps(business_rules, indent=2) if isinstance(business_rules, dict) else business_rules}

EXAMPLE QUERIES FOR REFERENCE:
{example_queries}

QUERY GUIDELINES:
1. Always include explicit JOINs with proper table aliases (e.g., 'o' for orders, 'u' for users, 'l' for locations)
2. CRITICAL: ALWAYS filter by location_id = {location_id} for EVERY query, without exception
   - For menu queries (categories, items): JOIN categories to menus AND filter WHERE m.location_id = {location_id}
   - For order queries: filter WHERE o.location_id = {location_id}
   - For any table not directly having location_id, JOIN to a table that does and filter there
3. When querying completed orders, include status = 7 in your WHERE clause
4. Use COALESCE for nullable numeric fields to handle NULL values (e.g., COALESCE(total, 0) instead of just total)
5. Handle division operations safely with NULLIF to prevent division by zero (e.g., total / NULLIF(count, 0))
6. For date filtering, use the timezone adjusted timestamp: (updated_at - INTERVAL '7 hours')::date 
7. When aggregating data, use appropriate GROUP BY clauses with all non-aggregated columns
8. For improved readability, structure complex queries with CTEs (WITH clauses) for multi-step analysis
9. When counting or summing, ensure proper handling of NULL values with COALESCE or appropriate conditions
10. Always use updated_at instead of created_at for time-based calculations
11. For date format conversions, use TO_CHAR function with appropriate format (e.g., 'YYYY-MM-DD')
12. Include explicit ORDER BY clauses for consistent results, especially with LIMIT

COMMON QUERY PATTERNS:
1. For order counts: USE COUNT(o.id) with appropriate filters
2. For revenue: USE SUM(COALESCE(o.total, 0)) with proper grouping
3. For date ranges: USE BETWEEN or >= and <= with timezone adjusted dates
4. For menu items: JOIN orders, order_items, and items tables

STEP-BY-STEP APPROACH:
1. Identify the tables needed based on the question
2. Determine the appropriate JOIN conditions
3. Apply proper filtering (location, status, date range)
4. Select the correct aggregation functions if needed
5. Include proper GROUP BY, ORDER BY, and LIMIT clauses
6. Add NULL handling for numeric calculations

IMPORTANT: For follow-up queries, maintain date filters and other context from previous queries unless explicitly changed in the new query.

Generate ONLY a clean, efficient SQL query that precisely answers the user's question. No explanations or commentary.
"""
