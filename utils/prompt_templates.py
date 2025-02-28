"""
Prompt templates for various AI interactions in the application.
This module centralizes all prompt creation logic for better maintainability.
"""

import json
import os
from typing import Dict, Any, Optional, List

def create_categorization_prompt() -> str:
    """Create an optimized categorization prompt for OpenAI
    
    Returns:
        str: An optimized prompt for OpenAI query categorization
    """
    # ENHANCEMENT 1: Improved categorization prompt with clearer guidance and examples
    return """You are an expert query categorization system for a restaurant management application. 
Analyze user queries and classify them into the correct category from the following options:

QUERY CATEGORIES:
- "order_history": Requests related to past orders, revenue, sales figures, order counts, or trends
- "update_price": Requests to change a menu item's price
- "disable_item": Requests to disable/remove a menu item from availability
- "enable_item": Requests to re-enable/restore a menu item to availability
- "query_menu": Questions about current menu, item availability, pricing, or menu structure
- "query_performance": Questions about business metrics, trends, or performance indicators
- "query_ratings": Questions about customer ratings, feedback, or satisfaction metrics

For "order_history" queries, also identify:
- time_period: The specific timeframe (today, yesterday, last week, this month, custom date range)
- analysis_type: What's being analyzed (count, revenue, details, trend, comparison)

EXAMPLES BY CATEGORY:
1. order_history:
   - "How many orders were completed yesterday?" → time_period=yesterday, analysis_type=count
   - "Show revenue from last week" → time_period=last_week, analysis_type=revenue
   - "What were our busiest days this month?" → time_period=this_month, analysis_type=trend

2. update_price:
   - "Update the price of French Fries to $4.99" → item_name=French Fries, new_price=4.99
   - "Change Burger price to $8.50" → item_name=Burger, new_price=8.50

3. disable_item:
   - "Disable the Chocolate Cake menu item" → item_name=Chocolate Cake
   - "Remove Veggie Burger from the menu" → item_name=Veggie Burger

4. enable_item:
   - "Make the Veggie Burger available again" → item_name=Veggie Burger
   - "Add Apple Pie back to the menu" → item_name=Apple Pie

5. query_menu:
   - "Show all active dessert items" 
   - "What vegetarian options do we have?"
   - "How much does the Caesar Salad cost?"

6. query_performance:
   - "What's our average order value this month?"
   - "How do weekday sales compare to weekend sales?"
   - "Which time of day has the highest sales?"

7. query_ratings:
   - "Show orders with low customer ratings"
   - "What menu items get the most complaints?"
   - "What's our average customer satisfaction score?"

CATEGORIZATION APPROACH:
1. First, identify the core intent (retrieving information vs. making changes)
2. For information requests, determine if they're about orders, menu items, performance, or ratings
3. For change requests, determine if they're updating prices, enabling, or disabling items
4. Look for time-related terms to identify time periods for order_history queries
5. Pay attention to verbs like "update", "change", "disable", "remove", "show", "get" as intent indicators

Make the most accurate determination based on the query's intent and content.
Respond with the appropriate function call containing the categorized request."""

