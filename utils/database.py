"""
Database access module for the AI Menu Updater application.
Provides functions for connecting to the database and executing queries.
"""

import os
import re
import logging
import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import DB_CONFIG, USER_TIMEZONE, CUSTOMER_DEFAULT_TIMEZONE, DB_TIMEZONE, MOCK_DATA

# Global flag to indicate if we're using mock data
USING_MOCK_DATA = False

# Configure logger
logger = logging.getLogger("ai_menu_updater")

def get_location_timezone(location_id):
    """Get timezone for a specific location, defaulting to EST if not found"""
    # This would normally query the database, but for testing we'll hardcode
    location_timezones = {
        62: CUSTOMER_DEFAULT_TIMEZONE,  # Idle Hour Country Club
        # Add other locations as needed
    }
    return location_timezones.get(location_id, CUSTOMER_DEFAULT_TIMEZONE)

def adjust_query_timezone(query, location_id):
    """Adjust SQL query to handle timezone conversion"""
    location_tz = get_location_timezone(location_id)

    # Replace any date/time comparisons with timezone-aware versions
    if "updated_at" in query:
        # First convert CURRENT_DATE to user timezone (Arizona)
        current_date_in_user_tz = datetime.datetime.now(USER_TIMEZONE).date()

        # Handle different date patterns
        if "CURRENT_DATE" in query:
            # Convert current date to location timezone for comparison
            query = query.replace(
                "CURRENT_DATE",
                f"(CURRENT_DATE AT TIME ZONE 'UTC' AT TIME ZONE '{USER_TIMEZONE.zone}')",
            )

        # Handle the updated_at conversion
        query = query.replace(
            "(o.updated_at - INTERVAL '7 hours')",
            f"(o.updated_at AT TIME ZONE 'UTC' AT TIME ZONE '{location_tz.zone}')",
        )

    return query

def get_db_connection(timeout=3):
    """Get a database connection with fallback to mock mode if database is unavailable
    
    Args:
        timeout: Connection timeout in seconds (default: 3)
        
    Returns:
        Connection object or None if connection fails
    """
    global USING_MOCK_DATA
    
    try:
        # Add timeout to prevent hanging indefinitely
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=timeout,  # Add timeout parameter
        )
        USING_MOCK_DATA = False
        return conn
    except Exception as e:
        logger.warning(f"Database connection failed: {str(e)}. Switching to mock data mode.")
        USING_MOCK_DATA = True
        return None

def execute_menu_query(query: str, params=None) -> Dict[str, Any]:
    """Execute a read-only menu query and return results with mock data fallback"""
    global USING_MOCK_DATA
    conn = None
    
    try:
        conn = get_db_connection()
        
        # If database connection failed, use mock data
        if USING_MOCK_DATA or conn is None:
            mock_result = handle_mock_query(query)
            logger.info(f"Using mock data for query: {query}")
            return mock_result
            
        # If we have a real connection, execute the real query
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        # Convert Decimal types to float for JSON serialization
        results = [
            {
                col: float(val) if isinstance(val, (Decimal))
                else val.isoformat() if isinstance(val, (datetime.date, datetime.datetime))
                else val
                for col, val in row.items()
            }
            for row in cur.fetchall()
        ]

        return {
            "success": True,
            "results": results,
            "columns": [desc[0] for desc in cur.description] if cur.description else [],
            "query": query,
        }
    except Exception as e:
        logger.error(f"Error executing menu query: {str(e)}")
        
        # Try mock data as fallback if real query fails
        if not USING_MOCK_DATA:
            USING_MOCK_DATA = True
            logger.info(f"Falling back to mock data for query: {query}")
            return handle_mock_query(query)
            
        return {"success": False, "error": str(e), "query": query}
    finally:
        if conn and not USING_MOCK_DATA:
            conn.close()

