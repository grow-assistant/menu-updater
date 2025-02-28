import json


def create_summary_prompt(user_query, sql_query, result, query_type=None):
    """Generate an optimized prompt for OpenAI summarization

    Args:
        user_query (str): The original user query
        sql_query (str): The executed SQL query
        result (dict): The database result dictionary
        query_type (str, optional): The type of query (order_history, query_menu, etc.)

    Returns:
        str: The optimized prompt for summarization
    """
    # Format SQL query for better readability - clean up whitespace and formatting
    formatted_sql = sql_query.strip().replace("\n", " ").replace("  ", " ")

    # Extract query type from result if not provided
    if not query_type and "function_call" in result:
        query_type = result.get("function_call", {}).get("name", "unknown")

    # Add query-specific context based on query type
    type_specific_instructions = {
        "order_history": "Present order counts, revenue figures, and trends with proper formatting. Use dollar signs for monetary values and include percent changes for trends. Be careful to distinguish between 'placed' and 'completed' orders based on the user's exact wording.",
        "query_performance": "Highlight key performance metrics for ALL results in the dataset. If there are multiple customers or items, list the top entries (at least 3 if available). Always include all relevant data from the results.",
        "query_menu": "Structure menu information clearly, listing items with their prices and availability status in an organized way.",
        "query_ratings": "Present ALL items in the results with their counts or metrics. If the query is about most ordered items, list at least the top 5 items with their order counts.",
        "update_price": "Confirm the exact price change with both old and new values clearly stated.",
        "disable_item": "Confirm the item has been disabled and explain the impact (no longer available to customers).",
        "enable_item": "Confirm the item has been re-enabled and is now available to customers again.",
    }

    type_guidance = type_specific_instructions.get(
        query_type, "Provide a clear, direct answer to the user's question."
    )

    # Determine if we have empty results to provide better context
    results_count = len(result.get("results", []))
    result_context = ""
    if results_count == 0:
        result_context = "The query returned no results, which typically means no data matches the specified criteria for the given time period or filters."

    # Build optimized prompt with essential context and guidance
    return (
        f"USER QUERY: '{user_query}'\n\n"
        f"SQL QUERY: {formatted_sql}\n\n"
        f"DATABASE RESULTS: {json.dumps(result.get('results', []), indent=2)}\n\n"
        f"{result_context}\n\n"
        f"BUSINESS CONTEXT:\n"
        f"- Revenue in USD, ratings on scale 1-5\n\n"
        f"GUIDANCE: {type_guidance}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Answer directly with all relevant metrics ($ for money, % for percentages)\n"
        f"2. Use conversational language, be concise yet informative\n"
        f"3. Include ALL relevant results - don't summarize only the first result\n"
        f"4. If no results found, explain the business implications\n"
    )
