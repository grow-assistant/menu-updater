"""
SQL Execution Layer for the Execution Service.

This module provides the main interface for executing SQL queries
and processing the results.
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
import concurrent.futures

from config.settings import Config
from services.execution.db_utils import execute_query, execute_transaction
from services.execution.result_formatter import format_result, get_summary_stats

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

class SQLExecutionLayer:
    """
    A class for executing SQL queries and processing the results.
    """
    
    def __init__(self):
        """Initialize the SQL Execution Layer."""
        config = Config()
        # Use more conservative settings from test_db_connection.py
        self.max_rows = config.get("services.execution.max_rows", 1000)
        self.timeout = config.get("services.execution.timeout", 10)  # Reduced from 30 to 10 seconds
        self.query_retry_count = config.get("services.execution.retry_count", 1)
        self.retry_delay = config.get("services.execution.retry_delay", 0.5)  # seconds between retries
        
        logger.info(f"SQLExecutionLayer initialized with max_rows={self.max_rows}, timeout={self.timeout}")
    
    async def execute_sql(
        self, 
        query: str,
        params: Optional[List[Any]] = None,
        timeout: Optional[float] = None,
        max_rows: Optional[int] = None,
        format_type: str = "json",
        format_options: Optional[Dict[str, Any]] = None,
        include_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            timeout: Timeout in seconds (default: from config)
            max_rows: Maximum number of rows to return (default: from config)
            format_type: Format of the results (default: json)
            format_options: Options for formatting the results
            include_summary: Whether to include summary statistics (default: False)
            
        Returns:
            Dictionary containing the results and execution information
        """
        # Use defaults if not provided
        timeout = timeout or self.timeout
        max_rows = max_rows or self.max_rows
        
        # Add limit to query if needed
        if max_rows:
            query = self._add_limit_if_needed(query, max_rows)
        
        start_time = time.time()
        
        try:
            # Execute the query
            retry_count = 0
            while True:
                try:
                    results = await execute_query(
                        query=query,
                        params=params,
                        timeout=timeout
                    )
                    break  # Success, exit the retry loop
                except asyncio.TimeoutError:
                    logger.warning(f"Query timed out after {timeout} seconds")
                    return {
                        "success": False,
                        "error": f"Query execution timed out after {timeout} seconds",
                        "query": query,
                        "execution_time": time.time() - start_time
                    }
                except Exception as e:
                    retry_count += 1
                    if retry_count <= self.query_retry_count:
                        logger.warning(f"Query execution failed, retrying ({retry_count}/{self.query_retry_count}): {e}")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        # Max retries reached, propagate the exception
                        raise
            
            execution_time = time.time() - start_time
            logger.info(f"SQL query executed in {execution_time:.3f}s")
            
            # Check if the results were truncated
            truncated = False
            row_count = len(results) if results else 0
            if row_count >= max_rows:
                truncated = True
            
            # Format the results
            formatted_results = format_result(
                data=results,
                format_type=format_type,
                format_options=format_options
            )
            
            # Build the response
            response = {
                "success": True,
                "data": formatted_results,
                "execution_time": execution_time,
                "row_count": row_count,
                "truncated": truncated,
                "query": query
            }
            
            # Include summary statistics if requested
            if include_summary and results:
                summary = get_summary_stats(results)
                response["summary"] = summary
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            logger.error(f"Error executing SQL query: {error_message}")
            
            return {
                "success": False,
                "error": error_message,
                "execution_time": execution_time,
                "data": None,
                "row_count": 0,
                "truncated": False,
                "query": query
            }
    
    async def execute_transaction_queries(
        self,
        queries: List[Tuple[str, Optional[List[Any]]]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple SQL queries as a transaction.
        
        Args:
            queries: List of tuples containing (query, params)
            timeout: Timeout in seconds (default: from config)
            
        Returns:
            Dictionary with execution status and metadata
        """
        if not queries:
            return {
                "success": False,
                "error": "No queries provided",
                "execution_time": 0,
                "query_count": 0
            }
        
        # Use default timeout if not provided
        timeout = timeout or self.timeout
        
        start_time = time.time()
        try:
            # Execute the transaction
            await execute_transaction(
                queries=queries,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            logger.info(f"Transaction with {len(queries)} queries executed in {execution_time:.3f}s")
            
            return {
                "success": True,
                "execution_time": execution_time,
                "query_count": len(queries)
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            logger.error(f"Error executing transaction: {error_message}")
            
            return {
                "success": False,
                "error": error_message,
                "execution_time": execution_time,
                "query_count": len(queries)
            }
    
    def _add_limit_if_needed(self, query: str, max_rows: int) -> str:
        """
        Add a LIMIT clause to the query if it doesn't already have one.
        
        Args:
            query: SQL query
            max_rows: Maximum number of rows
            
        Returns:
            Query with LIMIT clause if needed
        """
        # Check if the query already has a LIMIT clause
        if "LIMIT" in query.upper():
            return query
        
        # Add the LIMIT clause
        return f"{query.rstrip(';')} LIMIT {max_rows};"
    
    def execute_sql_sync(
        self, 
        query: str,
        params: Optional[List[Any]] = None,
        timeout: Optional[float] = None,
        max_rows: Optional[int] = None,
        format_type: str = "json",
        format_options: Optional[Dict[str, Any]] = None,
        include_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronous version of execute_sql.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.execute_sql(
                query=query,
                params=params,
                timeout=timeout,
                max_rows=max_rows,
                format_type=format_type,
                format_options=format_options,
                include_summary=include_summary
            )
        )
    
    def execute_transaction_queries_sync(
        self,
        queries: List[Tuple[str, Optional[List[Any]]]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of execute_transaction_queries.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.execute_transaction_queries(
                queries=queries,
                timeout=timeout
            )
        )


# Create a singleton instance
sql_execution_layer = SQLExecutionLayer() 