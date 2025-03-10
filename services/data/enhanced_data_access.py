"""
Enhanced Data Access Layer for the Swoop AI Conversational Query Flow.

This module integrates database connections and query caching into a unified interface
for efficient and robust data access with performance monitoring.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import pandas as pd
import time
import threading
import json
from datetime import datetime

from services.data.db_connection_manager import DatabaseConnectionManager
from services.data.query_cache_manager import QueryCacheManager

logger = logging.getLogger(__name__)


class EnhancedDataAccess:
    """
    Enhanced data access layer that provides a unified interface for database operations.
    
    Features:
    - Integrated query caching
    - Connection pooling and management
    - Performance monitoring
    - Query result standardization
    - Schema introspection
    - Transparent handling of database errors
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the enhanced data access layer.
        
        Args:
            config: Configuration dictionary containing database and cache settings
        """
        self.config = config
        
        # Initialize the database connection manager
        self.db_manager = DatabaseConnectionManager(config)
        
        # Initialize the query cache manager
        self.cache_manager = QueryCacheManager(config)
        
        # Tracked relations (for schema changes)
        self._tracked_tables: Set[str] = set()
        
        # Register for cache invalidation when schema changes
        self.cache_manager.register_invalidation_callback(self._cache_invalidation_callback)
        
        # Additional state tracking
        self._last_query_time = 0
        self._query_count = 0
        self._transaction_depth = 0
        self._transaction_lock = threading.RLock()
        
        logger.info("Initialized EnhancedDataAccess layer")
    
    def execute_query(self,
                     sql_query: str,
                     params: Optional[Dict[str, Any]] = None,
                     use_cache: bool = True,
                     cache_ttl: Optional[int] = None,
                     timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a SQL query with integrated caching.
        
        Args:
            sql_query: SQL query to execute
            params: Query parameters (default: None)
            use_cache: Whether to use query caching (default: True)
            cache_ttl: Cache time-to-live in seconds (default: None = use default)
            timeout: Query timeout in seconds (default: None = use default)
            
        Returns:
            Dict containing query results and metadata
        """
        start_time = time.time()
        
        # Track query count
        self._query_count += 1
        
        # Initialize result with defaults
        result = {
            "success": False,
            "data": None,
            "cached": False,
            "execution_time": 0,
            "total_time": 0,
            "rowcount": 0,
            "error": None,
            "query_id": f"q-{int(start_time)}-{self._query_count}"
        }
        
        # Determine if this is a SELECT query
        is_select = sql_query.strip().upper().startswith("SELECT")
        
        # Try to get from cache if it's a cacheable query
        if use_cache and is_select and self._transaction_depth == 0:
            cache_hit, cached_data = self.cache_manager.get(sql_query, params)
            
            if cache_hit:
                result["success"] = True
                result["data"] = cached_data
                result["cached"] = True
                result["rowcount"] = len(cached_data) if isinstance(cached_data, list) else 0
                result["total_time"] = time.time() - start_time
                
                logger.debug(f"Query {result['query_id']} served from cache in {result['total_time']:.4f}s")
                return result
        
        # Not in cache or not using cache, execute the query
        try:
            # Execute query through DB manager
            db_result = self.db_manager.execute_query(
                sql_query=sql_query,
                params=params,
                timeout=timeout
            )
            
            # Process the result
            if db_result["success"]:
                result["success"] = True
                result["data"] = db_result["data"] if is_select else db_result["rowcount"]
                result["rowcount"] = db_result["rowcount"]
                result["execution_time"] = db_result["execution_time"]
                
                # Store in cache if criteria are met
                if use_cache and is_select and self._transaction_depth == 0:
                    self.cache_manager.set(
                        query=sql_query,
                        params=params,
                        result=db_result["data"],
                        is_select=is_select,
                        execution_time=db_result["execution_time"],
                        ttl=cache_ttl
                    )
            else:
                result["error"] = db_result["error"]
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error executing query {result['query_id']}: {e}")
        
        # Calculate total time including cache checks, etc.
        result["total_time"] = time.time() - start_time
        
        # Log query execution
        self._log_query_execution(result, sql_query)
        
        # Update tracking state
        self._last_query_time = time.time()
        
        return result
    
    def query_to_dataframe(self, 
                         sql_query: str, 
                         params: Optional[Dict[str, Any]] = None,
                         use_cache: bool = True,
                         cache_ttl: Optional[int] = None,
                         timeout: Optional[int] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute a SQL query and return result as a pandas DataFrame.
        
        Args:
            sql_query: SQL query to execute
            params: Query parameters
            use_cache: Whether to use query caching
            cache_ttl: Cache time-to-live in seconds
            timeout: Query timeout in seconds
            
        Returns:
            Tuple of (DataFrame, metadata dict)
              - Empty DataFrame on failure
              - metadata contains success, timing, and error information
        """
        result = self.execute_query(
            sql_query=sql_query,
            params=params,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            timeout=timeout
        )
        
        metadata = {
            "success": result["success"],
            "cached": result["cached"],
            "execution_time": result["execution_time"],
            "total_time": result["total_time"],
            "rowcount": result["rowcount"],
            "error": result["error"],
            "query_id": result["query_id"]
        }
        
        if result["success"] and isinstance(result["data"], list):
            return pd.DataFrame(result["data"]), metadata
        else:
            return pd.DataFrame(), metadata
    
    def execute_batch(self, 
                     statements: List[Dict[str, Any]],
                     transaction: bool = True) -> List[Dict[str, Any]]:
        """
        Execute a batch of SQL statements, optionally in a transaction.
        
        Args:
            statements: List of statement dicts, each containing:
                - sql: SQL statement to execute
                - params: Optional parameters for the statement
                - name: Optional name for the statement
            transaction: Whether to execute as a single transaction
            
        Returns:
            List of results for each statement
        """
        results = []
        
        # Start transaction if requested
        if transaction:
            self.begin_transaction()
        
        try:
            for idx, stmt in enumerate(statements):
                sql = stmt.get("sql")
                params = stmt.get("params")
                name = stmt.get("name", f"stmt-{idx+1}")
                
                # Execute the statement
                result = self.execute_query(
                    sql_query=sql,
                    params=params,
                    use_cache=False  # No caching in batch mode
                )
                
                # Add statement name to result
                result["statement_name"] = name
                
                results.append(result)
                
                # If any statement fails and we're in transaction mode, abort
                if transaction and not result["success"]:
                    logger.error(f"Statement '{name}' failed, rolling back transaction")
                    self.rollback_transaction()
                    break
            
            # Commit if all succeeded and we're in transaction mode
            if transaction and all(r["success"] for r in results):
                self.commit_transaction()
            elif transaction:
                # Rollback if we haven't already
                if self._transaction_depth > 0:
                    self.rollback_transaction()
                
        except Exception as e:
            logger.error(f"Error in batch execution: {e}")
            
            # Rollback if exception and in transaction
            if transaction and self._transaction_depth > 0:
                self.rollback_transaction()
                
            # Add error to results
            results.append({
                "success": False,
                "statement_name": "batch_error",
                "error": str(e),
                "data": None,
                "rowcount": 0
            })
        
        return results
    
    def begin_transaction(self):
        """Begin a new database transaction or increment depth if already in one."""
        with self._transaction_lock:
            if self._transaction_depth == 0:
                # Start a new transaction
                logger.debug("Beginning new database transaction")
                # Actual transaction begin happens in db_manager.get_transaction() when needed
            
            self._transaction_depth += 1
            logger.debug(f"Transaction depth: {self._transaction_depth}")
    
    def commit_transaction(self):
        """Commit the current transaction if at top level."""
        with self._transaction_lock:
            if self._transaction_depth <= 0:
                logger.warning("Attempted to commit with no active transaction")
                return
            
            self._transaction_depth -= 1
            
            if self._transaction_depth == 0:
                logger.debug("Committing database transaction")
                # Actual commit happens in db_manager.get_transaction() context exit
    
    def rollback_transaction(self):
        """Rollback the current transaction."""
        with self._transaction_lock:
            if self._transaction_depth <= 0:
                logger.warning("Attempted to rollback with no active transaction")
                return
            
            # Reset to 0 regardless of depth (full rollback)
            self._transaction_depth = 0
            logger.debug("Rolling back database transaction")
            # Actual rollback happens in db_manager.get_transaction() context exit
    
    def get_table_schema(self, table_name: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Get schema information for a table.
        
        Args:
            table_name: Name of the table to get schema for
            refresh: Force refresh schema from database
            
        Returns:
            Dict containing table schema information
        """
        # Add to tracked tables
        self._tracked_tables.add(table_name.lower())
        
        # Get schema from DB manager
        schema = self.db_manager.get_table_schema(table_name, refresh)
        
        return schema
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        return self.db_manager.list_tables()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check on the data access layer.
        
        Returns:
            Dict with health status information
        """
        start_time = time.time()
        
        # Get individual component health
        db_health = self.db_manager.health_check()
        cache_stats = self.cache_manager.get_stats()
        
        # Compile overall health
        health_info = {
            "service": "enhanced_data_access",
            "status": "ok" if db_health["status"] == "ok" else "error",
            "components": {
                "database": db_health,
                "cache": {
                    "status": "ok",
                    "stats": cache_stats
                }
            },
            "response_time": time.time() - start_time
        }
        
        # Add cache invalidation info if available
        if hasattr(self, "_last_cache_invalidation"):
            health_info["components"]["cache"]["last_invalidation"] = self._last_cache_invalidation
        
        return health_info
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics for the data access layer.
        
        Returns:
            Dict containing performance metrics for both database and cache
        """
        db_metrics = self.db_manager.get_performance_metrics()
        cache_stats = self.cache_manager.get_stats()
        
        metrics = {
            "database": db_metrics,
            "cache": cache_stats,
            "overall": {
                "last_query_time": self._last_query_time,
                "query_count": self._query_count,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return metrics
    
    def invalidate_cache(self, 
                        table_name: Optional[str] = None, 
                        pattern: Optional[str] = None, 
                        complete: bool = False) -> int:
        """
        Invalidate the query cache.
        
        Args:
            table_name: Invalidate entries for a specific table
            pattern: Invalidate entries matching pattern
            complete: Clear the entire cache
            
        Returns:
            Number of invalidated entries
        """
        return self.cache_manager.invalidate(table_name, pattern, complete)
    
    def _cache_invalidation_callback(self, 
                                    table_name: Optional[str], 
                                    pattern: Optional[str], 
                                    complete: bool):
        """
        Callback for cache invalidation events.
        
        Args:
            table_name: Table that triggered invalidation
            pattern: Pattern that triggered invalidation
            complete: Whether complete invalidation occurred
        """
        self._last_cache_invalidation = {
            "timestamp": datetime.now().isoformat(),
            "table": table_name,
            "pattern": pattern,
            "complete": complete
        }
    
    def _log_query_execution(self, result: Dict[str, Any], query: str):
        """
        Log information about a query execution.
        
        Args:
            result: Query execution result
            query: The executed query
        """
        # Truncate query for logging
        truncated_query = query[:100] + "..." if len(query) > 100 else query
        
        if result["success"]:
            logger.debug(
                f"Query {result['query_id']} executed in {result['execution_time']:.4f}s "
                f"(total: {result['total_time']:.4f}s, cached: {result['cached']}): "
                f"{truncated_query}"
            )
        else:
            logger.error(
                f"Query {result['query_id']} failed in {result['total_time']:.4f}s: "
                f"{truncated_query} - Error: {result['error']}"
            )


# Singleton instance
_data_access_instance = None
_instance_lock = threading.Lock()

def get_data_access(config: Optional[Dict[str, Any]] = None) -> EnhancedDataAccess:
    """
    Get the singleton instance of EnhancedDataAccess.
    
    Args:
        config: Configuration dictionary (only used if instance doesn't exist yet)
        
    Returns:
        EnhancedDataAccess instance
    """
    global _data_access_instance
    
    if _data_access_instance is None:
        with _instance_lock:
            if _data_access_instance is None:
                if config is None:
                    raise ValueError("Config is required when initializing EnhancedDataAccess")
                
                _data_access_instance = EnhancedDataAccess(config)
    
    return _data_access_instance 