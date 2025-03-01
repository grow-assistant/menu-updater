import json
import logging
import os
import glob
import time
from . import load_example_queries  # Import the function from prompts package

# Get the logger that was configured in utils/langchain_integration.py
logger = logging.getLogger("ai_menu_updater")

# For Gemini token counting
try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")  # Using OpenAI's tokenizer as approximation
    
    def count_tokens(text):
        """Count tokens in a string using tiktoken"""
        if not text:
            return 0
        try:
            return len(TOKENIZER.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {str(e)}")
            # Fallback approximation: ~4 chars per token
            return len(text) // 4
except ImportError:
    logger.warning("tiktoken not available, using character-based approximation")
    def count_tokens(text):
        """Approximate token count (4 chars ≈ 1 token)"""
        if not text:
            return 0
        return len(text) // 4


def create_gemini_prompt(
    user_query,
    context_files,
    location_id,
    conversation_history=None,
    previous_sql=None,
    date_context=None,
):
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
    start_time = time.time()
    
    # Log input parameters
    logger.info(f"Gemini prompt inputs: user_query='{user_query}', location_id={location_id}, " 
                f"has_conversation_history={bool(conversation_history)}, " 
                f"has_previous_sql={bool(previous_sql)}, " 
                f"date_context={date_context}")
    
    # Extract context files with error handling
    business_rules = context_files.get("business_rules", "Business rules unavailable")

    # When business_rules is a dictionary, update the time_period_guidance to use the current location_id
    if isinstance(business_rules, dict) and "time_period_guidance" in business_rules:
        for key, value in business_rules["time_period_guidance"].items():
            if isinstance(value, str) and "[LOCATION_ID]" in value:
                business_rules["time_period_guidance"][key] = value.replace(
                    "[LOCATION_ID]", str(location_id)
                )
    # If it's a string, replace placeholders directly
    elif isinstance(business_rules, str):
        business_rules = business_rules.replace("[LOCATION_ID]", str(location_id))

    # Truncate database schema if too long
    database_schema = context_files.get(
        "database_schema", "Database schema unavailable"
    )
    
    MAX_SCHEMA_LENGTH = 3000
    if len(database_schema) > MAX_SCHEMA_LENGTH:
        database_schema = database_schema[:MAX_SCHEMA_LENGTH] + "...(truncated)"
    
    # Determine query category from user query to load specific examples
    query_type = None
    # First check if we already have a categorized query type from the context
    if context_files and "categorized_type" in context_files:
        query_type = context_files["categorized_type"]
        logger.info(f"Using pre-categorized query type: {query_type}")
    
    # If no pre-categorized type, try to determine from query text
    if not query_type:
        for category in ["order_history", "update_price", "disable_item", "enable_item", 
                        "query_menu", "query_performance", "query_ratings", "delete_options"]:
            if category.lower() in user_query.lower():
                query_type = category
                logger.info(f"Determined query type from text: {query_type}")
                break
    
    # Try to infer the query type from the conversation history if not found in the query
    if not query_type and conversation_history and len(conversation_history) > 0:
        last_query = conversation_history[-1].get('query', '')
        for category in ["order_history", "update_price", "disable_item", "enable_item", 
                        "query_menu", "query_performance", "query_ratings", "delete_options"]:
            if category.lower() in last_query.lower():
                query_type = category
                logger.info(f"Inferred query type '{query_type}' from previous conversation")
                break
    
    # Load example queries directly from the database folders
    logger.info(f"Loading examples for query type: {query_type if query_type else 'ALL TYPES'}")
    all_examples = load_example_queries(query_type)
    logger.info(f"Loaded example length: {len(all_examples) if all_examples else 0} characters")
    
    # Limit number of example queries to reduce prompt size
    MAX_EXAMPLES_PER_CATEGORY = 10
    MAX_TOTAL_EXAMPLES = 10
    
    # Process examples to limit their size
    example_categories = all_examples.split('\n\n')
    limited_examples = []
    example_count = 0
    
    for category in example_categories:
        if not category.strip():
            continue
            
        # Skip if we've reached our max total examples
        if example_count >= MAX_TOTAL_EXAMPLES:
            break
            
        # Extract category lines
        lines = category.split('\n')
        if not lines:
            continue
            
        # First line is usually the category title
        title = lines[0]
        limited_examples.append(title)
        
        # Process examples in this category
        example_lines = []
        category_count = 0
        
        for i in range(1, len(lines)):
            example_lines.append(lines[i])
            
            # If this is a SQL line, count it as an example
            if lines[i].startswith("SQL:"):
                category_count += 1
                example_count += 1
                
                # Truncate long SQL
                if len(lines[i]) > 500:
                    example_lines[-1] = lines[i][:500] + " ... (truncated)"
                
                # If we've reached our limit for this category, add what we have and break
                if category_count >= MAX_EXAMPLES_PER_CATEGORY or example_count >= MAX_TOTAL_EXAMPLES:
                    limited_examples.extend(example_lines)
                    break
        
        # Add all lines for this category if we didn't hit a limit
        if category_count < MAX_EXAMPLES_PER_CATEGORY:
            limited_examples.extend(example_lines)
    
    # Join the limited examples back together
    example_queries = "\n".join(limited_examples)
    
    # Format user query for better processing - strip whitespace and ensure question ends with ?
    formatted_query = user_query.strip().rstrip("?") + "?"

    # Extract previous conversation context if available
    previous_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent conversation
        last_exchange = conversation_history[-1]
        
        # Truncate previous SQL if too long
        prev_sql = last_exchange.get('sql', '')
        if len(prev_sql) > 300:
            prev_sql = prev_sql[:300] + "... (truncated)"
            
        previous_context = f"""
PREVIOUS QUERY CONTEXT:
Previous Question: "{last_exchange.get('query', '')}"
Previous SQL: "{prev_sql}"
Previous Results: {len(last_exchange.get('results', []))} rows returned

When generating SQL for this query, maintain context from the previous query (especially date filters, 
location filters, and other constraints) unless the new query explicitly overrides them.
"""

    # Add order detail requirements if needed
    order_detail_section = ""
    if any(
        term in user_query.lower()
        for term in [
            "order detail",
            "order history",
            "order info",
            "customer order",
            "order lookup",
            "find order",
            "show order",
            "get order",
            "specific order",
            "order number",
        ]
    ):
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

    # Truncate business rules if it's a string and too long
    if isinstance(business_rules, str) and len(business_rules) > 1000:
        business_rules = business_rules[:1000] + "... (truncated)"
    
    # For dictionary business rules, convert to string with a reasonable limit
    if isinstance(business_rules, dict):
        try:
            rules_str = json.dumps(business_rules, indent=2)
            if len(rules_str) > 1000:
                # Try to extract key information instead of showing all
                key_rules = {
                    "order_status": business_rules.get("order_status", {}),
                    "time_period_guidance": business_rules.get("time_period_guidance", {})
                }
                rules_str = json.dumps(key_rules, indent=2)
                if len(rules_str) > 1000:
                    rules_str = rules_str[:1000] + "... (truncated)"
            business_rules = rules_str
        except Exception as e:
            logger.warning(f"Error converting business rules to JSON: {str(e)}")
            business_rules = str(business_rules)[:1000] + "... (truncated)"

    # Create a comprehensive prompt with all context files and specific guidelines
    prompt = f"""You are an expert SQL developer specializing in restaurant order systems. Your task is to generate precise SQL queries for a restaurant management system.

USER QUESTION: {formatted_query}

{date_context or 'No explicit date filter context provided'}
{previous_context}
{order_detail_section}

DATABASE SCHEMA:
{database_schema}

BUSINESS RULES:
{business_rules}

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

Generate ONLY a clean, efficient SQL query that precisely answers the user's question. No explanations or commentary.
"""

    # Count tokens in the prompt
    prompt_tokens = count_tokens(prompt)
    processing_time = time.time() - start_time
    
    # Log token counts and processing time
    logger.info(f"Generated Gemini prompt: {prompt[:200]}..." if len(prompt) > 200 else prompt)
    logger.info(f"Generated Gemini prompt for query '{user_query}' - Length: {len(prompt)} characters")
    logger.info(f"Gemini prompt tokens: {prompt_tokens} (approximate)")
    logger.info(f"Prompt generation time: {processing_time:.2f} seconds")
    logger.debug(f"Gemini prompt first 100 chars: {prompt[:100]}...")
    
    return prompt


# Add a function to log Gemini API response tokens and timing
def log_gemini_response(query, response, start_time):
    """Log token counts and timing for a Gemini API response"""
    response_time = time.time() - start_time
    response_text = response if isinstance(response, str) else str(response)
    response_tokens = count_tokens(response_text)
    
    logger.info(f"Gemini response received for query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
    logger.info(f"Gemini response tokens: {response_tokens} (approximate)")
    logger.info(f"Gemini response time: {response_time:.2f} seconds")
    logger.info(f"Gemini total tokens (prompt+response): {count_tokens(query) + response_tokens}")
    
    return response
