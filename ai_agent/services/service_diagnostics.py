"""
Service diagnostics module for the test runner.

This module provides functions to diagnose issues with services.
"""

import logging
from typing import Dict, Any, List, Optional

def diagnose_sql_error(error: Exception, query: str, logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Diagnose SQL errors.
    
    Args:
        error: SQL error exception
        query: SQL query that caused the error
        logger: Logger instance
        
    Returns:
        Diagnostic information
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.error(f"SQL error encountered: {str(error)}")
    
    # Create diagnostic information
    diagnostics = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "query": query,
        "possible_causes": [],
        "suggested_fixes": []
    }
    
    # Check for common error patterns
    error_str = str(error).lower()
    
    if "syntax error" in error_str:
        diagnostics["possible_causes"].append("SQL syntax error in query")
        diagnostics["suggested_fixes"].append("Check query syntax")
    
    if "table" in error_str and ("not found" in error_str or "doesn't exist" in error_str):
        diagnostics["possible_causes"].append("Referenced table does not exist")
        diagnostics["suggested_fixes"].append("Verify table name and database schema")
    
    if "column" in error_str and ("not found" in error_str or "doesn't exist" in error_str):
        diagnostics["possible_causes"].append("Referenced column does not exist")
        diagnostics["suggested_fixes"].append("Verify column names in the query")
    
    if "permission" in error_str or "access" in error_str:
        diagnostics["possible_causes"].append("Insufficient database permissions")
        diagnostics["suggested_fixes"].append("Check database user permissions")
    
    # Add generic suggestions if no specific ones found
    if not diagnostics["possible_causes"]:
        diagnostics["possible_causes"].append("Unknown SQL error")
        diagnostics["suggested_fixes"].append("Review query and database structure")
    
    return diagnostics

