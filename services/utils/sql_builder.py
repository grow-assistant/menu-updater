"""
SQL Builder Utility

This module provides utilities for building SQL queries using templates and variables.
It works with the RulesManager to load SQL patterns and schema information.
"""

import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from services.rules.rules_manager import RulesManager
from services.utils.logging import get_logger

logger = get_logger(__name__)


class SQLBuilder:
    """
    A utility class for building SQL queries from patterns and variables.
    """
    
    def __init__(self, rules_manager: Optional[RulesManager] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the SQLBuilder.
        
        Args:
            rules_manager: Optional RulesManager instance to use for loading SQL patterns
            config: Optional configuration parameters
        """
        self.config = config or {}
        self.rules_manager = rules_manager or RulesManager(config)
    
    def build_query(self, pattern_type: str, pattern_name: str, variables: Dict[str, Any]) -> str:
        """
        Build a SQL query by loading a pattern and substituting variables.
        
        Args:
            pattern_type: The type of pattern (e.g., 'menu', 'order_history')
            pattern_name: The name of the specific pattern
            variables: Dictionary of variable values to substitute
            
        Returns:
            The complete SQL query
        """
        # Get the SQL pattern
        sql_pattern = self.rules_manager.get_sql_pattern(pattern_type, pattern_name)
        
        if not sql_pattern:
            logger.warning(f"SQL pattern '{pattern_name}' not found for type '{pattern_type}'")
            return ""
        
        # Substitute variables
        sql_query = self.rules_manager.substitute_variables(sql_pattern, variables)
        
        return sql_query
    
    def get_schema_info(self, pattern_type: str) -> Dict[str, Any]:
        """
        Get database schema information for a specific pattern type.
        
        Args:
            pattern_type: The type of pattern (e.g., 'menu', 'order_history')
            
        Returns:
            Dictionary containing schema information
        """
        return self.rules_manager.get_schema_for_type(pattern_type)
    
    def get_table_columns(self, pattern_type: str, table_name: str) -> Dict[str, str]:
        """
        Get column information for a specific table.
        
        Args:
            pattern_type: The type of pattern (e.g., 'menu', 'order_history')
            table_name: The name of the table
            
        Returns:
            Dictionary mapping column names to their descriptions
        """
        schema = self.get_schema_info(pattern_type)
        table_info = schema.get("tables", {}).get(table_name, {})
        return table_info.get("columns", {})
    
    def build_select_query(
        self,
        pattern_type: str,
        tables: List[str],
        columns: List[str],
        where_conditions: Optional[List[str]] = None,
        joins: Optional[List[str]] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Build a SELECT query from components.
        
        Args:
            pattern_type: The type of pattern for schema information
            tables: List of table names
            columns: List of columns to select
            where_conditions: Optional list of WHERE conditions
            joins: Optional list of JOIN clauses
            group_by: Optional list of GROUP BY columns
            order_by: Optional list of ORDER BY columns
            limit: Optional LIMIT value
            
        Returns:
            The complete SQL query
        """
        # Start building the query
        query_parts = ["SELECT"]
        
        # Add columns
        if not columns:
            query_parts.append("*")
        else:
            query_parts.append(", ".join(columns))
        
        # Add FROM clause
        query_parts.append("FROM")
        if len(tables) == 1:
            query_parts.append(tables[0])
        else:
            query_parts.append(", ".join(tables))
        
        # Add JOINs
        if joins:
            query_parts.append(" ".join(joins))
        
        # Add WHERE clause
        if where_conditions:
            query_parts.append("WHERE")
            query_parts.append(" AND ".join(where_conditions))
        
        # Add GROUP BY
        if group_by:
            query_parts.append("GROUP BY")
            query_parts.append(", ".join(group_by))
        
        # Add ORDER BY
        if order_by:
            query_parts.append("ORDER BY")
            query_parts.append(", ".join(order_by))
        
        # Add LIMIT
        if limit is not None:
            query_parts.append(f"LIMIT {limit}")
        
        # Combine parts
        query = " ".join(query_parts) + ";"
        
        return query
    
    def build_update_query(
        self,
        pattern_type: str,
        table: str,
        set_values: Dict[str, Any],
        where_conditions: List[str]
    ) -> str:
        """
        Build an UPDATE query.
        
        Args:
            pattern_type: The type of pattern for schema information
            table: Table name to update
            set_values: Dictionary of column:value pairs to set
            where_conditions: List of WHERE conditions
            
        Returns:
            The complete SQL query
        """
        if not set_values or not where_conditions:
            logger.error("Cannot build UPDATE query without SET values and WHERE conditions")
            return ""
        
        # Start building the query
        query_parts = [f"UPDATE {table}"]
        
        # Add SET clause
        set_clauses = []
        for column, value in set_values.items():
            if isinstance(value, str):
                # Special handling for SQL functions (NOW(), etc.)
                if value.upper().endswith("()") and "(" in value and "'" not in value:
                    set_clauses.append(f"{column} = {value}")
                else:
                    # Escape single quotes in strings
                    escaped_value = value.replace("'", "''")
                    set_clauses.append(f"{column} = '{escaped_value}'")
            elif value is None:
                set_clauses.append(f"{column} = NULL")
            else:
                set_clauses.append(f"{column} = {value}")
        
        query_parts.append("SET")
        query_parts.append(", ".join(set_clauses))
        
        # Add WHERE clause
        query_parts.append("WHERE")
        query_parts.append(" AND ".join(where_conditions))
        
        # Combine parts
        query = " ".join(query_parts) + ";"
        
        return query
    
    def build_insert_query(
        self,
        pattern_type: str,
        table: str,
        values: Dict[str, Any]
    ) -> str:
        """
        Build an INSERT query.
        
        Args:
            pattern_type: The type of pattern for schema information
            table: Table name to insert into
            values: Dictionary of column:value pairs to insert
            
        Returns:
            The complete SQL query
        """
        if not values:
            logger.error("Cannot build INSERT query without values")
            return ""
        
        # Start building the query
        query = f"INSERT INTO {table} ("
        
        # Add columns
        columns = list(values.keys())
        query += ", ".join(columns)
        
        # Add VALUES clause
        query += ") VALUES ("
        
        # Process values
        value_strings = []
        for value in values.values():
            if isinstance(value, str):
                # Special handling for SQL functions (NOW(), etc.)
                if value.upper().endswith("()") and "(" in value and "'" not in value:
                    value_strings.append(f"{value}")
                else:
                    # Escape single quotes in strings
                    escaped_value = value.replace("'", "''")
                    value_strings.append(f"'{escaped_value}'")
            elif value is None:
                value_strings.append("NULL")
            else:
                value_strings.append(str(value))
        
        query += ", ".join(value_strings)
        query += ");"
        
        return query
    
    def validate_query(self, query: str) -> bool:
        """
        Perform basic validation on a SQL query.
        
        Args:
            query: The SQL query to validate
            
        Returns:
            True if the query appears valid, False otherwise
        """
        # Check for basic SQL syntax
        if not query or not isinstance(query, str):
            return False
        
        # Check for unsubstituted placeholders
        if re.search(r'\[\w+\]', query):
            logger.warning("Query contains unsubstituted placeholders")
            return False
        
        # Basic check for quotes matching
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            logger.warning("Query has mismatched single quotes")
            return False
        
        double_quotes = query.count('"')
        if double_quotes % 2 != 0:
            logger.warning("Query has mismatched double quotes")
            return False
        
        # Basic check for balanced parentheses
        if query.count("(") != query.count(")"):
            logger.warning("Query has mismatched parentheses")
            return False
        
        return True 