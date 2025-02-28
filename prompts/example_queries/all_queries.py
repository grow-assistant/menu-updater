"""
This module imports and provides access to all category-specific query examples.
"""

from prompts.example_queries.order_history import ORDER_HISTORY_QUERIES
from prompts.example_queries.update_price import UPDATE_PRICE_QUERIES
from prompts.example_queries.disable_item import DISABLE_ITEM_QUERIES
from prompts.example_queries.enable_item import ENABLE_ITEM_QUERIES
from prompts.example_queries.query_menu import QUERY_MENU_QUERIES
from prompts.example_queries.query_performance import QUERY_PERFORMANCE_QUERIES
from prompts.example_queries.query_ratings import QUERY_RATINGS_QUERIES

# Dictionary mapping category types to their respective queries
CATEGORY_QUERIES = {
    "order_history": ORDER_HISTORY_QUERIES,
    "update_price": UPDATE_PRICE_QUERIES,
    "disable_item": DISABLE_ITEM_QUERIES,
    "enable_item": ENABLE_ITEM_QUERIES,
    "query_menu": QUERY_MENU_QUERIES, 
    "query_performance": QUERY_PERFORMANCE_QUERIES,
    "query_ratings": QUERY_RATINGS_QUERIES
}

def get_queries_by_category(category_type):
    """
    Returns the example queries for a specific category type.
    
    Args:
        category_type (str): One of the category types
        
    Returns:
        str: The example queries for the specified category type
    """
    return CATEGORY_QUERIES.get(category_type, "No queries found for this category type.")

def get_all_queries():
    """
    Returns a dictionary of all example queries organized by category type.
    
    Returns:
        dict: Dictionary with category types as keys and query strings as values
    """
    return CATEGORY_QUERIES 