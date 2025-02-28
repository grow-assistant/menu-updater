"""
Prompt templates for various AI interactions in the application.
This module centralizes all prompt creation logic for better maintainability.
"""

import json
from typing import Dict, Any, Optional, List


def create_categorization_prompt() -> str:
    """Create an optimized categorization prompt for OpenAI

    Returns:
        str: An optimized prompt for OpenAI query categorization
    """
    # ENHANCEMENT 1: Improved categorization prompt with clearer guidance and examples  # noqa: E501
    return """You are an expert query categorization system for a restaurant management application.  # noqa: E501
Analyze user queries and classify them into the correct category from the following options:  # noqa: E501

QUERY CATEGORIES:
- "order_history": Requests related to past orders, revenue, sales figures, order counts, or trends  # noqa: E501
- "update_price": Requests to change a menu item's price
- "disable_item": Requests to disable/remove a menu item from availability
- "enable_item": Requests to re-enable/restore a menu item to availability
- "query_menu": Questions about current menu, item availability, pricing, or menu structure  # noqa: E501
- "query_performance": Questions about business metrics, trends, or performance indicators  # noqa: E501
- "query_ratings": Questions about customer ratings, feedback, or satisfaction metrics  # noqa: E501

For "order_history" queries, also identify:
- time_period: The specific timeframe (today, yesterday, last week, this month, custom date range)  # noqa: E501
- analysis_type: What's being analyzed (count, revenue, details, trend, comparison)  # noqa: E501

EXAMPLES BY CATEGORY:
1. order_history:
   - "How many orders were completed yesterday?" → time_period=yesterday, analysis_type=count  # noqa: E501
   - "Show revenue from last week" → time_period=last_week, analysis_type=revenue  # noqa: E501
   - "What were our busiest days this month?" → time_period=this_month, analysis_type=trend  # noqa: E501

2. update_price:
   - "Update the price of French Fries to $4.99" → item_name=French Fries, new_price=4.99  # noqa: E501
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
2. For information requests, determine if they're about orders, menu items, performance, or ratings  # noqa: E501
3. For change requests, determine if they're updating prices, enabling, or disabling items  # noqa: E501
4. Look for time-related terms to identify time periods for order_history queries  # noqa: E501
5. Pay attention to verbs like "update", "change", "disable", "remove", "show", "get" as intent indicators  # noqa: E501

Make the most accurate determination based on the query's intent and content.
Respond with the appropriate function call containing the categorized request."""  # noqa: E501


