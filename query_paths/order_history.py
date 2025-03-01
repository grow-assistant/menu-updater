"""
Order history query path for the AI Menu Updater application.
Handles queries about order history, such as "Show me orders from today" or
"How many orders did we have yesterday?".
"""

import datetime
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from query_paths.base import QueryPath
from utils.database import execute_sql_query

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class OrderHistoryPath(QueryPath):
    """Handles queries about order history."""

    _query_type = "order_history"

    def generate_sql(self, query: str, **kwargs) -> str:
        """
        Generate SQL for an order history query.
        
        Args:
            query: Original user query
            **kwargs: Additional arguments including:
                - time_period: Optional time period mentioned in the query
                - start_date: Optional start date for filtering
                - end_date: Optional end date for filtering
            
        Returns:
            str: SQL query
        """
        time_period = kwargs.get("time_period")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        
        # Get location IDs
        location_id = self.get_location_id()
        location_ids = self.get_location_ids()
        
        # Default SQL is to get all completed orders for the default location
        sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} LIMIT 50"
        
        # If we have multiple locations, use IN clause
        if len(location_ids) > 1:
            locations_str = ", ".join(map(str, location_ids))
            sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) LIMIT 50"
        
        # If we have explicit date range
        if start_date and end_date:
            if len(location_ids) > 1:
                locations_str = ", ".join(map(str, location_ids))
                sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date BETWEEN '{start_date}' AND '{end_date}' LIMIT 50"
            else:
                sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date BETWEEN '{start_date}' AND '{end_date}' LIMIT 50"
        
        # If we have a time period keyword
        elif time_period:
            if time_period == "today":
                # Today's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date = CURRENT_DATE LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date = CURRENT_DATE LIMIT 50"
            
            elif time_period == "yesterday":
                # Yesterday's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date = CURRENT_DATE - INTERVAL '1 day' LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date = CURRENT_DATE - INTERVAL '1 day' LIMIT 50"
            
            elif time_period == "this_week":
                # This week's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date >= date_trunc('week', CURRENT_DATE) LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date >= date_trunc('week', CURRENT_DATE) LIMIT 50"
            
            elif time_period == "last_week":
                # Last week's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date >= date_trunc('week', CURRENT_DATE - INTERVAL '1 week') AND updated_at::date < date_trunc('week', CURRENT_DATE) LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date >= date_trunc('week', CURRENT_DATE - INTERVAL '1 week') AND updated_at::date < date_trunc('week', CURRENT_DATE) LIMIT 50"
            
            elif time_period == "this_month":
                # This month's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date >= date_trunc('month', CURRENT_DATE) LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date >= date_trunc('month', CURRENT_DATE) LIMIT 50"
            
            elif time_period == "last_month":
                # Last month's orders
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id IN ({locations_str}) AND updated_at::date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND updated_at::date < date_trunc('month', CURRENT_DATE) LIMIT 50"
                else:
                    sql = f"SELECT * FROM orders WHERE status = 7 AND location_id = {location_id} AND updated_at::date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND updated_at::date < date_trunc('month', CURRENT_DATE) LIMIT 50"

        # If "count" or similar aggregation terms are in the query, adjust to COUNT(*)
        count_terms = ["how many", "count", "total number", "number of"]
        if any(term in query.lower() for term in count_terms):
            # Extract the WHERE clause from the existing SQL
            match = re.search(r'WHERE\s+(.*?)(?:LIMIT|$)', sql, re.IGNORECASE)
            if match:
                where_clause = match.group(1).strip()
                sql = f"SELECT COUNT(*) as count FROM orders WHERE {where_clause}"
            else:
                # Fallback if WHERE clause extraction fails
                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql = f"SELECT COUNT(*) as count FROM orders WHERE status = 7 AND location_id IN ({locations_str})"
                else:
                    sql = f"SELECT COUNT(*) as count FROM orders WHERE status = 7 AND location_id = {location_id}"
                    
        # Log the generated SQL
        logger.info(f"Generated SQL for order history: {sql}")
        
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
                "summary": f"Error retrieving order data: {results.get('error', 'Unknown error')}",
                "verbal_answer": f"Sorry, there was an error retrieving the order data.",
                "text_answer": f"Error retrieving order data: {results.get('error', 'Unknown error')}",
            }
            
        # Get result data
        result_data = results.get("results", [])
        
        # If this is a count query
        if result_data and "count" in result_data[0]:
            count = result_data[0]["count"]
            
            # Format time period for the summary - safely handle None values
            time_period = kwargs.get("time_period") or ""
            if time_period:
                time_period = time_period.replace("_", " ")
                
            date_range = ""
            if kwargs.get("start_date") and kwargs.get("end_date"):
                date_range = f"between {kwargs['start_date']} and {kwargs['end_date']}"
            elif time_period:
                date_range = time_period
                
            # Create verbal answer (optimized for speaking)
            verbal_answer = f"I found {count} completed orders"
            if date_range:
                verbal_answer += f" for {date_range}"
                
            # Create text answer (more detailed)
            text_answer = f"**Order Count: {count}**\n\n"
            if date_range:
                text_answer += f"Time period: {date_range}\n\n"
            text_answer += "This represents all completed orders with status code 7."
            
            return {
                "summary": text_answer,
                "verbal_answer": verbal_answer,
                "text_answer": text_answer,
                "count": count,
            }
        
        # For list of orders
        else:
            # Format time period for the summary - safely handle None values
            time_period = kwargs.get("time_period") or ""
            if time_period:
                time_period = time_period.replace("_", " ")
                
            date_range = ""
            if kwargs.get("start_date") and kwargs.get("end_date"):
                date_range = f"between {kwargs['start_date']} and {kwargs['end_date']}"
            elif time_period:
                date_range = time_period
                
            # Count of orders
            order_count = len(result_data)
            
            # Calculate total revenue
            total_revenue = sum(order.get("order_total", 0) for order in result_data)
            
            # Create verbal answer (optimized for speaking)
            verbal_answer = f"I found {order_count} completed orders"
            if date_range:
                verbal_answer += f" for {date_range}"
            verbal_answer += f", with total revenue of ${total_revenue:.2f}"
                
            # Create text answer (more detailed)
            text_answer = f"**Order Results:**\n\n"
            if date_range:
                text_answer += f"Time period: {date_range}\n\n"
            text_answer += f"Found {order_count} completed orders with total revenue of **${total_revenue:.2f}**\n\n"
            
            # Add table of orders if we have results
            if order_count > 0:
                text_answer += "**Order Details:**\n\n"
                text_answer += "| Order ID | Customer | Order Date | Total |\n"
                text_answer += "|:---------|:---------|:-----------|:------|\n"
                
                # Add up to 10 orders to the table
                for order in result_data[:10]:
                    order_id = order.get("order_id", "N/A")
                    customer = f"{order.get('customer_first_name', '')} {order.get('customer_last_name', '')}".strip() or "N/A"
                    order_date = order.get("order_created_at", "N/A")
                    total = f"${order.get('order_total', 0):.2f}"
                    
                    text_answer += f"| {order_id} | {customer} | {order_date} | {total} |\n"
                
                # Note if more orders were truncated
                if order_count > 10:
                    text_answer += f"\n_Showing 10 of {order_count} orders._"
            
            return {
                "summary": text_answer,
                "verbal_answer": verbal_answer,
                "text_answer": text_answer,
                "count": order_count,
                "total_revenue": total_revenue,
            } 