def diagnose_response_issues(response: str, sql_results: List[Any], logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Diagnose issues with response generation.
    
    Args:
        response: Generated response
        sql_results: SQL query results
        logger: Logger instance
        
    Returns:
        Diagnostic information
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("Diagnosing response issues")
    
    # Create diagnostic information
    diagnostics = {
        "response_length": len(response),
        "issues": [],
        "suggestions": []
    }
    
    # Check for empty or very short response
    if not response:
        diagnostics["issues"].append("Empty response")
        diagnostics["suggestions"].append("Check response generator service")
    elif len(response) < 50:
        diagnostics["issues"].append("Very short response")
        diagnostics["suggestions"].append("Verify response generator is providing complete responses")
    
    # Check if SQL results are reflected in response
    if sql_results:
        # Assume SQL results should be reflected in response
        # Check if response mentions data or results
        if "data" not in response.lower() and "result" not in response.lower():
            diagnostics["issues"].append("Response may not incorporate SQL results")
            diagnostics["suggestions"].append("Improve response generation to include query results")
    
    # Check for placeholder or template content
    placeholder_phrases = ["[INSERT", "PLACEHOLDER", "{VARIABLE}"]
    for phrase in placeholder_phrases:
        if phrase in response:
            diagnostics["issues"].append(f"Response contains placeholder text: {phrase}")
            diagnostics["suggestions"].append("Template substitution may have failed")
    
    return diagnostics

def extract_context_hints(context):
    """
    Extract helpful hints from the context for diagnosing issues.
    
    Args:
        context: Query execution context
        
    Returns:
        dict: Hints extracted from context
    """
    hints = {}
    
    if not context:
        return {"warning": "No context provided"}
    
    # Extract query type
    if "query_type" in context:
        hints["query_type"] = context["query_type"]
    
    # Extract query intent
    if "intent" in context:
        hints["intent"] = context["intent"]
    
    # Extract entities mentioned
    if "entities" in context:
        hints["entities"] = context["entities"]
    
    # Extract location information
    if "location_id" in context:
        hints["location_id"] = context["location_id"]
    
    # Check if schema info was available
    if "schema_info" in context:
        schema_info = context["schema_info"]
        table_count = len(schema_info.get("tables", {}))
        hints["schema_available"] = True
        hints["table_count"] = table_count
    else:
        hints["schema_available"] = False
    
    # Check for sql_generation_hints
    if "sql_generation_hints" in context:
        hints["sql_generation_hints_provided"] = True
        sql_hints = context["sql_generation_hints"]
        if "preferred_tables" in sql_hints:
            hints["preferred_tables"] = sql_hints["preferred_tables"]
    
    return hints

def summarize_service_issues(test_results, logger):
    """
    Summarize service issues based on test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        logger: Logger instance
        
    Returns:
        dict: Summary of service issues
    """
    service_issues = {
        "SQLExecutor": [],
        "SQLGenerator": [],
        "ResponseGenerator": [],
        "RulesService": [],
        "ClassificationService": []
    }
    
    # Define patterns for common service issues
    patterns = {
        "parameter_substitution_failure": {
            "service": "SQLGenerator",
            "description": "Failed to substitute parameters in SQL queries",
            "indicators": ["parameter", "substitution", "placeholder"]
        },
        "schema_mismatch": {
            "service": "SQLGenerator",
            "description": "Generated SQL does not match database schema",
            "indicators": ["column", "table", "does not exist", "no such"]
        },
        "empty_query": {
            "service": "SQLGenerator",
            "description": "Empty SQL query generated",
            "indicators": ["empty query", "null query"]
        },
        "syntax_error": {
            "service": "SQLGenerator",
            "description": "SQL syntax errors",
            "indicators": ["syntax error", "parse error"]
        },
        "empty_response": {
            "service": "ResponseGenerator",
            "description": "Empty response generated",
            "indicators": ["empty response", "null response"]
        },
        "hallucination": {
            "service": "ResponseGenerator",
            "description": "Response contains hallucinated information",
            "indicators": ["hallucination", "not in results"]
        }
    }
    
    # Process test results
    for scenario_name, result in test_results.items():
        # Check for SQL errors
        if "sql_errors" in result and result["sql_errors"]:
            for error in result["sql_errors"]:
                error_message = str(error.get("error_message", ""))
                error_type = error.get("error_type", "unknown")
                
                # Match error patterns to services
                for pattern_name, pattern_info in patterns.items():
                    if any(indicator in error_message.lower() for indicator in pattern_info["indicators"]):
                        service = pattern_info["service"]
                        description = pattern_info["description"]
                        
                        service_issues[service].append({
                            "scenario": scenario_name,
                            "error_type": error_type,
                            "description": description,
                            "error_message": error_message,
                            "root_cause": error.get("root_cause", "Unknown"),
                            "suggestion": error.get("suggestion", "No suggestion available")
                        })
                        break
        
        # Check for response issues
        if "response_issues" in result and result["response_issues"]:
            for issue in result["response_issues"]:
                issue_type = issue.get("type", "unknown")
                
                # Match response issues to services
                for pattern_name, pattern_info in patterns.items():
                    if any(indicator in issue_type.lower() for indicator in pattern_info["indicators"]):
                        service = pattern_info["service"]
                        service_issues[service].append({
                            "scenario": scenario_name,
                            "issue_type": issue_type,
                            "description": issue.get("description", "Unknown issue"),
                            "severity": issue.get("severity", "medium"),
                            "suggestion": issue.get("suggestion", "No suggestion available")
                        })
                        break
    
    # Summarize issues
    summary = {
        "total_issues": sum(len(issues) for issues in service_issues.values()),
        "issues_by_service": {service: len(issues) for service, issues in service_issues.items()},
        "service_issues": service_issues,
        "top_issues": []
    }
    
    # Identify top issues by frequency
    issue_counts = {}
    for service, issues in service_issues.items():
        for issue in issues:
            key = f"{service}: {issue.get('error_type', issue.get('issue_type', 'unknown'))}"
            if key not in issue_counts:
                issue_counts[key] = {
                    "service": service,
                    "type": issue.get("error_type", issue.get("issue_type", "unknown")),
                    "count": 0,
                    "description": issue.get("description", "Unknown issue"),
                    "suggestion": issue.get("suggestion", "No suggestion available")
                }
            issue_counts[key]["count"] += 1
    
    # Sort issues by count
    top_issues = sorted(issue_counts.values(), key=lambda x: x["count"], reverse=True)
    summary["top_issues"] = top_issues[:5]  # Top 5 issues
    
    # Log summary
    logger.info(f"Service issue summary: {summary['total_issues']} total issues found")
    for service, count in summary["issues_by_service"].items():
        if count > 0:
            logger.info(f"  {service}: {count} issues")
    
    return summary 