def create_gemini_prompt(
    user_query: str,
    context_files: Dict[str, Any],
    location_id: int = 62,
    conversation_history: Optional[List[Dict]] = None,
    previous_sql: Optional[str] = None,
    previous_results: Optional[List[Dict]] = None,
    order_detail_fields: Optional[Dict] = None,
    date_context_instruction: str = "",
) -> str:
    """Create an optimized prompt for Google Gemini with full business context and conversation history  # noqa: E501

    Args:
        user_query (str): The user's original query
        context_files (dict): Dictionary containing business rules, schema, and example queries  # noqa: E501
        location_id (int, optional): The location ID to filter data. Defaults to 62.  # noqa: E501
        conversation_history (list, optional): Previous exchanges in the conversation  # noqa: E501
        previous_sql (str, optional): The previously executed SQL query
        previous_results (list, optional): Results from previous queries
        order_detail_fields (dict, optional): Order detail fields to include
        date_context_instruction (str, optional): Specific instructions for date filtering  # noqa: E501

    Returns:
        str: The optimized prompt for SQL generation
    """
    # Extract context files with error handling
    business_rules = context_files.get(
        "business_rules", "Business rules unavailable"
    )  # noqa: E501
    database_schema = context_files.get(
        "database_schema", "Database schema unavailable"
    )  # noqa: E501
    example_queries = context_files.get(
        "example_queries", "Example queries unavailable"
    )  # noqa: E501

    # Format user query for better processing
    formatted_query = user_query.strip().rstrip("?") + "?"

    # NEW: Add conversation context for follow-up queries
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Extract the last 3 exchanges to provide context
        recent_exchanges = (
            conversation_history[-3:]
            if len(conversation_history) >= 3
            else conversation_history
        )  # noqa: E501
        conversation_context = "RECENT CONVERSATION:\n"
        for i, exchange in enumerate(recent_exchanges):
            conversation_context += (
                f"- User asked: {exchange.get('query', '')}\n"  # noqa: E501
            )
            if exchange.get("sql"):
                conversation_context += (
                    f"  SQL used: {exchange.get('sql', '')}\n"  # noqa: E501
                )
            if exchange.get("results"):
                result_preview = str(exchange.get("results", [])[:1])
                conversation_context += (
                    f"  Results showed: {result_preview} [...]\n\n"  # noqa: E501
                )

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
            "This appears to be a follow-up question to previous queries. When generating SQL:\n"  # noqa: E501
            "1. Reference the previous SQL query structure when appropriate\n"
            "2. Maintain the same filters for location_id and other consistent parameters\n"  # noqa: E501
            "3. If the user refers to 'those orders' or similar, use the same WHERE conditions\n"  # noqa: E501
            "4. For 'more details' requests, expand the SELECT clause while keeping the same core\n"  # noqa: E501
            "   query structure\n"
            "5. For time-based follow-ups, maintain the date range from the previous query unless\n"  # noqa: E501
            "   explicitly changed\n\n"
        )

    # Add order detail fields if provided
    order_detail_guidance = ""
    if order_detail_fields and "order_history" in user_query.lower():
        order_detail_guidance = "\n\nWhen returning order details, please include these specific fields:\n"  # noqa: E501
        order_detail_guidance += f"- Customer Info: {', '.join(order_detail_fields['customer_info'])}\n"  # noqa: E501
        order_detail_guidance += f"- Order Info: {', '.join(order_detail_fields['order_info'])}\n"  # noqa: E501
        order_detail_guidance += (
            f"- SQL Guidance: {order_detail_fields['query_guidance']}\n"  # noqa: E501
        )

    # Add special handling for average-related queries
    avg_guidance = ""
    if "average" in user_query.lower() or "avg" in user_query.lower():
        avg_guidance = "\n\nIMPORTANT: When calculating any average, you MUST include the total "  # noqa: E501
        avg_guidance += "count of records and the count of non-null values used in the calculation "  # noqa: E501
        avg_guidance += "to provide proper context. This is mandatory for all average calculations."  # noqa: E501

    # Add special handling for rating-related queries
    rating_guidance = ""
    if "rating" in user_query.lower() or "feedback" in user_query.lower():
        rating_guidance = "\n\nCRITICAL FOR RATINGS: When querying ratings data, you MUST:\n"  # noqa: E501
        rating_guidance += "1. Count an order as having a rating ONLY if f.id IS NOT NULL\n"  # noqa: E501
        rating_guidance += "2. Include these exact metrics:\n"
        rating_guidance += "   - COUNT(DISTINCT o.id) AS total_orders\n"
        rating_guidance += "   - COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) "  # noqa: E501
        rating_guidance += "AS orders_with_ratings\n"
        rating_guidance += (
            "   - COUNT(DISTINCT CASE WHEN f.id IS NULL THEN o.id END) "  # noqa: E501
        )
        rating_guidance += "AS orders_without_ratings\n"
        rating_guidance += "   - Calculate percent_with_ratings using orders_with_ratings / total_orders\n"  # noqa: E501
        rating_guidance += "3. For average calculations, only include orders with actual feedback values\n"  # noqa: E501
        rating_guidance += "4. Follow this exact join pattern: orders → order_ratings → order_ratings_feedback\n"  # noqa: E501

    date_handling = (
        "\nDATE HANDLING: Always use (o.updated_at - INTERVAL '7 hours')::date "  # noqa: E501
        "for date comparisons, NOT time zone conversions"
    )

    # Create a comprehensive prompt with all context files and specific guidelines  # noqa: E501
    return f"""You are an expert SQL developer specializing in restaurant order systems. Your task is to generate precise SQL queries for a restaurant management system.  # noqa: E501

USER QUESTION: {formatted_query}{order_detail_guidance}{avg_guidance}{rating_guidance}{date_handling}  # noqa: E501

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
1. Always include explicit JOINs with proper table aliases (e.g., 'o' for orders, 'u' for users)  # noqa: E501
2. Always filter by location_id = {location_id} to ensure accurate restaurant-specific data  # noqa: E501
3. When querying completed orders, include status = 7 in your WHERE clause
4. Use COALESCE for nullable numeric fields to handle NULL values
5. Handle division operations safely with NULLIF to prevent division by zero
6. For date filtering, use the timezone adjusted timestamp: (updated_at - INTERVAL '7 hours')::date  # noqa: E501
7. When aggregating data, use appropriate GROUP BY clauses with all non-aggregated columns  # noqa: E501
8. For improved readability, structure complex queries with CTEs (WITH clauses)
9. When counting or summing, ensure proper handling of NULL values
10. Always use updated_at instead of created_at for time-based calculations
11. For date format conversions, use TO_CHAR function with appropriate format
12. Include explicit ORDER BY clauses for consistent results, especially with LIMIT  # noqa: E501

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

Generate ONLY a clean, efficient SQL query that precisely answers the user's question.  # noqa: E501
No explanations or commentary.
"""


