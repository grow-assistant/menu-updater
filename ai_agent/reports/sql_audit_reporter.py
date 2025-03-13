"""
SQL audit reporting module for the test runner.

This module is responsible for generating SQL audit reports based on test results.
It tracks SQL queries executed during tests, their results, and validation status.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

def generate_sql_audit_report(
    test_results: List[Dict[str, Any]],
    output_path: str,
    scenario_output_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> str:
    """
    Generate SQL audit report based on test results.
    
    Args:
        test_results: List of test results
        output_path: Path to save the SQL audit summary report
        scenario_output_path: Path to save scenario-specific SQL audit report
        logger: Logger instance
        
    Returns:
        Path to the SQL audit report
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("Generating SQL audit report")
    
    # Initialize SQL audit report
    sql_audit_report = {
        "timestamp": datetime.now().isoformat(),
        "scenarios_executed": len(test_results),
        "sql_queries_executed": 0,
        "sql_validation_passed": True,
        "scenarios": {}
    }
    
    # Process test results
    for result in test_results:
        scenario_name = result.get("scenario_name", "Unknown Scenario")
        sql_results = result.get("sql_results", [])
        
        # Add SQL queries executed to the total
        sql_audit_report["sql_queries_executed"] += len(sql_results)
        
        # Check if SQL validation was performed and passed
        validation = result.get("validation", {})
        sql_validation_passed = False
        if "sql_validation" in validation:
            sql_validation_passed = validation["sql_validation"].get("is_valid", False)
        
        # Update SQL validation passed status
        if not sql_validation_passed:
            sql_audit_report["sql_validation_passed"] = False
        
        # Create scenario entry
        scenario_entry = {
            "name": scenario_name,
            "queries_executed": len(sql_results),
            "validation_passed": sql_validation_passed,
            "query_details": []
        }
        
        # Add query details
        for i, sql_result in enumerate(sql_results):
            # Extract query and result from the SQL result
            query = ""
            result = None
            execution_time = 0
            
            if isinstance(sql_result, dict):
                query = sql_result.get("query", "")
                result = sql_result.get("result", None)
                execution_time = sql_result.get("execution_time", 0)
            
            # Create query detail entry
            query_detail = {
                "query_index": i,
                "query": query,
                "result_summary": summarize_result(result),
                "execution_time_ms": execution_time * 1000 if execution_time else 0
            }
            
            scenario_entry["query_details"].append(query_detail)
        
        # Add scenario entry to the report
        sql_audit_report["scenarios"][scenario_name] = scenario_entry
    
    # Save SQL audit report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(sql_audit_report, f, indent=2)
    
    logger.info(f"SQL audit report saved to {output_path}")
    
    # Generate scenario-specific report if requested
    if scenario_output_path and len(test_results) == 1:
        scenario_result = test_results[0]
        scenario_name = scenario_result.get("scenario_name", "Unknown Scenario")
        
        # Create scenario-specific report
        scenario_report = {
            "timestamp": datetime.now().isoformat(),
            "scenario_name": scenario_name,
            "queries_executed": len(scenario_result.get("sql_results", [])),
            "validation_passed": False
        }
        
        # Check if SQL validation was performed and passed
        validation = scenario_result.get("validation", {})
        if "sql_validation" in validation:
            scenario_report["validation_passed"] = validation["sql_validation"].get("is_valid", False)
            scenario_report["validation_details"] = validation["sql_validation"]
        
        # Add SQL results
        scenario_report["sql_results"] = scenario_result.get("sql_results", [])
        
        # Save scenario-specific report
        os.makedirs(os.path.dirname(scenario_output_path), exist_ok=True)
        with open(scenario_output_path, "w") as f:
            json.dump(scenario_report, f, indent=2)
        
        logger.info(f"Scenario-specific SQL audit report saved to {scenario_output_path}")
    
    return output_path

def summarize_result(result: Any) -> Dict[str, Any]:
    """
    Summarize SQL result for reporting.
    
    Args:
        result: SQL result
        
    Returns:
        Summarized result
    """
    if result is None:
        return {"type": "None", "rows": 0}
    
    if isinstance(result, list):
        return {
            "type": "list",
            "rows": len(result),
            "sample": result[:3] if result else []
        }
    
    if isinstance(result, dict):
        return {
            "type": "dict",
            "keys": list(result.keys()),
            "sample": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        }
    
    return {
        "type": str(type(result)),
        "summary": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
    } 