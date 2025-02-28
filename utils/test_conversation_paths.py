"""
This file contains 10 different conversation paths for testing the simulated_chat_dynamic.py script.
Each path has questions in sequence, sometimes building on previous questions and sometimes changing topics.
"""

# Dictionary of conversation paths
# Each path has an initial query and follow-up questions
conversation_paths = {
    "path1": {
        "description": "Orders on a specific date and details",
        "initial_query": "How many orders were completed on 2/21/2025?",
        "followup_queries": [
            "How much were those orders totals?",
            "What was the average order rating for all of those orders?",
            "Give me the order details for all of the orders?",
        ],
    },
    "path2": {
        "description": "Revenue analysis with time comparison",
        "initial_query": "What was our total revenue last week?",
        "followup_queries": [
            "How does that compare to the previous week?",
            "Which day had the highest sales?",
            "What were the top 5 selling menu items by revenue?",
        ],
    },
    "path3": {
        "description": "Customer-focused inquiries",
        "initial_query": "Who are our top 10 customers by order frequency?",
        "followup_queries": [
            "How many new customers did we have in the last 30 days?",
            "How many of the orders in the past week were from repeat customers?",
            "How many of the orders in the past week were from new customers?",
        ],
    },
    "path4": {
        "description": "Mixed topics with abrupt changes",
        "initial_query": "How many vegetarian items do we have on the menu?",
        "followup_queries": [
            "What are the top selling items by revenue in the past 30 days?",
            "Which ones are the most popular by order count?",
            "What was our total revenue yesterday?",
        ],
    },
    "path5": {
        "description": "Customer Review Analysis",
        "initial_query": "What's our average order time for the past 30 days?",
        "followup_queries": [
            "What orders were placed in the last month that did not have a 5 star rating?",
            "Give me the details of those orders",
            "What was the average rating for the orders that did not have a 5 star rating?",
        ],
    },
    "path6": {
        "description": "Monthly sales comparison",
        "initial_query": "What is our total revenue for this month so far?",
        "followup_queries": [
            "How does that compare to the same month last year?",
            "What were our top 5 best selling menu items this month?",
            "What is our average order value this month?",
        ],
    },
    "path7": {
        "description": "Customer ordering patterns",
        "initial_query": "What are our peak ordering hours?",
        "followup_queries": [
            "Which day of the week has the highest order volume?",
            "What's the average time between a customer's first and second order?",
            "What's the lifetime value of our average customer?",
        ],
    },
    "path8": {
        "description": "Order fulfillment analysis",
        "initial_query": "What's our average order fulfillment time in minutes for the past 30 days?",
        "followup_queries": [
            "How does that compare to delivery orders specifically?",
            "How many orders were canceled or refunded in the past month?",
            "What's the most common reason for cancellation?",
        ],
    },
    "path9": {
        "description": "Menu category performance",
        "initial_query": "Which menu categories have the highest sales?",
        "followup_queries": [
            "What specific items in those categories sell the most?",
            "What's the average order value for each category?",
            "Have any categories seen significant changes in sales over the past month?",
        ],
    },
    "path10": {
        "description": "Customer acquisition and retention",
        "initial_query": "How many new customers did we acquire in the last week?",
        "followup_queries": [
            "What percentage of our orders come from repeat customers?",
            "What's the average number of orders per customer?",
            "Which menu items are most popular with new customers versus repeat customers?",
        ],
    },
}


def get_conversation_path(path_name):
    """
    Get a specific conversation path by name.

    Args:
        path_name (str): The name of the path to retrieve (e.g., "path1", "path2")

    Returns:
        dict: Dictionary containing the initial query and follow-up queries
    """
    return conversation_paths.get(path_name, conversation_paths["path1"])


def list_available_paths():
    """
    List all available conversation paths with their descriptions.

    Returns:
        dict: Dictionary with path names as keys and descriptions as values
    """
    return {path: data["description"] for path, data in conversation_paths.items()}


# Sample function for integrating with simulated_chat_dynamic.py
def get_path_for_testing(path_name="path1"):
    """
    Get a path formatted for direct use in simulated_chat_dynamic.py.

    Args:
        path_name (str): The name of the path to retrieve

    Returns:
        tuple: (initial_query, followup_queries_list)
    """
    path = get_conversation_path(path_name)
    return path["initial_query"], path["followup_queries"]