def create_summary_prompt(
    user_query: str,
    sql_query: str,
    result: Dict[str, Any],
    query_type: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None,
) -> str:
    """Generate an optimized prompt for OpenAI summarization with conversation history  # noqa: E501

    Args:
        user_query (str): The original user query
        sql_query (str): The executed SQL query
        result (dict): The database result dictionary
        query_type (str, optional): The type of query (order_history, query_menu, etc.)  # noqa: E501
        conversation_history (list, optional): Previous exchanges in the conversation  # noqa: E501

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
        "order_history": "Present order counts, revenue figures, and trends with proper formatting. "  # noqa: E501
        "Use dollar signs for monetary values and include percent changes for trends.",  # noqa: E501
        "query_performance": "Highlight key performance metrics, compare to benchmarks when available, "  # noqa: E501
        "and provide actionable business insights.",
        "query_menu": "Structure menu information clearly, listing items with their prices "  # noqa: E501
        "and availability status in an organized way.",
        "query_ratings": "Present rating metrics with context (e.g., 'above average', 'concerning') "  # noqa: E501
        "and suggest possible actions based on feedback.",
        "update_price": "Confirm the exact price change with both old and new values clearly stated.",  # noqa: E501
        "disable_item": "Confirm the item has been disabled and explain the impact "  # noqa: E501
        "(no longer available to customers).",
        "enable_item": "Confirm the item has been re-enabled and is now available to customers again.",  # noqa: E501
    }

    type_guidance = type_specific_instructions.get(
        query_type, "Provide a clear, direct answer to the user's question."
    )
    # Determine if we have empty results to provide better context
    results_count = len(result.get("results", []))
    result_context = ""
    if results_count == 0:
        result_context = (
            "The query returned no results, which typically means no data matches "  # noqa: E501
            "the specified criteria for the given time period or filters."
        )  # noqa: E501

    # NEW: Add conversation context for follow-up queries
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Extract the last 2-3 exchanges to provide context
        recent_exchanges = (
            conversation_history[-3:]
            if len(conversation_history) >= 3
            else conversation_history
        )  # noqa: E501
        conversation_context = "CONVERSATION HISTORY:\n"
        for i, exchange in enumerate(recent_exchanges):
            if "query" in exchange and "answer" in exchange:
                conversation_context += f"User: {exchange['query']}\nAssistant: {exchange['answer']}\n\n"  # noqa: E501

    # NEW: Detect if this is a follow-up query
    is_followup = is_followup_query(user_query, conversation_history)

    followup_guidance = ""
    if is_followup:
        followup_guidance = (
            "This appears to be a follow-up question. Connect your answer to the previous context. "  # noqa: E501
            "Reference specific details from previous exchanges when relevant. "  # noqa: E501
            "Maintain continuity in your explanation style and terminology."
        )

    # Build optimized prompt with enhanced context and guidance
    return (
        f"USER QUERY: '{user_query}'\n\n"
        f"{conversation_context}\n"
        f"SQL QUERY: {formatted_sql}\n\n"
        f"QUERY TYPE: {query_type}\n\n"
        f"DATABASE RESULTS: {json.dumps(result.get('results', []), indent=2)}\n\n"  # noqa: E501
        f"RESULT CONTEXT: {result_context}\n\n"
        f"BUSINESS CONTEXT:\n"
        f"- Order statuses: 0=Open, 1=Pending, 2=Confirmed, 3=In Progress, 4=Ready, 5=In Transit, "  # noqa: E501
        f"6=Cancelled, 7=Completed, 8=Refunded\n"
        f"- Order types: 1=Delivery, 2=Pickup, 3=Dine-In\n"
        f"- Revenue values are in USD\n"
        f"- Ratings are on a scale of 1-5, with 5 being highest\n\n"
        f"SPECIFIC GUIDANCE FOR {query_type.upper()}: {type_guidance}\n\n"
        f"{followup_guidance}\n\n"
        f"SUMMARY INSTRUCTIONS:\n"
        f"1. Provide a clear, direct answer to the user's question\n"
        f"2. Include relevant metrics with proper formatting ($ for money, % for percentages)\n"  # noqa: E501
        f"3. If no results were found, explain what that means in business terms\n"  # noqa: E501
        f"4. Use natural, conversational language with a friendly, helpful tone\n"  # noqa: E501
        f"5. Be specific about the time period mentioned in the query\n"
        f"6. Keep the response concise but informative\n"
        f"7. If appropriate, suggest a follow-up question the user might want to ask\n"  # noqa: E501
    )


def create_system_prompt_with_business_rules() -> str:
    """Create a system prompt that includes business rules for the summarization step  # noqa: E501

    Returns:
        str: System prompt with business rules context
    """
    try:
        from prompts.business_rules import (
            ORDER_STATUS,
            RATING_SIGNIFICANCE,
            ORDER_FILTERS,
        )  # noqa: E501

        business_context = {
            "order_status": ORDER_STATUS,
            "rating_significance": RATING_SIGNIFICANCE,
            "order_filters": ORDER_FILTERS,
        }

        # Enhanced system prompt with business rules and conversational guidelines  # noqa: E501
        return (
            "You are a helpful restaurant analytics assistant that translates database results "  # noqa: E501
            "into natural language answers. "
            "Your goal is to provide clear, actionable insights from restaurant order data. "  # noqa: E501
            f"Use these business rules for context: {json.dumps(business_context, indent=2)}\n\n"  # noqa: E501
            "CONVERSATIONAL GUIDELINES:\n"
            "1. Use a friendly, professional tone that balances expertise with approachability\n"  # noqa: E501
            "2. Begin responses with a direct answer to the question, then provide supporting details\n"  # noqa: E501
            "3. Use natural transitions between ideas and maintain a conversational flow\n"  # noqa: E501
            "4. Highlight important metrics or insights with bold formatting (**like this**)\n"  # noqa: E501
            "5. For follow-up questions, explicitly reference previous context\n"  # noqa: E501
            "6. When appropriate, end with a subtle suggestion for what the user might want to know next\n"  # noqa: E501
            "7. Keep responses concise but complete - prioritize clarity over verbosity\n"  # noqa: E501
            "8. Use bullet points or numbered lists for multiple data points\n"
            "9. Format currency values with dollar signs and commas ($1,234.56)\n"  # noqa: E501
            "10. When discussing ratings, include their significance (e.g., '5.0 - Very Satisfied')\n"  # noqa: E501
        )
    except ImportError:
        # Fallback if business rules can't be imported
        return (
            "You are a helpful restaurant analytics assistant that translates database results "  # noqa: E501
            "into natural language answers. "
            "Your goal is to provide clear, actionable insights from restaurant order data.\n\n"  # noqa: E501
            "CONVERSATIONAL GUIDELINES:\n"
            "1. Use a friendly, professional tone that balances expertise with approachability\n"  # noqa: E501
            "2. Begin responses with a direct answer to the question, then provide supporting details\n"  # noqa: E501
            "3. Use natural transitions between ideas and maintain a conversational flow\n"  # noqa: E501
            "4. Highlight important metrics or insights with bold formatting (**like this**)\n"  # noqa: E501
            "5. For follow-up questions, explicitly reference previous context\n"  # noqa: E501
            "6. When appropriate, end with a subtle suggestion for what the user might want to know next\n"  # noqa: E501
            "7. Keep responses concise but complete - prioritize clarity over verbosity\n"  # noqa: E501
            "8. Use bullet points or numbered lists for multiple data points\n"
            "9. Format currency values with dollar signs and commas ($1,234.56)\n"  # noqa: E501
            "10. When discussing ratings, include their significance (e.g., '5.0 - Very Satisfied')\n"  # noqa: E501
        )


def is_followup_query(
    user_query: str, conversation_history: Optional[List[Dict]] = None
) -> bool:  # noqa: E501
    """Determine if a query is a follow-up to previous conversation with more sophisticated detection.  # noqa: E501

    Args:
        user_query (str): The current user query
        conversation_history (list, optional): Previous exchanges in the conversation  # noqa: E501

    Returns:
        bool: True if the query appears to be a follow-up, False otherwise
    """
    # Normalize the query
    query_lower = user_query.lower().strip()

    # 1. Check for explicit follow-up indicators
    explicit_indicators = [
        "those",
        "these",
        "that",
        "it",
        "they",
        "them",
        "their",
        "previous",
        "last",
        "again",
        "more",
        "further",
        "additional",
        "also",
        "too",
        "as well",
        "what about",
        "how about",
        "tell me more",
        "can you elaborate",
        "show me",
        "what else",
        "and",
        "what if",
    ]

    # Check if query starts with certain phrases
    starting_phrases = [
        "what about",
        "how about",
        "what if",
        "and what",
        "and how",
        "can you also",
        "could you also",
        "show me",
        "tell me more",
    ]

    # Check if query is very short (likely a follow-up)
    is_short_query = len(query_lower.split()) <= 3

    # 2. Check for pronouns without clear referents
    has_pronoun_without_referent = False
    pronouns = ["it", "they", "them", "those", "these", "that", "this"]
    for pronoun in pronouns:
        # Check if pronoun exists as a standalone word
        has_pronoun = f" {pronoun} " in f" {query_lower} "
        no_referent = not any(
            noun in query_lower
            for noun in ["order", "revenue", "sales", "item", "menu", "customer"]
        )
        if has_pronoun and no_referent:
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
        is_short_query
        and not any(
            x in query_lower for x in ["show", "list", "get", "find"]
        ),  # noqa: E501
    ]

    # 4. Context-based detection (if conversation history is available)
    context_based = False
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent query for comparison
        last_query = ""
        if "query" in conversation_history[-1]:
            last_query = conversation_history[-1].get("query", "").lower()

        # Check for shared key terms between queries
        last_query_terms = set(last_query.split())
        current_query_terms = set(query_lower.split())

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "by",
            "for",
            "with",
            "about",
            "from",
            "to",
            "of",
        }
        last_query_terms = last_query_terms - stop_words
        current_query_terms = current_query_terms - stop_words

        # If the current query has significantly fewer terms and shares some with the previous query  # noqa: E501
        if len(current_query_terms) < len(last_query_terms) * 0.7:
            common_terms = current_query_terms.intersection(last_query_terms)
            if len(common_terms) > 0:
                context_based = True
    # Combine all detection methods
    return (
        any(indicator in query_lower.split() for indicator in explicit_indicators)
        or any(query_lower.startswith(phrase) for phrase in starting_phrases)
        or has_pronoun_without_referent
        or any(incomplete_indicators)
        or context_based
    )
