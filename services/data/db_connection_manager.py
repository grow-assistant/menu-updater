"""
Enhanced Database Connection Manager for Swoop AI Conversational Query Flow.

This module provides a robust data access layer with connection pooling, 
retry mechanisms, and performance monitoring.
"""
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import logging
import time
import pandas as pd
import threading
import queue
from datetime import datetime, timedelta
from contextlib import contextmanager
import re
import json
import traceback

# SQLAlchemy imports
from sqlalchemy import create_engine, text, exc, MetaData, Table, Column, inspect
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Enhanced database connection manager with pooling, monitoring, and fault tolerance.
    
    Features:
    - Connection pooling with configurable parameters
    - Automatic retry for transient failures
    - Query timeout mechanism
    - Performance monitoring and metrics collection
    - Connection validation and health checks
    - Schema introspection capabilities
    - Transaction management
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the database connection manager.
        
        Args:
            config: Dictionary containing configuration options including:
                - connection_string: Database connection string
                - pool_size: Size of the connection pool (default: 8)
                - max_overflow: Maximum overflow connections (default: 5)
                - pool_timeout: Timeout for getting a connection from pool (default: 8)
                - pool_recycle: Time in seconds to recycle connections (default: 600)
                - connect_args: Additional connection arguments
                - max_retries: Maximum number of retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 0.5)
                - default_timeout: Default query timeout in seconds (default: 30)
                - application_name: Application name for connection tracking
        """
        # Extract database configuration
        db_config = config.get("database", {})
        connection_string = db_config.get("connection_string")
        
        if not connection_string:
            msg = "Database connection string not provided in configuration"
            logger.error(msg)
            raise ValueError(msg)
        
        # Store config for later use
        self.config = config
        self.connection_string = connection_string
        
        # Retry and timeout settings
        self.max_retries = db_config.get("max_retries", 3)
        self.retry_delay = db_config.get("retry_delay", 0.5)
        self.default_timeout = db_config.get("default_timeout", 30)
        
        # Connection pool settings
        pool_size = db_config.get("pool_size", 8)
        max_overflow = db_config.get("max_overflow", 5)
        pool_timeout = db_config.get("pool_timeout", 8)
        pool_recycle = db_config.get("pool_recycle", 600)
        
        # Set application name for easier connection tracking
        connect_args = db_config.get("connect_args", {})
        if "application_name" not in connect_args and db_config.get("application_name"):
            connect_args["application_name"] = db_config.get("application_name")
        
        # Create engine with connection pooling
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=db_config.get("pool_pre_ping", True),
            connect_args=connect_args
        )
        
        # Performance monitoring
        self.query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_execution_time": 0,
            "average_execution_time": 0,
            "slowest_query": {"query": None, "time": 0},
            "fastest_query": {"query": None, "time": float('inf')},
            "recent_errors": [],
            "query_history": []
        }
        
        # Maximum history to keep
        self.max_history = db_config.get("max_history", 100)
        self.max_recent_errors = db_config.get("max_recent_errors", 20)
        
        # Thread safety for stats
        self._stats_lock = threading.Lock()
        
        # Cache for table metadata
        self.metadata_cache = {}
        self.metadata_cache_expiry = {}
        self.metadata_cache_ttl = db_config.get("metadata_cache_ttl", 3600)  # 1 hour default
        
        logger.info(f"Initialized DatabaseConnectionManager with pool_size={pool_size}")
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool using a context manager.
        
        Usage:
            with db_manager.get_connection() as conn:
                result = conn.execute(text("SELECT * FROM users"))
        
        Yields:
            SQLAlchemy connection object
        """
        connection = None
        try:
            connection = self.engine.connect()
            yield connection
        except Exception as e:
            logger.error(f"Error acquiring connection: {str(e)}")
            if connection:
                connection.close()
            raise
        finally:
            if connection:
                connection.close()
    
    @contextmanager
    def get_transaction(self):
        """
        Get a connection with transaction support using a context manager.
        
        Usage:
            with db_manager.get_transaction() as conn:
                conn.execute(text("INSERT INTO users VALUES (...)"))
                conn.execute(text("UPDATE user_stats SET ..."))
                # Auto-commits on exit if no exceptions, rolls back on exception
        
        Yields:
            SQLAlchemy connection object with transaction
        """
        connection = None
        try:
            connection = self.engine.connect()
            transaction = connection.begin()
            try:
                yield connection
                transaction.commit()
            except Exception:
                transaction.rollback()
                raise
        except Exception as e:
            logger.error(f"Error in transaction: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, 
                      sql_query: str, 
                      params: Optional[Dict[str, Any]] = None, 
                      timeout: Optional[int] = None,
                      max_retries: Optional[int] = None,
                      retry_delay: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a SQL query with retry logic and timeout.
        
        Args:
            sql_query: SQL query string
            params: Query parameters
            timeout: Query timeout in seconds (None uses default)
            max_retries: Max retry attempts (None uses default)
            retry_delay: Delay between retries (None uses default)
            
        Returns:
            Dict containing:
                - success: Whether query executed successfully
                - is_select: Whether it was a SELECT query
                - data: For SELECT queries, the result data
                - rowcount: For non-SELECT queries, the number of affected rows
                - error: Error message if failed
                - execution_time: Query execution time in seconds
        """
        # Use defaults if not specified
        actual_timeout = timeout if timeout is not None else self.default_timeout
        actual_max_retries = max_retries if max_retries is not None else self.max_retries
        actual_retry_delay = retry_delay if retry_delay is not None else self.retry_delay
        
        # Initialize params dict if None
        if params is None:
            params = {}
        
        # Preprocess query (add location filters, etc.)
        processed_query, processed_params = self._preprocess_query(sql_query, params)
        
        # Determine if this is a SELECT query
        is_select = self._is_select_query(processed_query)
        
        result = {
            "success": False,
            "is_select": is_select,
            "data": [] if is_select else None,
            "rowcount": 0,
            "error": None,
            "execution_time": 0,
            "query": processed_query
        }
        
        # Retry loop
        attempts = 0
        last_error = None
        
        start_time = time.time()
        
        while attempts < actual_max_retries:
            attempts += 1
            try:
                # Execute with timeout
                execution_result = self._execute_with_timeout(
                    processed_query, 
                    processed_params, 
                    actual_timeout
                )
                
                if is_select:
                    result["data"] = execution_result.to_dict(orient="records")
                    result["rowcount"] = len(result["data"])
                else:
                    result["rowcount"] = execution_result
                
                result["success"] = True
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"Query attempt {attempts} failed: {str(e)}")
                
                # Only retry on certain errors
                if isinstance(e, (OperationalError, TimeoutError)) and attempts < actual_max_retries:
                    time.sleep(actual_retry_delay)
                    continue
                else:
                    break
        
        end_time = time.time()
        execution_time = end_time - start_time
        result["execution_time"] = execution_time
        
        # Record performance metrics
        self._record_query_performance(
            processed_query,
            execution_time,
            result["success"],
            str(last_error) if not result["success"] else None,
            result["rowcount"]
        )
        
        # Set error message if failed
        if not result["success"]:
            result["error"] = str(last_error)
            
        return result
    
    def _execute_with_timeout(self, 
                              sql_query: str, 
                              params: Dict[str, Any],
                              timeout: int) -> Union[pd.DataFrame, int]:
        """
        Execute a query with a timeout using threading.
        
        Args:
            sql_query: SQL query to execute
            params: Query parameters
            timeout: Timeout in seconds
            
        Returns:
            pd.DataFrame for SELECT queries or affected row count for others
            
        Raises:
            TimeoutError: If the query times out
            Various SQL exceptions: If query execution fails
        """
        result_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def worker():
            """Worker thread to execute the query."""
            try:
                with self.get_connection() as connection:
                    if self._is_select_query(sql_query):
                        # For SELECT queries, return a DataFrame
                        df = pd.read_sql(sql_query, connection, params=params)
                        result_queue.put(df)
                    else:
                        # For non-SELECT queries, execute and return affected rows
                        result = connection.execute(text(sql_query), params)
                        result_queue.put(result.rowcount)
            except Exception as e:
                # Put the exception in the error queue
                error_queue.put(e)
                logger.error(f"Query execution error: {str(e)}")
        
        # Start the worker thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # Wait for the thread to complete with timeout
        thread.join(timeout)
        
        # Check if thread is still alive (timeout occurred)
        if thread.is_alive():
            raise TimeoutError(f"Query execution timed out after {timeout} seconds")
        
        # Check for errors
        if not error_queue.empty():
            raise error_queue.get()
        
        # Get the result
        if not result_queue.empty():
            return result_queue.get()
        else:
            raise RuntimeError("Query execution failed with an unknown error")
    
    def _record_query_performance(self, 
                                  sql_query: str,
                                  execution_time: float,
                                  success: bool,
                                  error_type: Optional[str],
                                  row_count: int):
        """
        Record query performance metrics.
        
        Args:
            sql_query: The executed query
            execution_time: Time taken to execute the query
            success: Whether the query succeeded
            error_type: Error message if failed
            row_count: Number of rows affected or returned
        """
        with self._stats_lock:
            self.query_stats["total_queries"] += 1
            
            if success:
                self.query_stats["successful_queries"] += 1
            else:
                self.query_stats["failed_queries"] += 1
                
                # Record the error
                if error_type:
                    self.query_stats["recent_errors"].append({
                        "timestamp": datetime.now().isoformat(),
                        "query": sql_query,
                        "error": error_type
                    })
                    
                    # Trim errors list if it gets too long
                    if len(self.query_stats["recent_errors"]) > self.max_recent_errors:
                        self.query_stats["recent_errors"] = self.query_stats["recent_errors"][-self.max_recent_errors:]
            
            # Update timings
            self.query_stats["total_execution_time"] += execution_time
            self.query_stats["average_execution_time"] = (
                self.query_stats["total_execution_time"] / self.query_stats["total_queries"]
            )
            
            # Update slowest/fastest query if applicable
            if success:
                truncated_query = sql_query[:100] + "..." if len(sql_query) > 100 else sql_query
                
                if execution_time > self.query_stats["slowest_query"]["time"]:
                    self.query_stats["slowest_query"] = {
                        "query": truncated_query,
                        "time": execution_time
                    }
                
                if execution_time < self.query_stats["fastest_query"]["time"]:
                    self.query_stats["fastest_query"] = {
                        "query": truncated_query,
                        "time": execution_time
                    }
            
            # Record in history
            query_record = {
                "timestamp": datetime.now().isoformat(),
                "query": sql_query[:100] + "..." if len(sql_query) > 100 else sql_query,
                "execution_time": execution_time,
                "success": success,
                "rows": row_count
            }
            
            self.query_stats["query_history"].append(query_record)
            
            # Trim history if it gets too long
            if len(self.query_stats["query_history"]) > self.max_history:
                self.query_stats["query_history"] = self.query_stats["query_history"][-self.max_history:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get query performance metrics.
        
        Returns:
            Dict containing query performance statistics
        """
        with self._stats_lock:
            # Create a copy to avoid thread safety issues
            metrics = {
                "total_queries": self.query_stats["total_queries"],
                "successful_queries": self.query_stats["successful_queries"],
                "failed_queries": self.query_stats["failed_queries"],
                "success_rate": (
                    self.query_stats["successful_queries"] / self.query_stats["total_queries"] * 100
                    if self.query_stats["total_queries"] > 0 else 0
                ),
                "average_execution_time": self.query_stats["average_execution_time"],
                "slowest_query": self.query_stats["slowest_query"],
                "fastest_query": (
                    self.query_stats["fastest_query"]
                    if self.query_stats["fastest_query"]["query"] is not None else None
                ),
                "recent_errors": self.query_stats["recent_errors"][-5:],  # Last 5 errors
                "recent_queries": self.query_stats["query_history"][-5:]  # Last 5 queries
            }
            
            return metrics
    
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool status information.
        
        Returns:
            Dict containing pool statistics
        """
        pool = self.engine.pool
        status = {
            "size": pool.size(),
            "checkedin": pool.checkedin(),
            "checkedout": pool.checkedout(),
            "overflow": pool.overflow(),
            "checkedout_overflow": pool.overflow_checkedout(),
        }
        
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.
        
        Returns:
            Dict with health status information
        """
        start_time = time.time()
        status = {
            "service": "database_connection_manager",
            "status": "ok",
            "connection_test": True,
            "response_time": 0,
            "pool_status": self.get_connection_pool_status()
        }
        
        try:
            # Try a simple query to check connection
            self.execute_query("SELECT 1 AS test", timeout=5)
        except Exception as e:
            status["status"] = "error"
            status["connection_test"] = False
            status["error"] = str(e)
            logger.error(f"Database health check failed: {e}")
        
        status["response_time"] = time.time() - start_time
        return status
    
    def _preprocess_query(self, sql_query: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Preprocess a SQL query before execution.
        
        This can include:
        - Adding location_id filters
        - SQL injection prevention
        - Query normalization
        - Parameter type handling
        
        Args:
            sql_query: The original SQL query
            params: The original parameters
            
        Returns:
            Tuple of (processed_query, processed_params)
        """
        processed_query = sql_query
        processed_params = params.copy()
        
        # Add location_id filter if present in params but not in query
        if "location_id" in processed_params and "location_id" not in processed_query:
            # Only modify SELECT queries
            if self._is_select_query(processed_query):
                # Check if there's a WHERE clause
                if "WHERE" in processed_query.upper():
                    # Add to existing WHERE clause
                    processed_query = re.sub(
                        r"\bWHERE\b",
                        "WHERE location_id = :location_id AND ",
                        processed_query,
                        flags=re.IGNORECASE
                    )
                else:
                    # Find position to insert WHERE clause (after FROM table_name)
                    from_match = re.search(r"\bFROM\s+\w+", processed_query, re.IGNORECASE)
                    if from_match:
                        insert_pos = from_match.end()
                        processed_query = (
                            processed_query[:insert_pos] + 
                            " WHERE location_id = :location_id" + 
                            processed_query[insert_pos:]
                        )
        
        # Handle parameter types
        for key, value in processed_params.items():
            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                processed_params[key] = value.isoformat()
            # Convert lists to JSON strings
            elif isinstance(value, (list, dict)):
                processed_params[key] = json.dumps(value)
        
        return processed_query, processed_params
    
    def _is_select_query(self, sql_query: str) -> bool:
        """
        Determine if a SQL query is a SELECT query.
        
        Args:
            sql_query: The SQL query
            
        Returns:
            True if it's a SELECT query, False otherwise
        """
        # Remove comments and normalize whitespace
        normalized_query = re.sub(r"--.*$", "", sql_query, flags=re.MULTILINE)
        normalized_query = re.sub(r"/\*.*?\*/", "", normalized_query, flags=re.DOTALL)
        normalized_query = normalized_query.strip()
        
        # Check if it starts with SELECT
        return normalized_query.upper().startswith("SELECT")
    
    def get_table_schema(self, table_name: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Get the schema information for a table.
        
        Args:
            table_name: Name of the table
            refresh: Whether to refresh the cached schema
            
        Returns:
            Dict containing table schema information
        """
        # Check if we have valid cached metadata
        now = datetime.now()
        if (not refresh and 
            table_name in self.metadata_cache and 
            table_name in self.metadata_cache_expiry and
            self.metadata_cache_expiry[table_name] > now):
            return self.metadata_cache[table_name]
        
        # Get fresh metadata
        try:
            with self.get_connection() as conn:
                inspector = inspect(conn)
                
                # Get columns
                columns = []
                for col in inspector.get_columns(table_name):
                    column_info = {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default"),
                        "primary_key": col.get("primary_key", False)
                    }
                    columns.append(column_info)
                
                # Get primary key
                pk = inspector.get_pk_constraint(table_name)
                primary_keys = pk.get("constrained_columns", [])
                
                # Get foreign keys
                foreign_keys = []
                for fk in inspector.get_foreign_keys(table_name):
                    fk_info = {
                        "name": fk.get("name"),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns"),
                        "constrained_columns": fk.get("constrained_columns")
                    }
                    foreign_keys.append(fk_info)
                
                # Get indices
                indices = []
                for idx in inspector.get_indexes(table_name):
                    idx_info = {
                        "name": idx.get("name"),
                        "unique": idx.get("unique", False),
                        "columns": idx.get("column_names", [])
                    }
                    indices.append(idx_info)
                
                # Compile schema info
                schema_info = {
                    "table_name": table_name,
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "indices": indices
                }
                
                # Cache the result
                self.metadata_cache[table_name] = schema_info
                self.metadata_cache_expiry[table_name] = now + timedelta(seconds=self.metadata_cache_ttl)
                
                return schema_info
                
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            with self.get_connection() as conn:
                inspector = inspect(conn)
                return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []
    
    def validate_connection(self) -> bool:
        """
        Validate the database connection.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup resources when the object is destroyed."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Database connection pool disposed") 