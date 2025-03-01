"""
SQL database tool for the AI Menu Updater application.
Creates a LangChain tool for executing SQL queries.
"""

import logging
from typing import Callable, Dict, Any, Optional

# Configure logger
logger = logging.getLogger("ai_menu_updater")

# LangChain imports - make backward compatible
try:
    # Try newer LangChain versions
    from langchain_core.tools import BaseTool, Tool
    from pydantic import BaseModel, Field
    
    class SQLDatabaseToolInput(BaseModel):
        """Input for SQLDatabaseTool."""
        query: str = Field(description="SQL query to execute")
        
    class SQLDatabaseTool(BaseTool):
        """Tool for querying a SQL database."""
        name = "sql_database"
        description = """Useful for when you need to execute SQL queries against the database.

Important database schema information:
- The orders table has columns: id, customer_id, location_id, created_at, updated_at, status (NOT order_date or order_status)
- For date filtering, use 'updated_at' instead of 'order_date'
- For status filtering, use 'status' (NOT 'order_status')
- Date format should be 'YYYY-MM-DD'
- When querying orders without a specific status filter, ALWAYS filter for completed orders (status = 7)

Example valid queries:
- SELECT COUNT(*) FROM orders WHERE updated_at::date = '2025-02-21' AND status = 7; -- 7 is the status code for completed orders
- SELECT * FROM orders WHERE updated_at BETWEEN '2025-02-01' AND '2025-02-28' AND status = 7;
- SELECT * FROM orders WHERE status = 7; -- Default to completed orders"""
        
        # Define the input schema
        args_schema = SQLDatabaseToolInput
        
        # Store the execute_query_func in a private attribute
        _execute_query_func: Optional[Callable] = None
        
        def __init__(self, execute_query_func: Callable):
            """Initialize with the function to execute queries"""
            super().__init__()
            self._execute_query_func = execute_query_func
            
        def _run(self, query: str) -> str:
            """Run the query through the execute_query_func and return results"""
            # Log the query
            logger.info(f"Executing SQL query: {query}")
            
            # Execute the query
            result = self._execute_query_func(query)
            
            # Check if the query was successful
            if result.get("success", False):
                # Return the results as a string
                return str(result.get("results", []))
            else:
                # Return an error message
                return f"Error executing query: {result.get('error', 'Unknown error')}"
                
        def _arun(self, query: str):
            """Async version - just calls the normal one for now"""
            raise NotImplementedError("Async execution not implemented")
    
except ImportError:
    # Fallback to older LangChain
    from langchain.tools import Tool

def create_sql_database_tool(execute_query_func: Callable):
    """
    Create a Tool for executing SQL queries on the database.

    Args:
        execute_query_func: Function that executes SQL queries

    Returns:
        Tool: A LangChain Tool for executing SQL queries
    """
    try:
        # Try to use the new style tool class
        try:
            from langchain_core.tools import BaseTool
            # Check if we're dealing with the version that needs Pydantic
            return SQLDatabaseTool(execute_query_func=execute_query_func)
        except (ValueError, AttributeError):
            # This error happens when the BaseTool implementation changed but we have
            # an older LangChain version that doesn't expect Pydantic models
            logger.warning("Falling back to older Tool creation method")
            raise ImportError("Incompatible BaseTool version")
    except (ImportError, NameError):
        # Use old style Tool creation
        def _run_query(query: str) -> str:
            """
            Execute a SQL query and return the results as a string.
            
            Args:
                query: SQL query to execute
                
            Returns:
                str: String representation of the query results
            """
            # Log the query
            logger.info(f"Executing SQL query: {query}")
            
            # Execute the query
            result = execute_query_func(query)
            
            # Check if the query was successful
            if result.get("success", False):
                # Return the results as a string
                return str(result.get("results", []))
            else:
                # Return an error message
                return f"Error executing query: {result.get('error', 'Unknown error')}"

        # Create the tool
        return Tool(
            name="sql_database",
            func=_run_query,
            description="""Useful for when you need to execute SQL queries against the database.

Important database schema information:
- The orders table has columns: id, customer_id, location_id, created_at, updated_at, status (NOT order_date or order_status)
- For date filtering, use 'updated_at' instead of 'order_date'
- For status filtering, use 'status' (NOT 'order_status')
- Date format should be 'YYYY-MM-DD'
- When querying orders without a specific status filter, ALWAYS filter for completed orders (status = 7)

Example valid queries:
- SELECT COUNT(*) FROM orders WHERE updated_at::date = '2025-02-21' AND status = 7; -- 7 is the status code for completed orders
- SELECT * FROM orders WHERE updated_at BETWEEN '2025-02-01' AND '2025-02-28' AND status = 7;
- SELECT * FROM orders WHERE status = 7; -- Default to completed orders""",
        ) 