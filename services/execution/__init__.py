"""
Execution Service for the Swoop AI application.

This package provides functionality for executing SQL queries against
the database and processing the results.
"""

from services.execution.sql_executor import SQLExecutor
from services.execution.db_utils import (
    execute_query,
    execute_transaction,
    close_db_pool
)
from services.execution.result_formatter import (
    format_result,
    get_summary_stats
)
from services.execution.sql_execution_layer import SQLExecutionLayer, sql_execution_layer

__all__ = [
    "SQLExecutor",
    "SQLExecutionLayer", 
    "sql_execution_layer",
    "execute_query",
    "execute_transaction",
    "close_db_pool",
    "format_result",
    "get_summary_stats"
] 