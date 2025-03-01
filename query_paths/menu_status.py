"""
Menu status path for the AI Menu Updater application.
Handles enabling and disabling menu items, such as "Disable the French Fries" or
"Enable the Club Sandwich".
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from query_paths.base import QueryPath
from utils.database import execute_sql_query

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class MenuStatusPath(QueryPath):
    """Handles menu item status changes (enable/disable)."""

    _query_type = "menu_status"  # Generic type, will be overridden
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the menu status path.
        
        Args:
            context: Optional context dictionary with session state information
        """
        super().__init__(context)
        # The actual query type will be set based on the operation (enable/disable)
    
    def generate_sql(self, query: str, **kwargs) -> str:
        """
        Generate SQL for enabling or disabling a menu item.
        
        Args:
            query: Original user query
            **kwargs: Additional arguments including:
                - item_name: Name of the item to update
                - query_type: Type of query (enable_item or disable_item)
            
        Returns:
            str: SQL query
        """
        # Get required parameters
        item_name = kwargs.get("item_name")
        query_type = kwargs.get("query_type")
        
        # Set the query type for this instance
        self._query_type = query_type or "menu_status"
        
        # Validate required parameters
        if not item_name:
            logger.error("Missing item_name in menu status query")
            raise ValueError("Item name is required for menu status updates")
        
        # Determine if we're enabling or disabling based on query type
        if query_type == "disable_item":
            disabled = True
        elif query_type == "enable_item":
            disabled = False
        else:
            # Try to determine from the query text
            if "disable" in query.lower() or "deactivate" in query.lower() or "unavailable" in query.lower():
                disabled = True
                self._query_type = "disable_item"
            elif "enable" in query.lower() or "activate" in query.lower() or "available" in query.lower():
                disabled = False
                self._query_type = "enable_item"
            else:
                # Default to disabling if unclear
                logger.warning(f"Unclear menu status operation in query: {query}")
                disabled = True
                self._query_type = "disable_item"
        
        # Get location IDs
        location_id = self.get_location_id()
        location_ids = self.get_location_ids()
        
        # Generate SQL to update the item status
        if len(location_ids) > 1:
            locations_str = ", ".join(map(str, location_ids))
            sql = f"UPDATE items SET disabled = {str(disabled).lower()} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
        else:
            sql = f"UPDATE items SET disabled = {str(disabled).lower()} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        
        # Log the generated SQL
        logger.info(f"Generated SQL for menu status update ({self._query_type}): {sql}")
        
        return sql

    def process_results(self, results: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """
        Process the query results.
        
        Args:
            results: Database query results
            query: Original user query
            **kwargs: Additional parameters
            
        Returns:
            dict: Processed results with summary and formatted information
        """
        # Check if the results contain data
        if not results.get("success", False):
            return {
                "summary": f"Error updating menu item status: {results.get('error', 'Unknown error')}",
                "verbal_answer": f"Sorry, there was an error updating the menu item status.",
                "text_answer": f"Error updating menu item status: {results.get('error', 'Unknown error')}",
            }
            
        # Get result data
        result_data = results.get("results", [])
        
        # Get required parameters
        item_name = kwargs.get("item_name", "unknown item")
        query_type = kwargs.get("query_type", self._query_type)
        
        # Determine operation type
        operation = "disabled" if query_type == "disable_item" else "enabled"
        
        # Count of updated items
        updated_count = len(result_data)
        
        # Create verbal answer (optimized for speaking)
        if updated_count == 0:
            verbal_answer = f"I couldn't find any menu items matching '{item_name}' to {operation}."
        elif updated_count == 1:
            item = result_data[0]
            actual_name = item.get("name", item_name)
            verbal_answer = f"I've {operation} {actual_name} on the menu."
        else:
            verbal_answer = f"I've {operation} {updated_count} items matching '{item_name}' on the menu."
                
        # Create text answer (more detailed)
        if updated_count == 0:
            text_answer = f"❌ **Status Update Failed**\n\nNo menu items found matching '{item_name}'."
        else:
            status_emoji = "🚫" if operation == "disabled" else "✅"
            text_answer = f"{status_emoji} **Status Update Successful**\n\n"
            
            if updated_count == 1:
                item = result_data[0]
                actual_name = item.get("name", item_name)
                text_answer += f"{actual_name} has been {operation} on the menu.\n\n"
            else:
                text_answer += f"{updated_count} items matching '{item_name}' have been {operation} on the menu.\n\n"
            
            # Add table of updated items
            text_answer += "| Item | Status | Location ID |\n"
            text_answer += "|:-----|:-------|:------------|\n"
            
            # Add items to the table
            for item in result_data:
                name = item.get("name", "N/A")
                status = "Disabled" if item.get("disabled", False) else "Enabled"
                location = item.get("location_id", "N/A")
                
                text_answer += f"| {name} | {status} | {location} |\n"
            
            # Add note about what this means
            if operation == "disabled":
                text_answer += "\n**Note:** Disabled items will not appear to customers and cannot be ordered."
            else:
                text_answer += "\n**Note:** Enabled items are now available to customers and can be ordered."
        
        return {
            "summary": text_answer,
            "verbal_answer": verbal_answer,
            "text_answer": text_answer,
            "count": updated_count,
            "items": result_data,
            "operation": operation,
        } 