def handle_mock_query(query: str) -> Dict[str, Any]:
    """Parse the SQL query and return appropriate mock data"""
    query = query.lower()
    
    # Before detailed logic, check if the query is trying to use location_id
    # in tables where it might not exist in a real database
    if "location_id" in query and ("items" in query or "menu" in query):
        # For the mock data, we'll simulate as if this is a valid query
        # by removing location_id constraints for testing
        
        # For SELECT queries on items
        if query.startswith("select") and "items" in query:
            results = MOCK_DATA["menu_items"]
            
            # Apply other filters if needed
            if "where" in query:
                # Extract all non-location_id conditions
                # For now, just handle name ILIKE conditions
                if "name ilike" in query:
                    name_match = re.search(r"name ilike\s+'%([^%]+)%'", query)
                    if name_match:
                        search_term = name_match.group(1).lower()
                        results = [r for r in results if search_term in r.get("name", "").lower()]
                
                # Handle disabled status
                if "disabled = true" in query:
                    results = [r for r in results if r.get("disabled", False)]
                elif "disabled = false" in query:
                    results = [r for r in results if not r.get("disabled", False)]
            
            return {
                "success": True,
                "results": results,
                "columns": list(results[0].keys()) if results else [],
                "query": query,
            }
            
        # For UPDATE queries on items
        elif query.startswith("update items"):
            # Handle price updates
            if "price =" in query:
                price_match = re.search(r"price\s*=\s*(\d+\.?\d*)", query)
                item_match = re.search(r"name ilike\s*'%([^%]+)%'", query)
                
                if price_match and item_match:
                    price = float(price_match.group(1))
                    item_name = item_match.group(1)
                    
                    # Find matching items
                    affected_rows = 0
                    for item in MOCK_DATA["menu_items"]:
                        if item_name.lower() in item.get("name", "").lower():
                            item["price"] = price
                            affected_rows += 1
                            
                    return {
                        "success": True,
                        "results": [item for item in MOCK_DATA["menu_items"] if item_name.lower() in item.get("name", "").lower()],
                        "columns": ["name", "price", "disabled"],
                        "query": query,
                    }
                    
            # Handle disabled status updates
            elif "disabled =" in query:
                state_match = re.search(r"disabled\s*=\s*(true|false)", query)
                item_match = re.search(r"name ilike\s*'%([^%]+)%'", query)
                
                if state_match and item_match:
                    disabled = state_match.group(1).lower() == "true"
                    item_name = item_match.group(1)
                    
                    # Find matching items
                    affected_rows = 0
                    for item in MOCK_DATA["menu_items"]:
                        if item_name.lower() in item.get("name", "").lower():
                            item["disabled"] = disabled
                            affected_rows += 1
                            
                    return {
                        "success": True,
                        "results": [item for item in MOCK_DATA["menu_items"] if item_name.lower() in item.get("name", "").lower()],
                        "columns": ["name", "price", "disabled"],
                        "query": query,
                    }
    
    # Continue with the regular query handling logic...
    
    # Count query
    if "count(*)" in query:
        if "orders" in query and "status = 7" in query:
            count_value = 44  # Default number of completed orders
            
            # Check for date constraints
            if "2025-02-21" in query:
                count_value = 44
            elif "2025-02-22" in query:
                count_value = 38
            elif "current_date" in query or datetime.datetime.now().strftime("%Y-%m-%d") in query:
                count_value = 52
                
            return {
                "success": True,
                "results": [{"count": count_value}],
                "columns": ["count"],
                "query": query,
            }
    
    # Orders query
    elif "from orders" in query:
        results = MOCK_DATA["orders"]
        
        # Filter by status if needed
        if "status = 7" in query:
            results = [r for r in results if r.get("status") == 7]
            
        # Limit results if needed
        if "limit" in query:
            limit_match = re.search(r"limit\s+(\d+)", query)
            if limit_match:
                limit = int(limit_match.group(1))
                results = results[:limit]
        
        return {
            "success": True,
            "results": results,
            "columns": list(results[0].keys()) if results else [],
            "query": query,
        }
    
    # Menu items query - this is already handled by the location_id logic above for most cases
    # but we'll keep it for specific queries that don't have location_id
    elif ("from items" in query or "menu items" in query) and "location_id" not in query:
        results = MOCK_DATA["menu_items"]
        
        # Filter by name if needed
        if "name ilike" in query:
            name_match = re.search(r"name ilike\s+'%([^%]+)%'", query)
            if name_match:
                search_term = name_match.group(1).lower()
                results = [r for r in results if search_term in r.get("name", "").lower()]
        
        return {
            "success": True,
            "results": results,
            "columns": list(results[0].keys()) if results else [],
            "query": query,
        }
    
    # Update query (for menu items) - already handled by location_id logic above
    
    # Default fallback
    return {
        "success": True,
        "results": [{"result": "Mock data response"}],
        "columns": ["result"],
        "query": query,
    }

def execute_sql_query(query: str, location_id: int) -> Dict[str, Any]:
    """
    Execute SQL query with proper timezone adjustments.

    Args:
        query: SQL query to execute
        location_id: Location ID for timezone adjustment

    Returns:
        dict: Query result
    """
    # Adjust the query for timezone
    adjusted_query = adjust_query_timezone(query, location_id)

    # Execute the query
    return execute_menu_query(adjusted_query)

def check_database_connection() -> Dict[str, Any]:
    """Check if the database connection is available
    
    Returns:
        dict: Dictionary with connection status
    """
    global USING_MOCK_DATA
    
    try:
        # Use a short timeout for quick check
        conn = get_db_connection(timeout=1)
        if conn is None:
            return {"connected": False, "message": "Connection returned None"}
        
        # If we got here with a real connection, close it and return success
        if not USING_MOCK_DATA and conn:
            conn.close()
            return {"connected": True, "message": "Connected successfully"}
        else:
            return {"connected": False, "message": "Using mock data mode"}
    except Exception as e:
        return {"connected": False, "message": str(e)}

def attempt_db_reconnection() -> Dict[str, Any]:
    """Attempt to reconnect to the database
    
    Returns:
        dict: Dictionary with reconnection result
    """
    global USING_MOCK_DATA
    
    try:
        # Use a short timeout to prevent UI hanging
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"], 
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=2,  # Add short timeout
        )
        
        if conn:
            USING_MOCK_DATA = False
            conn.close()
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": "Connection returned None"}
    except Exception as e:
        return {"success": False, "error": str(e)} 