"""
Menu update path for the AI Menu Updater application.
Handles menu price updates, such as "Update the price of French Fries to $5.99".
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from query_paths.base import QueryPath
from utils.database import execute_sql_query

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class MenuUpdatePath(QueryPath):
    """Handles menu price update queries."""

    _query_type = "update_price"

    def generate_sql(self, query: str, **kwargs) -> str:
        """
        Generate SQL for updating a menu item price.
        
        Args:
            query: Original user query
            **kwargs: Additional arguments including:
                - item_name: Name of the item to update
                - new_price: New price for the item
            
        Returns:
            str: SQL query
        """
        # Get required parameters
        item_name = kwargs.get("item_name")
        new_price = kwargs.get("new_price")
        
        # Validate required parameters
        if not item_name:
            logger.error("Missing item_name in menu update query")
            raise ValueError("Item name is required for menu price updates")
        
        if not new_price:
            logger.error("Missing new_price in menu update query")
            raise ValueError("New price is required for menu price updates")
        
        # Try to convert price to float if it's a string
        if isinstance(new_price, str):
            new_price = float(new_price.replace('$', '').strip())
        
        # Get location IDs
        location_id = self.get_location_id()
        location_ids = self.get_location_ids()
        
        # Generate SQL to update the item price
        if len(location_ids) > 1:
            locations_str = ", ".join(map(str, location_ids))
            sql = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
        else:
            sql = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        
        # Log the generated SQL
        logger.info(f"Generated SQL for menu price update: {sql}")
        
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
                "summary": f"Error updating menu item: {results.get('error', 'Unknown error')}",
                "verbal_answer": f"Sorry, there was an error updating the menu item price.",
                "text_answer": f"Error updating menu item: {results.get('error', 'Unknown error')}",
            }
            
        # Get result data
        result_data = results.get("results", [])
        
        # Get required parameters
        item_name = kwargs.get("item_name", "unknown item")
        new_price = kwargs.get("new_price")
        
        # Try to convert price to float if it's a string
        if isinstance(new_price, str):
            try:
                new_price = float(new_price.replace('$', '').strip())
            except ValueError:
                new_price = 0.0
        
        # Format the price for display
        formatted_price = f"${new_price:.2f}"
        
        # Count of updated items
        updated_count = len(result_data)
        
        # Create verbal answer (optimized for speaking)
        if updated_count == 0:
            verbal_answer = f"I couldn't find any menu items matching '{item_name}' to update."
        elif updated_count == 1:
            item = result_data[0]
            actual_name = item.get("name", item_name)
            verbal_answer = f"I've updated the price of {actual_name} to {formatted_price}."
        else:
            verbal_answer = f"I've updated the price of {updated_count} items matching '{item_name}' to {formatted_price}."
                
        # Create text answer (more detailed)
        if updated_count == 0:
            text_answer = f"❌ **Price Update Failed**\n\nNo menu items found matching '{item_name}'."
        else:
            text_answer = f"✅ **Price Update Successful**\n\n"
            
            if updated_count == 1:
                item = result_data[0]
                actual_name = item.get("name", item_name)
                text_answer += f"Updated the price of '{actual_name}' to {formatted_price}.\n\n"
            else:
                text_answer += f"Updated the price of {updated_count} items matching '{item_name}' to {formatted_price}.\n\n"
            
            # Add table of updated items
            text_answer += "| Item | New Price | Location ID |\n"
            text_answer += "|:-----|:----------|:------------|\n"
            
            # Add items to the table
            for item in result_data:
                name = item.get("name", "N/A")
                price = f"${item.get('price', 0):.2f}"
                location = item.get("location_id", "N/A")
                
                text_answer += f"| {name} | {price} | {location} |\n"
        
        return {
            "summary": text_answer,
            "verbal_answer": verbal_answer,
            "text_answer": text_answer,
            "count": updated_count,
            "items": result_data,
        } 