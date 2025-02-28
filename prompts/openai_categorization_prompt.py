import datetime
import logging
import os
import glob
from typing import Dict, Optional, Any, Union
from . import load_example_queries  # Import the function from prompts package

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

    # Load examples directly from database folders
    examples_by_category = ""
    # Get raw examples from all categories
    example_data = load_example_queries()
    
    # Parse the example data into categories
    raw_examples = example_data.split("\n")
    current_category = None
    category_examples = {
        "order_history": [],
        "update_price": [],
        "disable_item": [],
        "enable_item": [],
        "query_menu": [],
        "query_performance": [],
        "query_ratings": [],
        "delete_options": []
    }
    
    # Process the raw examples to extract descriptions by category
    for line in raw_examples:
        if line.endswith("EXAMPLES:"):
            # Convert "ORDER_HISTORY EXAMPLES:" to "order_history"
            current_category = line.replace(" EXAMPLES:", "").strip().lower()
            continue
            
        if current_category in category_examples and ". " in line and ":" in line:
            # This looks like a description line
            description = line.split(":", 1)[0].split(". ", 1)[1].strip()
            if description:
                category_examples[current_category].append(f'"{description}"')
    
    # Format examples for the prompt
    category_num = 1
    for category, examples_list in category_examples.items():
        if examples_list:
            formatted_examples = "\n   - " + "\n   - ".join(examples_list[:3])  # Limit to 3 examples
            examples_by_category += f"\n{category_num}. {category}:{formatted_examples}\n"
            category_num += 1
    
    # If no examples were found, use some defaults
    if not examples_by_category:
        examples_by_category = (
"""
1. order_history:
   - "How many orders on 2023-10-15?"
   - "Show revenue from March 5th"
   - "What were yesterday's cancellations?"

2. update_price:
   - "Update the price of French Fries to $4.99"
   - "Change Burger price to $8.50"

3. disable_item:
   - "Disable the Chocolate Cake menu item"
   - "Remove Veggie Burger from the menu"

4. enable_item:
   - "Make the Veggie Burger available again"
   - "Add Apple Pie back to the menu"

5. query_menu:
   - "Show all active dessert items"
   - "What vegetarian options do we have?"

6. query_performance:
   - "What is our average order value this month?"
   - "How do weekday sales compare to weekend sales?"

7. query_ratings:
   - "Show orders with low customer ratings"
   - "What menu items get the most complaints?"
"""
        )

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

EXAMPLES BY CATEGORY:{examples_by_category}

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

def create_query_categorization_prompt(user_query, conversation_history=None):
    """Create a prompt for categorizing the user's query type.
    
    Args:
        user_query (str): The user's query to categorize
        conversation_history (list, optional): Previous conversation history. Defaults to None.
        
    Returns:
        str: The prompt for query categorization
    """
    # Load examples of each category
    examples = load_example_queries()
    
    # Include conversation history context if available
    previous_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent conversation
        last_exchange = conversation_history[-1]
        previous_context = f"""
PREVIOUS QUERY CONTEXT:
Previous Question: "{last_exchange.get('query', '')}"
Previous SQL: "{last_exchange.get('sql', '')}"
"""
    
    prompt = f"""You are an expert SQL query categorizer for a restaurant management system. Your task is to classify the user's query into one of the predefined categories.

USER QUERY: {user_query.strip()}

{previous_context}

CATEGORY DESCRIPTIONS:
1. order_history - Queries about past orders, order details, order lookup, customer orders
2. update_price - Queries about changing, updating, or modifying menu item prices
3. disable_item - Queries about turning off, disabling, or removing menu items from availability
4. enable_item - Queries about turning on, enabling, or making menu items available again
5. query_menu - Queries about menu structure, categories, items, or general menu information
6. query_performance - Queries about sales performance, revenue, trends, or business metrics
7. query_ratings - Queries about customer ratings, feedback, or review information
8. delete_options - Queries about removing customization options, toppings, or modifiers
9. other - Queries that don't fit into any of the above categories

EXAMPLE QUERIES FROM EACH CATEGORY:
{examples}

INSTRUCTIONS:
1. Analyze the user query carefully
2. Compare it to the example queries and category descriptions
3. Identify the most appropriate category based on the intent
4. If the query could fit multiple categories, prioritize based on the main action requested
5. Respond ONLY with the category name (lowercase, no explanation)

Your response must be EXACTLY one of these words: order_history, update_price, disable_item, enable_item, query_menu, query_performance, query_ratings, delete_options, other
"""
    
    # Log the generated prompt
    logger.info(f"Generated categorization prompt: {prompt[:200]}..." if len(prompt) > 200 else prompt)
    
    return prompt
