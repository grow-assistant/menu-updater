import datetime
import logging
from typing import Dict, Optional, Any, Union

# Get the logger that was configured in utils/langchain_integration.py
logger = logging.getLogger("ai_menu_updater")


def create_categorization_prompt(cached_dates=None) -> Dict[str, Any]:
    """Create an optimized categorization prompt for OpenAI

    Args:
        cached_dates: Optional previously cached date context

    Returns:
        Dict containing the prompt string and context information
    """
    # Log input parameters
    logger.info(f"Categorization prompt inputs: cached_dates={cached_dates}")
    
    yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Change arrows to text equivalents
    example_followups = f"""
    - Initial: "Orders on 2025-02-21" -> start_date=2025-02-21
    - Followup: "Total for those" -> use previous dates
    - New query: "Compare to last week" -> calculate new dates
    """

    prompt = f"""You are an expert query categorization system for a restaurant management application. 
Analyze user queries and classify them into the correct category from the following options.

Return a valid JSON object with the following fields:
- "request_type": (REQUIRED) One of: "order_history", "update_price", "disable_item", "enable_item", "query_menu", "query_performance", "query_ratings"
- "time_period": (Optional) The specific timeframe for order_history queries
- "analysis_type": (Optional) What's being analyzed for order_history queries
- "start_date": (Optional) Start date filter in YYYY-MM-DD format
- "end_date": (Optional) End date filter in YYYY-MM-DD format
- "item_name": (Optional) Menu item name for update/disable/enable requests
- "new_price": (Optional) New price value for update_price requests

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
- date_filter: EXACT date specified in format 'YYYY-MM-DD' (extract even if implied)

EXAMPLES BY CATEGORY:
1. order_history:
   - "How many orders on 2023-10-15?" → request_type="order_history", start_date="2023-10-15", end_date="2023-10-15"
   - "Show revenue from March 5th" → request_type="order_history", start_date="2024-03-05", end_date="2024-03-05", analysis_type="revenue"
   - "What were yesterday's cancellations?" → request_type="order_history", start_date="{yesterday_date}", end_date="{yesterday_date}"
   - "How many orders were completed yesterday?" → request_type="order_history", time_period="yesterday", analysis_type="count"
   - "Show revenue from last week" → request_type="order_history", time_period="last_week", analysis_type="revenue"
   - "What were our busiest days this month?" → request_type="order_history", time_period="this_month", analysis_type="trend"
   - "What was the most number of orders last year?" → request_type="order_history", time_period="last_year", analysis_type="trend"
   - "How many orders were placed in the last year?" → request_type="order_history", time_period="last_year", analysis_type="count"
   - "What was the highest revenue day last year?" → request_type="order_history", time_period="last_year", analysis_type="trend"
   - "How have sales changed in the last year?" → request_type="order_history", time_period="last_year", analysis_type="trend"

2. update_price:
   - "Update the price of French Fries to $4.99" → request_type="update_price", item_name="French Fries", new_price=4.99
   - "Change Burger price to $8.50" → request_type="update_price", item_name="Burger", new_price=8.50

3. disable_item:
   - "Disable the Chocolate Cake menu item" → request_type="disable_item", item_name="Chocolate Cake"
   - "Remove Veggie Burger from the menu" → request_type="disable_item", item_name="Veggie Burger"

4. enable_item:
   - "Make the Veggie Burger available again" → request_type="enable_item", item_name="Veggie Burger"
   - "Add Apple Pie back to the menu" → request_type="enable_item", item_name="Apple Pie"

5. query_menu:
   - "Show all active dessert items" → request_type="query_menu"
   - "What vegetarian options do we have?" → request_type="query_menu"
   - "How much does the Caesar Salad cost?" → request_type="query_menu", item_name="Caesar Salad"

6. query_performance:
   - "What's our average order value this month?" → request_type="query_performance", time_period="this_month"
   - "How do weekday sales compare to weekend sales?" → request_type="query_performance", analysis_type="comparison"
   - "Which time of day has the highest sales?" → request_type="query_performance", analysis_type="trend"

7. query_ratings:
   - "Show orders with low customer ratings" → request_type="query_ratings"
   - "What menu items get the most complaints?" → request_type="query_ratings", analysis_type="complaints"
   - "What's our average customer satisfaction score?" → request_type="query_ratings", analysis_type="average"

IMPORTANT TIME PERIOD GUIDANCE:
- "last year" refers to the calendar year 2024 (not a 365-day rolling window)
- "in the last year" refers to the previous 365 days (a rolling window)
- Both are categorized as time_period="last_year", but will be handled differently by the SQL generator

NEW DATE HANDLING RULES:
1. CURRENT_DATE: {current_date}
2. PREVIOUS DATE CONTEXT: {cached_dates or 'No previous dates available'}
3. If no dates specified, use previous context when available
4. Explicit dates always override previous context

EXAMPLE FOLLOWUPS:
{example_followups}

CATEGORIZATION APPROACH:
1. First, check for explicit date mentions
2. If found, extract and store as date_filter
3. If no date but previous exists, add date_filter=previous
4. If no date and no previous, use CURRENT_DATE
5. First, identify the core intent (retrieving information vs. making changes)
6. For information requests, determine if they're about orders, menu items, performance, or ratings
7. For change requests, determine if they're updating prices, enabling, or disabling items
8. Look for time-related terms to identify time periods for order_history queries
9. Pay attention to verbs like "update", "change", "disable", "remove", "show", "get" as intent indicators

Make the most accurate determination based on the query's intent and content.
Respond with a JSON object containing the categorized request information."""

    # Log the generated prompt
    logger.info(f"Generated categorization prompt: {prompt[:200]}..." if len(prompt) > 200 else prompt)
    
    # Return a structured dictionary instead of just a string
    result = {
        "prompt": prompt,
        "context": {
            "current_date": current_date,
            "yesterday_date": yesterday_date,
            "cached_dates": cached_dates,
            "date_context": cached_dates,  # Include date_context for compatibility
        },
    }
    
    return result
