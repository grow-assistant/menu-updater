"""
Tool factory for the AI Menu Updater application.
Creates all the necessary tools for the LangChain agent.
"""

import logging
import json
from typing import List, Dict, Any, Callable

# LangChain imports - make backward compatible
try:
    # Try newer LangChain versions
    from langchain_core.tools import BaseTool as Tool
except ImportError:
    # Fallback to older LangChain
    from langchain.tools import Tool

from tools.sql_database import create_sql_database_tool
from tools.menu_tools import create_menu_update_tool
from utils.database import execute_sql_query

# Configure logger
logger = logging.getLogger("ai_menu_updater")

def create_tools_for_agent(location_id: int = 62) -> List[Tool]:
    """
    Create tools for the LangChain agent based on the existing functionality.
    
    Args:
        location_id: Location ID to use for queries (default: 62)
    
    Returns:
        List[Tool]: List of LangChain tools
    """
    logger.info(f"Creating tools for agent with location_id: {location_id}")
    
    # SQL database tool
    def _execute_query_wrapper(query: str) -> Dict[str, Any]:
        """Execute SQL query with the location ID"""
        return execute_sql_query(query, location_id)
    
    sql_tool = create_sql_database_tool(execute_query_func=_execute_query_wrapper)

    # Menu update tool
    def _execute_menu_update(update_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute menu update with proper SQL generation"""
        item_name = update_spec.get("item_name")
        new_price = update_spec.get("new_price")
        disabled = update_spec.get("disabled")

        if not item_name:
            return {
                "success": False,
                "error": "Missing item_name in update specification",
            }

        if new_price is not None:
            # Update price query
            query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        elif disabled is not None:
            # Enable/disable query
            disabled_value = str(disabled).lower()
            query = f"UPDATE items SET disabled = {disabled_value} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        else:
            return {
                "success": False,
                "error": "Invalid update specification - must include either new_price or disabled",
            }

        return execute_sql_query(query, location_id)

    menu_tool = create_menu_update_tool(execute_update_func=_execute_menu_update)

    # Return all tools
    return [sql_tool, menu_tool] 