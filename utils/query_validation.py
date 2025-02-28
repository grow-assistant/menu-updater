"""
Query validation utilities for ensuring SQL queries are well-formed and safe.

This module provides functions to check for common errors in SQL queries
and provide diagnostic information for improving query quality.
"""

import re
from typing import List, Tuple


def validate_sql_query(sql_query: str) -> Tuple[bool, List[str]]:
    """
    Validate a SQL query for common issues and errors.

    Args:
        sql_query: The SQL query to validate

    Returns:
        Tuple of (is_valid, issues) where issues is a list of error messages
    """
    issues = []

    # Check for empty query
    if not sql_query or len(sql_query.strip()) < 10:
        issues.append("Query is empty or too short")
        return False, issues

    # Check for basic SQL syntax elements
    if "SELECT" not in sql_query.upper():
        issues.append("Missing SELECT statement")

    if "FROM" not in sql_query.upper():
        issues.append("Missing FROM clause")

    # Check for common table names
    required_tables = ["orders", "locations"]
    found_tables = []

    for table in required_tables:
        if re.search(r"\b" + table + r"\b", sql_query.lower()):
            found_tables.append(table)

    if len(found_tables) < len(required_tables):
        missing = set(required_tables) - set(found_tables)
        issues.append(f"Missing required tables: {', '.join(missing)}")

    # Check for location_id filter which is usually required
    if "location_id" not in sql_query.lower():
        issues.append("Missing location_id filter which is usually required")

    # Check for common SQL syntax errors
    syntax_errors = check_syntax_errors(sql_query)
    if syntax_errors:
        issues.extend(syntax_errors)

    # Check for potential time-related issues
    if "updated_at" in sql_query.lower() or "created_at" in sql_query.lower():
        time_issues = check_time_issues(sql_query)
        if time_issues:
            issues.extend(time_issues)

    is_valid = len(issues) == 0
    return is_valid, issues


def check_syntax_errors(sql_query: str) -> List[str]:
    """Check for common SQL syntax errors."""
    issues = []

    # Check for unclosed parentheses
    open_count = sql_query.count("(")
    close_count = sql_query.count(")")
    if open_count != close_count:
        issues.append(
            f"Mismatched parentheses: {open_count} opening vs {close_count} closing"
        )

    # Check for missing semicolons
    if ";" not in sql_query and len(sql_query) > 100:
        issues.append("Missing semicolon at the end of the query")

    # Check for invalid operators
    invalid_operators = re.findall(r"[<>=!]{3,}", sql_query)
    if invalid_operators:
        issues.append(f"Invalid operators found: {''.join(invalid_operators)}")

    # Check for keyword typos using regex
    common_keywords = [
        "SELECT",
        "FROM",
        "WHERE",
        "GROUP BY",
        "ORDER BY",
        "HAVING",
        "JOIN",
        "LIMIT",
    ]
    for keyword in common_keywords:
        # Look for near-matches like "SLECT" or "GROUPE BY"
        if keyword == "GROUP BY" and "GROUPE BY" in sql_query.upper():
            issues.append("Possible typo: 'GROUPE BY' should be 'GROUP BY'")
        elif keyword == "ORDER BY" and "ORDRE BY" in sql_query.upper():
            issues.append("Possible typo: 'ORDRE BY' should be 'ORDER BY'")
        elif keyword == "SELECT" and re.search(
            r"\bSLECT\b|\bSELCT\b", sql_query.upper()
        ):
            issues.append("Possible typo in 'SELECT' keyword")

    return issues


def check_time_issues(sql_query: str) -> List[str]:
    """Check for common time-related issues in SQL queries."""
    issues = []

    # Check for timezone handling
    if (
        "AT TIME ZONE" not in sql_query
        and "date" in sql_query.lower()
        or "time" in sql_query.lower()
        or "updated_at" in sql_query.lower()
        or "created_at" in sql_query.lower()
    ):
        issues.append("Time-related query is missing timezone handling (AT TIME ZONE)")

    # Check for strange time intervals
    interval_matches = re.findall(r"INTERVAL\s+'(\d+)\s+([^']+)'", sql_query)
    for match in interval_matches:
        value, unit = match
        value = int(value)
        if unit.lower() in ["day", "days"] and value > 3650:
            issues.append(
                f"Suspiciously large interval of {value} days (over 10 years)"
            )
        elif unit.lower() in ["hour", "hours"] and value > 87600:
            issues.append(
                f"Suspiciously large interval of {value} hours (over 10 years)"
            )

    return issues


def provide_query_improvement_suggestions(sql_query: str) -> List[str]:
    """
    Provide suggestions to improve a SQL query.

    Args:
        sql_query: The SQL query to analyze

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    # Check if query has a LIMIT clause
    if "LIMIT" not in sql_query.upper() and "COUNT" not in sql_query.upper():
        suggestions.append(
            "Consider adding a LIMIT clause to prevent returning too many rows"
        )

    # Check for descriptive column aliases
    if "AS" not in sql_query:
        suggestions.append("Consider using column aliases (AS) for better readability")

    # Check for efficient JOIN conditions
    if "JOIN" in sql_query.upper() and "ON" not in sql_query.upper():
        suggestions.append("JOIN clauses should use ON conditions")

    # Check for proper date filters
    if "updated_at" in sql_query.lower() and "INTERVAL" not in sql_query.upper():
        suggestions.append(
            "Consider adding a time range filter with INTERVAL for time-series data"
        )

    # Check for case handling in value clauses
    if (
        "LOWER(" not in sql_query.upper()
        and "UPPER(" not in sql_query.upper()
        and "LIKE" in sql_query.upper()
    ):
        suggestions.append(
            "Consider using LOWER() or UPPER() for case-insensitive string comparisons"
        )

    return suggestions


def fix_common_sql_issues(sql_query: str) -> str:
    """
    Attempt to fix common SQL issues automatically.

    Args:
        sql_query: The SQL query to fix

    Returns:
        Fixed SQL query
    """
    # Ensure updated_at is used instead of created_at for consistency
    fixed_query = sql_query.replace("created_at", "updated_at")

    # Add semicolon if missing
    if ";" not in fixed_query:
        fixed_query = fixed_query.rstrip() + ";"

    # Fix common typos
    fixed_query = fixed_query.replace("GROUPE BY", "GROUP BY")
    fixed_query = fixed_query.replace("ORDRE BY", "ORDER BY")
    fixed_query = fixed_query.replace("SLECT", "SELECT")
    fixed_query = fixed_query.replace("SELCT", "SELECT")

    # Add location_id filter if absent and WHERE clause exists
    if "location_id" not in fixed_query.lower() and "WHERE" in fixed_query.upper():
        fixed_query = fixed_query.replace("WHERE", "WHERE o.location_id = 62 AND")

    return fixed_query
