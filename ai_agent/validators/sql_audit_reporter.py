"""
SQL audit reporter for AI agent testing.

This module generates audit reports for SQL queries executed during tests.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

def generate_sql_audit_report(
    test_results: List[Dict[str, Any]],
    validation_results: Dict[str, Any],
    audit_dir: str,
    logger: logging.Logger
) -> str:
    """
    Generate an SQL audit report.
    
    Args:
        test_results: List of test results
        validation_results: Validation results
        audit_dir: Directory to store audit reports
        logger: Logger instance
        
    Returns:
        Path to the SQL audit report
    """
    logger.info("Generating SQL audit report")
    
    # Create audit report structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_report = {
        "timestamp": datetime.now().isoformat(),
        "scenarios_executed": len(test_results),
        "total_queries_executed": sum(len(r.get("sql_queries", [])) for r in test_results),
        "sql_validation_success": validation_results.get("sql_validation_success", False),
        "scenarios": {}
    }
    
    # Add scenario-specific SQL audit data
    for result in test_results:
        scenario_name = result.get("scenario_name", "Unknown")
        sql_queries = result.get("sql_queries", [])
        sql_results = result.get("sql_results", [])
        sql_execution_times = result.get("sql_execution_times", {})
        validation = result.get("validation", {})
        
        # Create scenario audit entry
        scenario_audit = {
            "scenario_name": scenario_name,
            "queries_executed": len(sql_queries),
            "validation_passed": validation.get("sql_validation_success", False),
            "queries": []
        }
        
        # Add each query's details
        for i, (query, result) in enumerate(zip(sql_queries, sql_results)):
            query_time = sql_execution_times.get(str(i), 0)
            
            # Safe result summary
            result_summary = _get_safe_result_summary(result)
            
            query_audit = {
                "query_index": i,
                "query": query,
                "execution_time_ms": query_time * 1000 if isinstance(query_time, (int, float)) else 0,
                "result_summary": result_summary
            }
            
            scenario_audit["queries"].append(query_audit)
        
        audit_report["scenarios"][scenario_name] = scenario_audit
    
    # Generate summary audit report
    os.makedirs(audit_dir, exist_ok=True)
    report_path = os.path.join(audit_dir, f"{timestamp}_sql_audit_summary.json")
    
    try:
        with open(report_path, 'w') as f:
            json.dump(audit_report, f, indent=2)
        logger.info(f"SQL audit report written to {report_path}")
        
        # Also generate scenario-specific audit reports
        for scenario_name, scenario_audit in audit_report["scenarios"].items():
            scenario_path = os.path.join(audit_dir, f"{timestamp}_{scenario_name.replace(' ', '_')}_sql_audit.json")
            with open(scenario_path, 'w') as f:
                json.dump(scenario_audit, f, indent=2)
            logger.info(f"Scenario SQL audit report written to {scenario_path}")
        
        # Generate HTML report for easier human reading
        html_report_path = os.path.join(audit_dir, f"{timestamp}_sql_audit.html")
        _generate_html_report(audit_report, html_report_path, logger)
        
    except Exception as e:
        logger.error(f"Error writing SQL audit report: {str(e)}")
    
    return report_path

def _get_safe_result_summary(result: Any) -> Dict[str, Any]:
    """
    Get a safe summary of SQL results that can be serialized to JSON.
    
    Args:
        result: SQL query result
        
    Returns:
        Dict containing a summary of the result
    """
    summary = {}
    
    try:
        if isinstance(result, list):
            summary["type"] = "list"
            summary["count"] = len(result)
            if result and len(result) > 0:
                if isinstance(result[0], dict):
                    summary["fields"] = list(result[0].keys())
                    summary["sample"] = result[0] if len(result) > 0 else None
        elif isinstance(result, dict):
            summary["type"] = "dict"
            summary["keys"] = list(result.keys())
            
            # Check for standard result formats
            if "rows" in result:
                summary["count"] = len(result.get("rows", []))
                if "columns" in result:
                    summary["fields"] = result.get("columns", [])
            else:
                summary["sample"] = {k: v for k, v in list(result.items())[:5]}
        else:
            summary["type"] = type(result).__name__
            summary["string_value"] = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
    except Exception as e:
        summary["error"] = f"Could not summarize result: {str(e)}"
    
    return summary

def _generate_html_report(
    audit_report: Dict[str, Any],
    output_path: str,
    logger: logging.Logger
) -> None:
    """
    Generate an HTML SQL audit report.
    
    Args:
        audit_report: SQL audit report data
        output_path: Path to write the HTML report
        logger: Logger instance
    """
    try:
        # Create the HTML content in parts
        html_parts = []
        
        # HTML header
        html_parts.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Audit Report</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 { 
            color: #333;
        }
        .header {
            background-color: #f4f4f4;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .summary {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .summary-item {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            flex: 1;
            margin: 0 10px;
            text-align: center;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
        }
        .failure {
            background-color: #f8d7da;
            color: #721c24;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #f4f4f4;
        }
        .query {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
            margin-bottom: 10px;
        }
        .timestamp {
            font-style: italic;
            color: #666;
            margin-bottom: 20px;
        }
        .expandable {
            cursor: pointer;
        }
        .expandable-content {
            display: none;
            margin: 10px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
    </style>
    <script>
        function toggleContent(id) {
            var content = document.getElementById(id);
            if (content.style.display === 'block') {
                content.style.display = 'none';
            } else {
                content.style.display = 'block';
            }
        }
    </script>
</head>
<body>
        """)
        
        # Header section
        header = f"""
    <div class="header">
        <h1>SQL Audit Report</h1>
        <p class="timestamp">Generated: {audit_report.get("timestamp", "Unknown")}</p>
    </div>
        """
        html_parts.append(header)
        
        # Summary section
        success_class = "success" if audit_report.get("sql_validation_success", False) else "failure"
        summary = f"""
    <div class="summary">
        <div class="summary-item">
            <h3>Scenarios Executed</h3>
            <p>{audit_report.get("scenarios_executed", 0)}</p>
        </div>
        <div class="summary-item">
            <h3>Total Queries Executed</h3>
            <p>{audit_report.get("total_queries_executed", 0)}</p>
        </div>
        <div class="summary-item {success_class}">
            <h3>SQL Validation</h3>
            <p>{audit_report.get("sql_validation_success", False)}</p>
        </div>
    </div>
        """
        html_parts.append(summary)
        
        # Add scenario sections
        for scenario_name, scenario_data in audit_report.get("scenarios", {}).items():
            # Scenario header
            scenario_success_class = "success" if scenario_data.get("validation_passed", False) else "failure"
            scenario_header = f"""
    <h2>Scenario: {scenario_name}</h2>
    <div class="summary">
        <div class="summary-item">
            <h3>Queries Executed</h3>
            <p>{scenario_data.get("queries_executed", 0)}</p>
        </div>
        <div class="summary-item {scenario_success_class}">
            <h3>Validation Passed</h3>
            <p>{scenario_data.get("validation_passed", False)}</p>
        </div>
    </div>
    
    <h3>Queries</h3>
    <table>
        <tr>
            <th>Query #</th>
            <th>Execution Time (ms)</th>
            <th>SQL Query</th>
            <th>Result</th>
        </tr>
            """
            html_parts.append(scenario_header)
            
            # Add query rows
            for query_data in scenario_data.get("queries", []):
                query_id = f"{scenario_name.replace(' ', '_')}_query_{query_data.get('query_index', 0)}"
                result_id = f"{scenario_name.replace(' ', '_')}_result_{query_data.get('query_index', 0)}"
                
                # Query preview (first 50 chars)
                query_preview = query_data.get("query", "")[:50] + "..."
                query_full = query_data.get("query", "")
                
                # Result summary as JSON string
                result_summary_json = json.dumps(query_data.get("result_summary", {}), indent=2)
                
                query_row = f"""
        <tr>
            <td>{query_data.get("query_index", 0) + 1}</td>
            <td>{query_data.get("execution_time_ms", 0):.2f}</td>
            <td class="expandable" onclick="toggleContent('{query_id}')">
                {query_preview}
                <div id="{query_id}" class="expandable-content">
                    <div class="query">{query_full}</div>
                </div>
            </td>
            <td class="expandable" onclick="toggleContent('{result_id}')">
                Result Summary
                <div id="{result_id}" class="expandable-content">
                    <pre>{result_summary_json}</pre>
                </div>
            </td>
        </tr>
                """
                html_parts.append(query_row)
            
            # Close the table
            html_parts.append("    </table>")
        
        # HTML footer
        html_parts.append("""
</body>
</html>
        """)
        
        # Combine all parts and write to file
        with open(output_path, 'w') as f:
            f.write(''.join(html_parts))
        
        logger.info(f"HTML SQL audit report written to {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating HTML report: {str(e)}") 