def create_gemini_prompt(user_query: str, context_files: Dict[str, Any], location_id: int = 62, conversation_history: Optional[List[Dict]] = None, previous_sql: Optional[str] = None, previous_results: Optional[List[Dict]] = None, order_detail_fields: Optional[Dict] = None, date_context_instruction: str = "") -> str:
    """Create an optimized prompt for Google Gemini with full business context and conversation history
    
    Args:
        user_query (str): The user's original query
        context_files (dict): Dictionary containing business rules, schema, and example queries
        location_id (int, optional): The location ID to filter data. Defaults to 62.
        conversation_history (list, optional): Previous exchanges in the conversation
        previous_sql (str, optional): The previously executed SQL query
        previous_results (list, optional): Results from previous queries
        order_detail_fields (dict, optional): Order detail fields to include
        date_context_instruction (str, optional): Specific instructions for date filtering
        
    Returns:
        str: The optimized prompt for SQL generation
    """
    # Extract context files with error handling
    business_rules = context_files.get('business_rules', 'Business rules unavailable')
    database_schema = context_files.get('database_schema', 'Database schema unavailable')
    example_queries = context_files.get('example_queries', 'Example queries unavailable')
    
    # Format user query for better processing
    formatted_query = user_query.strip().rstrip('?') + '?'
    
    # NEW: Add conversation context for follow-up queries
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Extract the last 3 exchanges to provide context
        recent_exchanges = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        conversation_context = "RECENT CONVERSATION:\n"
        for i, exchange in enumerate(recent_exchanges):
            conversation_context += f"- User asked: {exchange.get('query', '')}\n"
            if exchange.get('sql'):
                conversation_context += f"  SQL used: {exchange.get('sql', '')}\n"
            if exchange.get('results'):
                conversation_context += f"  Results showed: {str(exchange.get('results', [])[:1])} [...]\n\n"
    
    # NEW: Add previous SQL context if available
    previous_sql_context = ""
    if previous_sql:
        previous_sql_context = f"PREVIOUS SQL QUERY:\n{previous_sql}\n\n"
        
    # NEW: Add stronger date filtering guidance
    date_filtering_context = """
⚠️ MANDATORY DATE FILTERING:
1. EVERY query MUST filter by date using:
   (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE
2. This MUST be in the WHERE clause, not just the SELECT list
3. Simply including this in the SELECT output is NOT sufficient
4. The exact pattern must be in a WHERE or HAVING clause
5. DEFAULT TO CURRENT_DATE unless user explicitly requests another date

Examples:
✅ WHERE (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE
✅ WHERE (o.updated_at - INTERVAL '7 hours')::date = '2023-10-15'
❌ SELECT (o.updated_at - INTERVAL '7 hours')::date (Missing WHERE filter)
"""
    
    # NEW: Detect if this is a follow-up query
    is_followup = is_followup_query(user_query, conversation_history)
    
    followup_guidance = ""
    if is_followup:
        followup_guidance = (
            "FOLLOW-UP QUERY GUIDANCE:\n"
            "This appears to be a follow-up question to previous queries. When generating SQL:\n"
            "1. Reference the previous SQL query structure when appropriate\n"
            "2. Maintain the same filters for location_id and other consistent parameters\n"
            "3. If the user refers to 'those orders' or similar, use the same WHERE conditions from the previous query\n"
            "4. For 'more details' requests, expand the SELECT clause while keeping the same core query structure\n"
            "5. For time-based follow-ups, maintain the date range from the previous query unless explicitly changed\n\n"
        )
    
    # Add order detail fields if provided
    if order_detail_fields and "order_history" in user_query.lower():
        formatted_query += "\n\nWhen returning order details, please include these specific fields:\n"
        formatted_query += f"- Customer Info: {', '.join(order_detail_fields['customer_info'])}\n"
        formatted_query += f"- Order Info: {', '.join(order_detail_fields['order_info'])}\n"
        formatted_query += f"- SQL Guidance: {order_detail_fields['query_guidance']}\n"
    
    # Add special handling for average-related queries
    if "average" in user_query.lower() or "avg" in user_query.lower():
        formatted_query += "\n\nIMPORTANT: When calculating any average, you MUST include the total count of records and the count of non-null values used in the calculation to provide proper context. This is mandatory for all average calculations."
        
    # Add special handling for rating-related queries
    if "rating" in user_query.lower() or "feedback" in user_query.lower():
        formatted_query += "\n\nCRITICAL FOR RATINGS: When querying ratings data, you MUST:\n"
        formatted_query += "1. Count an order as having a rating ONLY if f.id IS NOT NULL (not r.id IS NOT NULL)\n"
        formatted_query += "2. Include these exact metrics:\n"
        formatted_query += "   - COUNT(DISTINCT o.id) AS total_orders\n"
        formatted_query += "   - COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) AS orders_with_ratings\n"
        formatted_query += "   - COUNT(DISTINCT CASE WHEN f.id IS NULL THEN o.id END) AS orders_without_ratings\n"
        formatted_query += "   - Calculate percent_with_ratings using orders_with_ratings / total_orders\n"
        formatted_query += "3. For average calculations, only include orders with actual feedback values\n"
        formatted_query += "4. Follow this exact join pattern: orders → order_ratings → order_ratings_feedback\n"
    
    formatted_query += (
        "\nDATE HANDLING: Always use (o.updated_at - INTERVAL '7 hours')::date "
        "for date comparisons, NOT time zone conversions"
    )
    
    # Create a comprehensive prompt with all context files and specific guidelines
    return f"""You are an expert SQL developer specializing in restaurant order systems. Your task is to generate precise SQL queries for a restaurant management system.

USER QUESTION: {formatted_query}

{conversation_context}
{previous_sql_context}
{date_filtering_context}
{followup_guidance}

DATABASE SCHEMA:
{database_schema}

BUSINESS RULES:
{business_rules}

EXAMPLE QUERIES FOR REFERENCE:
{example_queries}

QUERY GUIDELINES:
1. Always include explicit JOINs with proper table aliases (e.g., 'o' for orders, 'u' for users, 'l' for locations)
2. Always filter by location_id = {location_id} to ensure accurate restaurant-specific data
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

Generate ONLY a clean, efficient SQL query that precisely answers the user's question. No explanations or commentary.
"""

