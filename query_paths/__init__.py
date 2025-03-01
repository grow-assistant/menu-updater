"""
Query paths package for the AI Menu Updater application.
Contains classes and functions for different query paths (order history, menu updates, etc.).
"""

from query_paths.base import QueryPath
from query_paths.order_history import OrderHistoryPath
from query_paths.menu_query import MenuQueryPath
from query_paths.menu_update import MenuUpdatePath
from query_paths.menu_status import MenuStatusPath

# Map of query types to query path classes
QUERY_PATHS = {
    "order_history": OrderHistoryPath,
    "query_menu": MenuQueryPath,
    "update_price": MenuUpdatePath,
    "disable_item": MenuStatusPath,
    "enable_item": MenuStatusPath,
}

def get_query_path(query_type: str):
    """
    Get the appropriate query path class for a given query type.
    
    Args:
        query_type: Type of query (order_history, query_menu, update_price, etc.)
        
    Returns:
        QueryPath: The appropriate query path class, or None if not found
    """
    return QUERY_PATHS.get(query_type) 