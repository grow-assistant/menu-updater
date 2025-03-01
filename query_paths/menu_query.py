"""
Menu query path for the AI Menu Updater application.
Handles queries about menu items, such as "Show me all menu items" or
"What items are on our menu?".
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from query_paths.base import QueryPath
from utils.database import execute_sql_query

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class MenuQueryPath(QueryPath):
    """Handles queries about menu items."""

    _query_type = "query_menu"

    def generate_sql(self, query: str, **kwargs) -> str:
        """
        Generate SQL for a menu query.
        
        Args:
            query: Original user query
            **kwargs: Additional arguments including:
                - item_name: Optional specific item name to search for
            
        Returns:
            str: SQL query
        """
        # Get the item name if provided
        item_name = kwargs.get("item_name")
        
        # Get location IDs
        location_id = self.get_location_id()
        location_ids = self.get_location_ids()
        
        # Default SQL is to get all menu items for the default location
        if len(location_ids) > 1:
            locations_str = ", ".join(map(str, location_ids))
            sql = f"SELECT * FROM items WHERE location_id IN ({locations_str}) ORDER BY name"
        else:
            sql = f"SELECT * FROM items WHERE location_id = {location_id} ORDER BY name"
        
        # If we have a specific item name, filter for it
        if item_name:
            if len(location_ids) > 1:
                locations_str = ", ".join(map(str, location_ids))
                sql = f"SELECT * FROM items WHERE location_id IN ({locations_str}) AND name ILIKE '%{item_name}%' ORDER BY name"
            else:
                sql = f"SELECT * FROM items WHERE location_id = {location_id} AND name ILIKE '%{item_name}%' ORDER BY name"
        
        # Check if query is asking for disabled items specifically
        if "disabled" in query.lower() or "unavailable" in query.lower():
            if len(location_ids) > 1:
                locations_str = ", ".join(map(str, location_ids))
                sql = f"SELECT * FROM items WHERE location_id IN ({locations_str}) AND disabled = true ORDER BY name"
            else:
                sql = f"SELECT * FROM items WHERE location_id = {location_id} AND disabled = true ORDER BY name"
        
        # Check if query is asking for available items specifically
        elif "available" in query.lower() or "enabled" in query.lower():
            if len(location_ids) > 1:
                locations_str = ", ".join(map(str, location_ids))
                sql = f"SELECT * FROM items WHERE location_id IN ({locations_str}) AND disabled = false ORDER BY name"
            else:
                sql = f"SELECT * FROM items WHERE location_id = {location_id} AND disabled = false ORDER BY name"
        
        # If "count" or similar aggregation terms are in the query, adjust to COUNT(*)
        count_terms = ["how many", "count", "total number", "number of"]
        if any(term in query.lower() for term in count_terms):
            # Extract the WHERE clause from the existing SQL
            match = re.search(r'WHERE\s+(.*?)(?:ORDER BY|$)', sql, re.IGNORECASE)
            if match:
                where_clause = match.group(1).strip()
                sql = f"SELECT COUNT(*) as count FROM items WHERE {where_clause}"
            else:
                # Fallback if WHERE clause extraction fails
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT COUNT(*) as count FROM items WHERE location_id IN ({locations_str})"
                else:
                    sql = f"SELECT COUNT(*) as count FROM items WHERE location_id = {location_id}"
                    
        # Log the generated SQL
        logger.info(f"Generated SQL for menu query: {sql}")
        
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
                "summary": f"Error retrieving menu data: {results.get('error', 'Unknown error')}",
                "verbal_answer": f"Sorry, there was an error retrieving the menu data.",
                "text_answer": f"Error retrieving menu data: {results.get('error', 'Unknown error')}",
            }
            
        # Get result data
        result_data = results.get("results", [])
        
        # If this is a count query
        if result_data and "count" in result_data[0]:
            count = result_data[0]["count"]
            
            # Extract search context
            item_name = kwargs.get("item_name", "")
            search_context = f" matching '{item_name}'" if item_name else ""
            
            # Check if we're counting disabled or available items
            if "disabled" in query.lower() or "unavailable" in query.lower():
                item_type = "disabled"
            elif "available" in query.lower() or "enabled" in query.lower():
                item_type = "available"
            else:
                item_type = "menu"
            
            # Create verbal answer (optimized for speaking)
            verbal_answer = f"I found {count} {item_type} items{search_context} on the menu"
                
            # Create text answer (more detailed)
            text_answer = f"**Menu Item Count: {count}**\n\n"
            text_answer += f"Found {count} {item_type} items{search_context} on the menu."
            
            return {
                "summary": text_answer,
                "verbal_answer": verbal_answer,
                "text_answer": text_answer,
                "count": count,
            }
        
        # For list of menu items
        else:
            # Count of items
            item_count = len(result_data)
            
            # Get item name for context
            item_name = kwargs.get("item_name", "")
            
            # Check if we're listing disabled or available items
            if "disabled" in query.lower() or "unavailable" in query.lower():
                item_type = "disabled"
            elif "available" in query.lower() or "enabled" in query.lower():
                item_type = "available"
            else:
                item_type = "menu"
            
            # Add search context if applicable
            search_context = f" matching '{item_name}'" if item_name else ""
            
            # Create verbal answer (optimized for speaking)
            if item_count == 0:
                verbal_answer = f"I couldn't find any {item_type} items{search_context} on the menu"
            else:
                verbal_answer = f"I found {item_count} {item_type} items{search_context} on the menu"
                
            # Create text answer (more detailed)
            if item_count == 0:
                text_answer = f"No {item_type} items{search_context} found on the menu."
            else:
                text_answer = f"**Menu Items:**\n\n"
                text_answer += f"Found {item_count} {item_type} items{search_context}.\n\n"
                
                # Add table of menu items
                text_answer += "| Item | Price | Status |\n"
                text_answer += "|:-----|:------|:-------|\n"
                
                # Add menu items to the table
                for item in result_data:
                    name = item.get("name", "N/A")
                    price = f"${item.get('price', 0):.2f}"
                    status = "Disabled" if item.get("disabled", False) else "Available"
                    
                    text_answer += f"| {name} | {price} | {status} |\n"
            
            return {
                "summary": text_answer,
                "verbal_answer": verbal_answer,
                "text_answer": text_answer,
                "count": item_count,
                "items": result_data,
            } 