def create_summary_prompt(user_query: str, sql_query: str, result: Dict[str, Any], query_type: Optional[str] = None, conversation_history: Optional[List[Dict]] = None) -> str:
    """Generate an optimized prompt for OpenAI summarization with conversation history
    
    Args:
        user_query (str): The original user query
        sql_query (str): The executed SQL query
        result (dict): The database result dictionary
        query_type (str, optional): The type of query (order_history, query_menu, etc.)
        conversation_history (list, optional): Previous exchanges in the conversation
        
    Returns:
        str: The optimized prompt for summarization
    """
    # Format SQL query for better readability
    formatted_sql = sql_query.strip().replace("\n", " ").replace("  ", " ")
    
    # Extract query type from result if not provided
    if not query_type and "function_call" in result:
        query_type = result.get("function_call", {}).get("name", "unknown")
    
    # Add query-specific context based on query type
    type_specific_instructions = {
        "order_history": "Present order counts, revenue figures, and trends with proper formatting. Use dollar signs for monetary values and include percent changes for trends.",
        "query_performance": "Highlight key performance metrics, compare to benchmarks when available, and provide actionable business insights.",
        "query_menu": "Structure menu information clearly, listing items with their prices and availability status in an organized way.",
        "query_ratings": "Present rating metrics with context (e.g., 'above average', 'concerning') and suggest possible actions based on feedback.",
        "update_price": "Confirm the exact price change with both old and new values clearly stated.",
        "disable_item": "Confirm the item has been disabled and explain the impact (no longer available to customers).",
        "enable_item": "Confirm the item has been re-enabled and is now available to customers again."
    }
    
    type_guidance = type_specific_instructions.get(query_type, "Provide a clear, direct answer to the user's question.")
    
    # Determine if we have empty results to provide better context
    results_count = len(result.get('results', []))
    result_context = ""
    if results_count == 0:
        result_context = "The query returned no results, which typically means no data matches the specified criteria for the given time period or filters."
    
    # NEW: Add conversation context for follow-up queries
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Extract the last 2-3 exchanges to provide context
        recent_exchanges = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        conversation_context = "CONVERSATION HISTORY:\n"
        for i, exchange in enumerate(recent_exchanges):
            if 'query' in exchange and 'answer' in exchange:
                conversation_context += f"User: {exchange['query']}\nAssistant: {exchange['answer']}\n\n"
    
    # NEW: Detect if this is a follow-up query
    is_followup = is_followup_query(user_query, conversation_history)
    
    followup_guidance = ""
    if is_followup:
        followup_guidance = (
            "This appears to be a follow-up question. Connect your answer to the previous context. "
            "Reference specific details from previous exchanges when relevant. "
            "Maintain continuity in your explanation style and terminology."
        )
    
    # Build optimized prompt with enhanced context and guidance
    return (
        f"USER QUERY: '{user_query}'\n\n"
        f"{conversation_context}\n"
        f"SQL QUERY: {formatted_sql}\n\n"
        f"QUERY TYPE: {query_type}\n\n"
        f"DATABASE RESULTS: {json.dumps(result.get('results', []), indent=2)}\n\n"
        f"RESULT CONTEXT: {result_context}\n\n"
        f"BUSINESS CONTEXT:\n"
        f"- Order statuses: 0=Open, 1=Pending, 2=Confirmed, 3=In Progress, 4=Ready, 5=In Transit, 6=Cancelled, 7=Completed, 8=Refunded\n"
        f"- Order types: 1=Delivery, 2=Pickup, 3=Dine-In\n"
        f"- Revenue values are in USD\n"
        f"- Ratings are on a scale of 1-5, with 5 being highest\n\n"
        f"SPECIFIC GUIDANCE FOR {query_type.upper()}: {type_guidance}\n\n"
        f"{followup_guidance}\n\n"
        f"SUMMARY INSTRUCTIONS:\n"
        f"1. Provide a clear, direct answer to the user's question\n"
        f"2. Include relevant metrics with proper formatting ($ for money, % for percentages)\n"
        f"3. If no results were found, explain what that means in business terms\n"
        f"4. Use natural, conversational language with a friendly, helpful tone\n"
        f"5. Be specific about the time period mentioned in the query\n"
        f"6. Keep the response concise but informative\n"
        f"7. If appropriate, suggest a follow-up question the user might want to ask\n"
    )

