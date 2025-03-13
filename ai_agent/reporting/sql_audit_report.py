"""
SQL Audit Report Generator

This module implements SQL audit report generation functionality to track and report on 
SQL query execution, results, and validation status as required by the AI Agent Development Plan.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def generate_sql_audit_report(
    test_results: Dict[str, Any],
    audit_log_dir: str,
    logger: logging.Logger
) -> str:
    """
    Generate an SQL audit report from test results.
    
    Args:
        test_results: Test results dictionary containing test scenario outcomes
        audit_log_dir: Directory to store SQL audit logs
        logger: Logger instance
        
    Returns:
        Path to the generated SQL audit report
    """
    logger.info("Generating SQL audit report")
    
    # Create audit log directory if it doesn't exist
    audit_log_path = Path(audit_log_dir)
    audit_log_path.mkdir(parents=True, exist_ok=True)
    
    # Create a report timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a summary report
    summary_report = {
        "report_timestamp": datetime.now().isoformat(),
        "scenarios_executed": len(test_results),
        "sql_queries_executed": 0,
        "sql_validation_passed": 0,
        "sql_validation_failed": 0,
        "scenario_details": {}
    }
    
    # Process each test scenario
    for scenario_name, scenario_result in test_results.items():
        # Extract SQL queries and results
        sql_queries = scenario_result.get("sql_queries", [])
        sql_results = scenario_result.get("sql_results", [])
        sql_validation = scenario_result.get("sql_validation", {})
        
        # Organize SQL data for this scenario
        scenario_sql_data = {
            "scenario_name": scenario_name,
            "execution_timestamp": scenario_result.get("timestamp", datetime.now().isoformat()),
            "total_queries": len(sql_queries),
            "sql_validation_passed": sql_validation.get("is_valid", False),
            "queries": []
        }
        
        # Add each SQL query with its result
        for i, query in enumerate(sql_queries):
            query_result = sql_results[i] if i < len(sql_results) else None
            
            query_data = {
                "query_text": query,
                "execution_time": scenario_result.get("sql_execution_times", {}).get(str(i), None),
                "result": query_result,
                "validation_status": "Unknown"
            }
            
            # Add validation details if available
            if "details" in sql_validation:
                for detail in sql_validation["details"]:
                    if detail.get("query_index", -1) == i:
                        query_data["validation_status"] = "Passed" if detail.get("is_valid", False) else "Failed"
                        query_data["validation_details"] = detail.get("details", "")
            
            scenario_sql_data["queries"].append(query_data)
            
            # Update summary counts
            summary_report["sql_queries_executed"] += 1
            if query_data["validation_status"] == "Passed":
                summary_report["sql_validation_passed"] += 1
            elif query_data["validation_status"] == "Failed":
                summary_report["sql_validation_failed"] += 1
        
        # Save scenario SQL data to a separate file
        scenario_filename = f"{timestamp}_{scenario_name.replace(' ', '_')}_sql_audit.json"
        scenario_path = audit_log_path / scenario_filename
        
        try:
            with open(scenario_path, 'w') as f:
                json.dump(scenario_sql_data, f, indent=2, default=str)
            logger.info(f"SQL audit log for scenario '{scenario_name}' saved to {scenario_path}")
        except Exception as e:
            logger.error(f"Error saving SQL audit log for scenario '{scenario_name}': {str(e)}")
        
        # Add reference to the scenario SQL data file in the summary report
        summary_report["scenario_details"][scenario_name] = {
            "sql_audit_log_file": str(scenario_path),
            "total_queries": len(sql_queries),
            "validation_passed": sql_validation.get("is_valid", False)
        }
    
    # Save summary report
    summary_report_path = audit_log_path / f"{timestamp}_sql_audit_summary.json"
    try:
        with open(summary_report_path, 'w') as f:
            json.dump(summary_report, f, indent=2, default=str)
        logger.info(f"SQL audit summary report saved to {summary_report_path}")
        return str(summary_report_path)
    except Exception as e:
        logger.error(f"Error saving SQL audit summary report: {str(e)}")
        return ""


def generate_html_sql_audit_report(
    test_results: Dict[str, Any],
    audit_log_dir: str,
    logger: logging.Logger
) -> str:
    """
    Generate an HTML SQL audit report from test results.
    
    Args:
        test_results: Test results dictionary containing test scenario outcomes
        audit_log_dir: Directory to store SQL audit logs
        logger: Logger instance
        
    Returns:
        Path to the generated HTML SQL audit report
    """
    logger.info("Generating HTML SQL audit report")
    
    # Create audit log directory if it doesn't exist
    audit_log_path = Path(audit_log_dir)
    audit_log_path.mkdir(parents=True, exist_ok=True)
    
    # Create a report timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Audit Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .scenario {{ background-color: #fff; padding: 15px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; }}
        .query {{ background-color: #f9f9f9; padding: 10px; border-left: 4px solid #007bff; margin-bottom: 10px; }}
        .query-text {{ font-family: monospace; white-space: pre-wrap; }}
        .result {{ font-family: monospace; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .unknown {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>SQL Audit Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Scenarios Executed:</strong> {len(test_results)}</p>
        
        <table>
            <tr>
                <th>Metric</th>
                <th>Count</th>
            </tr>
"""
    
    # Count SQL queries and validation results
    total_queries = 0
    validation_passed = 0
    validation_failed = 0
    
    for scenario_name, scenario_result in test_results.items():
        sql_queries = scenario_result.get("sql_queries", [])
        total_queries += len(sql_queries)
        
        # Count validation results
        sql_validation = scenario_result.get("sql_validation", {})
        if sql_validation.get("is_valid", False):
            validation_passed += 1
        else:
            validation_failed += 1
    
    # Add summary counts to HTML
    html_content += f"""
            <tr>
                <td>Total SQL Queries Executed</td>
                <td>{total_queries}</td>
            </tr>
            <tr>
                <td>Scenarios with SQL Validation Passed</td>
                <td>{validation_passed}</td>
            </tr>
            <tr>
                <td>Scenarios with SQL Validation Failed</td>
                <td>{validation_failed}</td>
            </tr>
        </table>
    </div>
    
    <h2>Scenario Details</h2>
"""
    
    # Add scenario details to HTML
    for scenario_name, scenario_result in test_results.items():
        sql_queries = scenario_result.get("sql_queries", [])
        sql_results = scenario_result.get("sql_results", [])
        sql_validation = scenario_result.get("sql_validation", {})
        validation_status = "passed" if sql_validation.get("is_valid", False) else "failed"
        
        html_content += f"""
    <div class="scenario">
        <h3>{scenario_name}</h3>
        <p><strong>SQL Validation Status:</strong> <span class="{validation_status}">{validation_status.upper()}</span></p>
        <p><strong>Total Queries:</strong> {len(sql_queries)}</p>
        
        <h4>SQL Queries and Results</h4>
"""
        
        # Add each query and its result
        for i, query in enumerate(sql_queries):
            query_result = sql_results[i] if i < len(sql_results) else None
            
            # Determine validation status for this query
            query_validation_status = "unknown"
            validation_details = ""
            
            if "details" in sql_validation:
                for detail in sql_validation["details"]:
                    if detail.get("query_index", -1) == i:
                        query_validation_status = "passed" if detail.get("is_valid", False) else "failed"
                        validation_details = detail.get("details", "")
            
            html_content += f"""
        <div class="query">
            <h5>Query #{i+1}</h5>
            <p><strong>Validation Status:</strong> <span class="{query_validation_status}">{query_validation_status.upper()}</span></p>
            <div class="query-text">{query}</div>
            
            <h6>Result:</h6>
            <div class="result">{json.dumps(query_result, indent=2) if query_result else "No result"}</div>
            
            {f'<h6>Validation Details:</h6><div>{validation_details}</div>' if validation_details else ''}
        </div>
"""
        
        html_content += """
    </div>
"""
    
    # Close HTML document
    html_content += """
</body>
</html>
"""
    
    # Save HTML report
    html_report_path = audit_log_path / f"{timestamp}_sql_audit_report.html"
    try:
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        logger.info(f"HTML SQL audit report saved to {html_report_path}")
        return str(html_report_path)
    except Exception as e:
        logger.error(f"Error saving HTML SQL audit report: {str(e)}")
        return ""


def cleanup_old_audit_logs(
    audit_log_dir: str,
    retention_days: int,
    logger: logging.Logger
) -> None:
    """
    Clean up old SQL audit logs based on retention policy.
    
    Args:
        audit_log_dir: Directory containing SQL audit logs
        retention_days: Number of days to retain logs
        logger: Logger instance
    """
    logger.info(f"Cleaning up SQL audit logs older than {retention_days} days")
    
    try:
        # Calculate cutoff date
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        
        # Get all files in the audit log directory
        audit_log_path = Path(audit_log_dir)
        if not audit_log_path.exists() or not audit_log_path.is_dir():
            logger.warning(f"Audit log directory {audit_log_dir} does not exist or is not a directory")
            return
        
        # Check each file against retention policy
        deleted_count = 0
        for file_path in audit_log_path.glob("*_sql_audit*.json") or audit_log_path.glob("*_sql_audit*.html"):
            # Get file modification time
            file_mtime = file_path.stat().st_mtime
            
            # Delete file if older than retention period
            if file_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old SQL audit log files")
    except Exception as e:
        logger.error(f"Error cleaning up old SQL audit logs: {str(e)}") 