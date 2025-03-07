"""
Database utilities for the Execution Service.

This module provides functions for connecting to and interacting with the database.
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union, AsyncGenerator
import asyncio
import asyncpg
from asyncpg import Connection, Pool
from contextlib import asynccontextmanager

from config.settings import Config

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

# Global connection pool
_pool: Optional[Pool] = None


async def get_connection_pool() -> Pool:
    """
    Get or create a connection pool to the database.
    
    Returns:
        Pool: Connection pool for the database
    """
    global _pool
    
    if _pool is not None:
        return _pool
    
    # Get database configuration
    config = Config()
    db_config = config.get("database", {})
    
    # Required database connection parameters
    db_host = db_config.get("host") or os.environ.get("DB_HOST")
    db_port = db_config.get("port") or os.environ.get("DB_PORT", "5433")
    db_name = db_config.get("name") or os.environ.get("DB_NAME")
    db_user = db_config.get("user") or os.environ.get("DB_USER")
    db_password = db_config.get("password") or os.environ.get("DB_PASSWORD")
    
    # Optional pool configuration - using more conservative values based on test_db_connection.py
    min_size = db_config.get("min_pool_size", 3)  # Moderately increased from original 2
    max_size = db_config.get("max_pool_size", 13)  # Moderately increased from original 10
    
    # Connection timeouts
    connect_timeout = db_config.get("connect_timeout", 3.0)  # Reduced connection timeout
    command_timeout = db_config.get("command_timeout", 10.0)  # Reduced command timeout
    
    # Set max connection age to recycle connections periodically
    max_inactive_connection_lifetime = db_config.get("max_inactive_connection_lifetime", 300.0)  # 5 minutes
    
    # Set application name for easier tracking in database logs
    server_settings = {"application_name": "ai_menu_updater"}
    
    try:
        logger.info(
            f"Creating database connection pool: host={db_host}, port={db_port}, "
            f"database={db_name}, min_size={min_size}, max_size={max_size}"
        )
        
        # Create the connection pool
        _pool = await asyncpg.create_pool(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime,
            timeout=connect_timeout,
            server_settings=server_settings
        )
        
        if _pool is None:
            raise Exception("Failed to create database connection pool")
        
        logger.info("Database connection pool created successfully")
        return _pool
        
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[Connection, None]:
    """
    Get a connection from the pool as a context manager.
    
    Yields:
        Connection: Database connection
    """
    pool = await get_connection_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute_query(
    query: str, 
    params: Optional[List[Any]] = None, 
    timeout: Optional[float] = None,
    fetch_type: str = "all"
) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """
    Execute a SQL query and return the results.
    
    Args:
        query: SQL query to execute
        params: Optional parameters for the query
        timeout: Timeout in seconds (default: None)
        fetch_type: Type of fetch operation ("all", "one", "value", or "status")
        
    Returns:
        Query results as a list of dictionaries, a single dictionary, a value, or None
    """
    start_time = time.time()
    
    try:
        async with get_db_connection() as connection:
            # Use the timeout if specified
            if timeout:
                connection.set_type_codec(
                    'json', encoder=lambda x: x, decoder=lambda x: x,
                    schema='pg_catalog'
                )
                result = await asyncio.wait_for(
                    _execute_query_with_connection(connection, query, params, fetch_type),
                    timeout=timeout
                )
            else:
                connection.set_type_codec(
                    'json', encoder=lambda x: x, decoder=lambda x: x,
                    schema='pg_catalog'
                )
                result = await _execute_query_with_connection(connection, query, params, fetch_type)
            
            elapsed = time.time() - start_time
            logger.debug(f"Query executed in {elapsed:.3f}s: {query[:100]}...")
            return result
            
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"Query timed out after {elapsed:.3f}s: {query[:100]}...")
        raise TimeoutError(f"Query execution timed out after {timeout} seconds")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Query error after {elapsed:.3f}s: {str(e)}")
        raise


async def _execute_query_with_connection(
    connection: Connection, 
    query: str, 
    params: Optional[List[Any]],
    fetch_type: str
) -> Union[List[Dict[str, Any]], Dict[str, Any], Any, None]:
    """Helper function to execute a query with the given connection."""
    if fetch_type == "all":
        return await connection.fetch(query, *(params or []))
    elif fetch_type == "one":
        return await connection.fetchrow(query, *(params or []))
    elif fetch_type == "value":
        return await connection.fetchval(query, *(params or []))
    elif fetch_type == "status":
        return await connection.execute(query, *(params or []))
    else:
        raise ValueError(f"Invalid fetch_type: {fetch_type}")


async def execute_transaction(
    queries: List[Tuple[str, Optional[List[Any]]]], 
    timeout: Optional[float] = None
) -> None:
    """
    Execute multiple SQL queries as a transaction.
    
    Args:
        queries: List of tuples containing (query, params)
        timeout: Timeout in seconds (default: None)
        
    Returns:
        None
    """
    if not queries:
        logger.warning("No queries provided for transaction")
        return
    
    start_time = time.time()
    
    try:
        async with get_db_connection() as connection:
            # Use the timeout if specified
            if timeout:
                await asyncio.wait_for(
                    _execute_transaction_with_connection(connection, queries),
                    timeout=timeout
                )
            else:
                await _execute_transaction_with_connection(connection, queries)
            
            elapsed = time.time() - start_time
            logger.debug(f"Transaction with {len(queries)} queries executed in {elapsed:.3f}s")
            
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"Transaction timed out after {elapsed:.3f}s")
        raise TimeoutError(f"Transaction execution timed out after {timeout} seconds")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Transaction error after {elapsed:.3f}s: {str(e)}")
        raise


async def _execute_transaction_with_connection(
    connection: Connection, 
    queries: List[Tuple[str, Optional[List[Any]]]]
) -> None:
    """Helper function to execute a transaction with the given connection."""
    async with connection.transaction():
        for query, params in queries:
            await connection.execute(query, *(params or []))


async def close_db_pool() -> None:
    """
    Close the database connection pool.
    
    Returns:
        None
    """
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed") 