def create_system_prompt_with_business_rules() -> str:
    """Create a system prompt that includes business rules for the summarization step
    
    Returns:
        str: System prompt with business rules context
    """
    try:
        from prompts.business_rules import ORDER_STATUS, RATING_SIGNIFICANCE, ORDER_FILTERS
        
        business_context = {
            "order_status": ORDER_STATUS,
            "rating_significance": RATING_SIGNIFICANCE,
            "order_filters": ORDER_FILTERS
        }
        
        # Enhanced system prompt with business rules and conversational guidelines
        return (
            "You are a helpful restaurant analytics assistant that translates database results into natural language answers. "
            "Your goal is to provide clear, actionable insights from restaurant order data. "
            f"Use these business rules for context: {json.dumps(business_context, indent=2)}\n\n"
            "CONVERSATIONAL GUIDELINES:\n"
            "1. Use a friendly, professional tone that balances expertise with approachability\n"
            "2. Begin responses with a direct answer to the question, then provide supporting details\n"
            "3. Use natural transitions between ideas and maintain a conversational flow\n"
            "4. Highlight important metrics or insights with bold formatting (**like this**)\n"
            "5. For follow-up questions, explicitly reference previous context\n"
            "6. When appropriate, end with a subtle suggestion for what the user might want to know next\n"
            "7. Keep responses concise but complete - prioritize clarity over verbosity\n"
            "8. Use bullet points or numbered lists for multiple data points\n"
            "9. Format currency values with dollar signs and commas ($1,234.56)\n"
            "10. When discussing ratings, include their significance (e.g., '5.0 - Very Satisfied')\n"
        )
    except ImportError:
        # Fallback if business rules can't be imported
        return (
            "You are a helpful restaurant analytics assistant that translates database results into natural language answers. "
            "Your goal is to provide clear, actionable insights from restaurant order data.\n\n"
            "CONVERSATIONAL GUIDELINES:\n"
            "1. Use a friendly, professional tone that balances expertise with approachability\n"
            "2. Begin responses with a direct answer to the question, then provide supporting details\n"
            "3. Use natural transitions between ideas and maintain a conversational flow\n"
            "4. Highlight important metrics or insights with bold formatting (**like this**)\n"
            "5. For follow-up questions, explicitly reference previous context\n"
            "6. When appropriate, end with a subtle suggestion for what the user might want to know next\n"
            "7. Keep responses concise but complete - prioritize clarity over verbosity\n"
            "8. Use bullet points or numbered lists for multiple data points\n"
            "9. Format currency values with dollar signs and commas ($1,234.56)\n"
            "10. When discussing ratings, include their significance (e.g., '5.0 - Very Satisfied')\n"
        )

def is_followup_query(user_query: str, conversation_history: Optional[List[Dict]] = None) -> bool:
    """Determine if a query is a follow-up to previous conversation with more sophisticated detection.
    
    Args:
        user_query (str): The current user query
        conversation_history (list, optional): Previous exchanges in the conversation
        
    Returns:
        bool: True if the query appears to be a follow-up, False otherwise
    """
    # Normalize the query
    query_lower = user_query.lower().strip()
    
    # 1. Check for explicit follow-up indicators
    explicit_indicators = [
        "those", "these", "that", "it", "they", "them", "their",
        "previous", "last", "again", "more", "further", "additional",
        "also", "too", "as well", "what about", "how about", "tell me more",
        "can you elaborate", "show me", "what else", "and", "what if"
    ]
    
    # Check if query starts with certain phrases
    starting_phrases = [
        "what about", "how about", "what if", "and what", "and how", 
        "can you also", "could you also", "show me", "tell me more"
    ]
    
    # Check if query is very short (likely a follow-up)
    is_short_query = len(query_lower.split()) <= 3
    
    # 2. Check for pronouns without clear referents
    has_pronoun_without_referent = False
    pronouns = ["it", "they", "them", "those", "these", "that", "this"]
    for pronoun in pronouns:
        # Check if pronoun exists as a standalone word
        if f" {pronoun} " in f" {query_lower} " and not any(noun in query_lower for noun in ["order", "revenue", "sales", "item", "menu", "customer"]):
            has_pronoun_without_referent = True
            break
    
    # 3. Check for incomplete queries that would need context
    incomplete_indicators = [
        query_lower.startswith("what about"),
        query_lower.startswith("how about"),
        query_lower.startswith("and "),
        query_lower.startswith("but "),
        query_lower.startswith("also "),
        query_lower.startswith("what if"),
        query_lower == "why",
        query_lower == "how",
        query_lower == "when",
        is_short_query and not any(x in query_lower for x in ["show", "list", "get", "find"])
    ]
    
    # 4. Context-based detection (if conversation history is available)
    context_based = False
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent query for comparison
        last_query = conversation_history[-1].get('query', '').lower() if 'query' in conversation_history[-1] else ''
        
        # Check for shared key terms between queries
        last_query_terms = set(last_query.split())
        current_query_terms = set(query_lower.split())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "in", "on", "at", "by", "for", "with", "about", "from", "to", "of"}
        last_query_terms = last_query_terms - stop_words
        current_query_terms = current_query_terms - stop_words
        
        # If the current query has significantly fewer terms and shares some with the previous query
        if len(current_query_terms) < len(last_query_terms) * 0.7:
            common_terms = current_query_terms.intersection(last_query_terms)
            if len(common_terms) > 0:
                context_based = True
    
    # Combine all detection methods
    return (
        any(indicator in query_lower.split() for indicator in explicit_indicators) or
        any(query_lower.startswith(phrase) for phrase in starting_phrases) or
        has_pronoun_without_referent or
        any(incomplete_indicators) or
        context_based
    ) 