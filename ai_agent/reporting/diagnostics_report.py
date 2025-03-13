"""
Diagnostics report generation utilities for the test runner.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

def generate_diagnostics_report(test_results, output_path=None, logger=None):
    """
    Generate a diagnostics report from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        output_path: Path to save the report (optional)
        logger: Logger instance (optional)
        
    Returns:
        str: Path to the generated report
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Create reports directory if needed
    if output_path is None:
        project_root = Path(__file__).parents[2]  # Go up 2 levels from reporting/
        reports_dir = os.path.join(project_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create timestamped report file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(reports_dir, f"diagnostics_report_{timestamp}.json")
    
    # Collect service diagnostics
    service_diagnostics = collect_service_diagnostics(test_results, logger)
    
    # Collect error patterns
    error_patterns = collect_error_patterns(test_results, logger)
    
    # Generate root cause analysis
    root_cause_analysis = generate_root_cause_analysis(test_results, service_diagnostics, error_patterns, logger)
    
    # Prepare diagnostics report
    diagnostics_report = {
        "timestamp": datetime.now().isoformat(),
        "service_diagnostics": service_diagnostics,
        "error_patterns": error_patterns,
        "root_cause_analysis": root_cause_analysis,
        "service_health_assessment": assess_service_health(service_diagnostics),
        "priority_recommendations": get_priority_recommendations(service_diagnostics, root_cause_analysis)
    }
    
    # Write report to file
    with open(output_path, "w") as f:
        json.dump(diagnostics_report, f, indent=2)
    
    logger.info(f"Diagnostics report generated: {output_path}")
    
    return output_path


def generate_html_diagnostics_report(test_results, output_path=None, logger=None):
    """
    Generate an HTML diagnostics report from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        output_path: Path to save the report (optional)
        logger: Logger instance (optional)
        
    Returns:
        str: Path to the generated report
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Create reports directory if needed
    if output_path is None:
        project_root = Path(__file__).parents[2]  # Go up 2 levels from reporting/
        reports_dir = os.path.join(project_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create timestamped report file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(reports_dir, f"diagnostics_report_{timestamp}.html")
    
    # Collect service diagnostics
    service_diagnostics = collect_service_diagnostics(test_results, logger)
    
    # Collect error patterns
    error_patterns = collect_error_patterns(test_results, logger)
    
    # Generate root cause analysis
    root_cause_analysis = generate_root_cause_analysis(test_results, service_diagnostics, error_patterns, logger)
    
    # Get service health assessment
    service_health = assess_service_health(service_diagnostics)
    
    # Get priority recommendations
    priority_recommendations = get_priority_recommendations(service_diagnostics, root_cause_analysis)
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Diagnostics Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            h1, h2, h3 {{
                color: #333;
            }}
            .section {{
                margin-bottom: 30px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            .service {{
                margin-bottom: 15px;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 3px;
            }}
            .service-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }}
            .service-title {{
                font-weight: bold;
                color: #333;
            }}
            .status-badge {{
                padding: 5px 10px;
                border-radius: 3px;
                color: white;
            }}
            .status-healthy {{
                background-color: #4CAF50;
            }}
            .status-warning {{
                background-color: #FF9800;
            }}
            .status-critical {{
                background-color: #F44336;
            }}
            .issue {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #f5f5f5;
                border-left: 3px solid #FF9800;
                border-radius: 3px;
            }}
            .error-pattern {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #ffebee;
                border-left: 3px solid #F44336;
                border-radius: 3px;
            }}
            .root-cause {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #fff8e1;
                border-left: 3px solid #FFC107;
                border-radius: 3px;
            }}
            .recommendation {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #e1f5fe;
                border-left: 3px solid #03a9f4;
                border-radius: 3px;
            }}
            .summary-item {{
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Diagnostics Report</h1>
            
            <div class="section">
                <h2>Service Health Assessment</h2>
                <table>
                    <tr>
                        <th>Service</th>
                        <th>Status</th>
                        <th>Error Count</th>
                    </tr>
    """
    
    # Add service health assessment
    for service_name, health_info in service_health.items():
        status = health_info.get("status", "unknown")
        error_count = health_info.get("error_count", 0)
        
        status_class = "status-healthy"
        if status == "warning":
            status_class = "status-warning"
        elif status == "critical":
            status_class = "status-critical"
        
        html_content += f"""
                    <tr>
                        <td>{service_name}</td>
                        <td><span class="status-badge {status_class}">{status.upper()}</span></td>
                        <td>{error_count}</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Priority Recommendations</h2>
    """
    
    # Add priority recommendations
    for recommendation in priority_recommendations:
        html_content += f"""
                <div class="recommendation">
                    <div>{recommendation}</div>
                </div>
        """
    
    # Add error patterns
    html_content += """
            </div>
            
            <div class="section">
                <h2>Error Patterns</h2>
    """
    
    for pattern_name, pattern_info in error_patterns.items():
        html_content += f"""
                <div class="error-pattern">
                    <h3>{pattern_name}</h3>
                    <div class="summary-item">
                        <strong>Count:</strong> {pattern_info.get("count", 0)}
                    </div>
                    <div class="summary-item">
                        <strong>Description:</strong> {pattern_info.get("description", "No description available")}
                    </div>
                    <div class="summary-item">
                        <strong>Affected Scenarios:</strong> {", ".join(pattern_info.get("scenarios", []))}
                    </div>
                </div>
        """
    
    # Add root cause analysis
    html_content += """
            </div>
            
            <div class="section">
                <h2>Root Cause Analysis</h2>
    """
    
    for cause in root_cause_analysis:
        html_content += f"""
                <div class="root-cause">
                    <h3>{cause.get("cause", "Unknown Cause")}</h3>
                    <div class="summary-item">
                        <strong>Impact:</strong> {cause.get("impact", "Unknown")}
                    </div>
                    <div class="summary-item">
                        <strong>Affected Services:</strong> {", ".join(cause.get("affected_services", []))}
                    </div>
                    <div class="summary-item">
                        <strong>Solution:</strong> {cause.get("solution", "No solution available")}
                    </div>
                </div>
        """
    
    # Add service diagnostics
    html_content += """
            </div>
            
            <div class="section">
                <h2>Service Diagnostics</h2>
    """
    
    for service_name, service_info in service_diagnostics.items():
        error_count = service_info.get("error_count", 0)
        status = service_info.get("status", "healthy")
        
        status_class = "status-healthy"
        if status == "warning":
            status_class = "status-warning"
        elif status == "critical":
            status_class = "status-critical"
        
        html_content += f"""
                <div class="service">
                    <div class="service-header">
                        <div class="service-title">{service_name}</div>
                        <div class="status-badge {status_class}">{status.upper()}</div>
                    </div>
                    <div class="summary-item">
                        <strong>Error Count:</strong> {error_count}
                    </div>
        """
        
        # Add errors
        if "errors" in service_info and service_info["errors"]:
            html_content += """
                    <h3>Errors</h3>
                    <table>
                        <tr>
                            <th>Type</th>
                            <th>Count</th>
                            <th>Description</th>
                        </tr>
            """
            
            for error in service_info["errors"]:
                html_content += f"""
                        <tr>
                            <td>{error.get("type", "unknown")}</td>
                            <td>{error.get("count", 1)}</td>
                            <td>{error.get("description", "No description available")}</td>
                        </tr>
                """
            
            html_content += """
                    </table>
            """
        
        # Add remediation suggestions
        if "remediation" in service_info and service_info["remediation"]:
            html_content += """
                    <h3>Remediation Suggestions</h3>
            """
            
            for suggestion in service_info["remediation"]:
                html_content += f"""
                    <div class="recommendation">
                        <div>{suggestion}</div>
                    </div>
                """
        
        html_content += """
                </div>
        """
    
    # Close HTML
    html_content += """
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write HTML to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"HTML diagnostics report generated: {output_path}")
    
    return output_path


def collect_service_diagnostics(test_results, logger):
    """
    Collect service diagnostics from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        logger: Logger instance
        
    Returns:
        dict: Service diagnostics
    """
    service_diagnostics = {
        "SQLExecutor": {
            "error_count": 0,
            "status": "healthy",
            "errors": [],
            "remediation": []
        },
        "SQLGenerator": {
            "error_count": 0,
            "status": "healthy",
            "errors": [],
            "remediation": []
        },
        "ResponseGenerator": {
            "error_count": 0,
            "status": "healthy",
            "errors": [],
            "remediation": []
        },
        "RulesService": {
            "error_count": 0,
            "status": "healthy",
            "errors": [],
            "remediation": []
        },
        "ClassificationService": {
            "error_count": 0,
            "status": "healthy",
            "errors": [],
            "remediation": []
        }
    }
    
    # Process test results
    for scenario_name, result in test_results.items():
        # Check for SQL errors
        if "sql_errors" in result and result["sql_errors"]:
            for error in result["sql_errors"]:
                error_type = error.get("error_type", "unknown")
                
                # Map error types to services
                service = "SQLGenerator"
                description = "SQL Generator error"
                
                if error_type in ["column_does_not_exist", "table_does_not_exist", "ambiguous_column"]:
                    service = "SQLGenerator"
                    description = f"Schema mismatch: {error.get('root_cause', 'Unknown')}"
                elif error_type == "parameter_substitution":
                    service = "SQLGenerator"
                    description = f"Parameter substitution error: {error.get('root_cause', 'Unknown')}"
                elif error_type == "syntax_error":
                    service = "SQLGenerator"
                    description = f"SQL syntax error: {error.get('root_cause', 'Unknown')}"
                elif error_type == "empty_query":
                    service = "SQLGenerator"
                    description = "Empty query was generated"
                elif error_type == "other_sql_error":
                    service = "SQLExecutor"
                    description = f"SQL execution error: {error.get('error_message', 'Unknown')}"
                
                # Update service diagnostics
                service_diagnostics[service]["error_count"] += 1
                
                # Check if this error already exists
                error_exists = False
                for service_error in service_diagnostics[service]["errors"]:
                    if service_error["type"] == error_type:
                        service_error["count"] += 1
                        error_exists = True
                        
                        # Add scenario to affected scenarios if not already present
                        if scenario_name not in service_error["scenarios"]:
                            service_error["scenarios"].append(scenario_name)
                        
                        break
                
                if not error_exists:
                    service_diagnostics[service]["errors"].append({
                        "type": error_type,
                        "description": description,
                        "count": 1,
                        "scenarios": [scenario_name]
                    })
        
        # Check for response issues
        if "response_issues" in result and result["response_issues"]:
            for issue in result["response_issues"]:
                issue_type = issue.get("type", "unknown")
                
                # Map issue types to services
                service = "ResponseGenerator"
                description = "Response Generator issue"
                
                if issue_type == "empty_response":
                    service = "ResponseGenerator"
                    description = "Empty response was generated"
                elif issue_type == "potential_hallucination":
                    service = "ResponseGenerator"
                    description = "Response may contain hallucinated information"
                elif issue_type == "missing_content":
                    service = "ResponseGenerator"
                    description = f"Expected content missing: {issue.get('expected_content', 'Unknown')}"
                
                # Update service diagnostics
                service_diagnostics[service]["error_count"] += 1
                
                # Check if this error already exists
                error_exists = False
                for service_error in service_diagnostics[service]["errors"]:
                    if service_error["type"] == issue_type:
                        service_error["count"] += 1
                        error_exists = True
                        
                        # Add scenario to affected scenarios if not already present
                        if scenario_name not in service_error["scenarios"]:
                            service_error["scenarios"].append(scenario_name)
                        
                        break
                
                if not error_exists:
                    service_diagnostics[service]["errors"].append({
                        "type": issue_type,
                        "description": description,
                        "count": 1,
                        "scenarios": [scenario_name]
                    })
    
    # Determine service status based on error count
    for service_name, service_info in service_diagnostics.items():
        error_count = service_info["error_count"]
        
        if error_count == 0:
            service_info["status"] = "healthy"
        elif error_count <= 2:
            service_info["status"] = "warning"
        else:
            service_info["status"] = "critical"
        
        # Generate remediation suggestions based on errors
        if service_info["errors"]:
            if service_name == "SQLGenerator":
                for error in service_info["errors"]:
                    if error["type"] == "column_does_not_exist" or error["type"] == "table_does_not_exist":
                        service_info["remediation"].append(
                            "Update the SQL Generator with accurate database schema information."
                        )
                    elif error["type"] == "parameter_substitution":
                        service_info["remediation"].append(
                            "Fix parameter handling in the SQL Generator to properly substitute query parameters."
                        )
                    elif error["type"] == "syntax_error":
                        service_info["remediation"].append(
                            "Improve SQL syntax generation in the SQL Generator."
                        )
                    elif error["type"] == "empty_query":
                        service_info["remediation"].append(
                            "Enhance the SQL Generator to handle all query types and ensure it always produces a valid query."
                        )
            elif service_name == "ResponseGenerator":
                for error in service_info["errors"]:
                    if error["type"] == "potential_hallucination":
                        service_info["remediation"].append(
                            "Improve the Response Generator to only include information from the SQL results."
                        )
                    elif error["type"] == "empty_response":
                        service_info["remediation"].append(
                            "Fix the Response Generator to always produce a valid response, even when SQL results are empty."
                        )
            
            # Remove duplicate remediation suggestions
            service_info["remediation"] = list(set(service_info["remediation"]))
    
    return service_diagnostics


def collect_error_patterns(test_results, logger):
    """
    Collect error patterns from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        logger: Logger instance
        
    Returns:
        dict: Error patterns
    """
    error_patterns = {
        "column_does_not_exist": {
            "count": 0,
            "description": "SQL queries reference columns that do not exist in the database schema",
            "scenarios": []
        },
        "table_does_not_exist": {
            "count": 0,
            "description": "SQL queries reference tables that do not exist in the database schema",
            "scenarios": []
        },
        "parameter_substitution": {
            "count": 0,
            "description": "Parameter substitution fails in SQL queries",
            "scenarios": []
        },
        "syntax_error": {
            "count": 0,
            "description": "SQL queries contain syntax errors",
            "scenarios": []
        },
        "empty_query": {
            "count": 0,
            "description": "Empty SQL queries are generated",
            "scenarios": []
        },
        "other_sql_error": {
            "count": 0,
            "description": "Other SQL execution errors",
            "scenarios": []
        },
        "empty_response": {
            "count": 0,
            "description": "Empty responses are generated",
            "scenarios": []
        },
        "potential_hallucination": {
            "count": 0,
            "description": "Responses contain potential hallucinations",
            "scenarios": []
        }
    }
    
    # Process test results
    for scenario_name, result in test_results.items():
        # Check for SQL errors
        if "sql_errors" in result and result["sql_errors"]:
            for error in result["sql_errors"]:
                error_type = error.get("error_type", "unknown")
                
                if error_type in error_patterns:
                    error_patterns[error_type]["count"] += 1
                    
                    # Add scenario to affected scenarios if not already present
                    if scenario_name not in error_patterns[error_type]["scenarios"]:
                        error_patterns[error_type]["scenarios"].append(scenario_name)
                else:
                    error_patterns["other_sql_error"]["count"] += 1
                    
                    # Add scenario to affected scenarios if not already present
                    if scenario_name not in error_patterns["other_sql_error"]["scenarios"]:
                        error_patterns["other_sql_error"]["scenarios"].append(scenario_name)
        
        # Check for response issues
        if "response_issues" in result and result["response_issues"]:
            for issue in result["response_issues"]:
                issue_type = issue.get("type", "unknown")
                
                if issue_type in error_patterns:
                    error_patterns[issue_type]["count"] += 1
                    
                    # Add scenario to affected scenarios if not already present
                    if scenario_name not in error_patterns[issue_type]["scenarios"]:
                        error_patterns[issue_type]["scenarios"].append(scenario_name)
    
    # Remove patterns with zero count
    error_patterns = {k: v for k, v in error_patterns.items() if v["count"] > 0}
    
    return error_patterns


def generate_root_cause_analysis(test_results, service_diagnostics, error_patterns, logger):
    """
    Generate root cause analysis from test results, service diagnostics, and error patterns.
    
    Args:
        test_results: Dictionary of test results by scenario name
        service_diagnostics: Service diagnostics dictionary
        error_patterns: Error patterns dictionary
        logger: Logger instance
        
    Returns:
        list: Root cause analysis
    """
    root_causes = []
    
    # Check for schema issues
    if "column_does_not_exist" in error_patterns or "table_does_not_exist" in error_patterns:
        column_count = error_patterns.get("column_does_not_exist", {}).get("count", 0)
        table_count = error_patterns.get("table_does_not_exist", {}).get("count", 0)
        
        if column_count > 0 or table_count > 0:
            root_causes.append({
                "cause": "Incomplete or inaccurate database schema information",
                "impact": f"{column_count + table_count} errors related to missing schema information",
                "affected_services": ["SQLGenerator"],
                "solution": "Update the SQL Generator with accurate and complete database schema information"
            })
    
    # Check for parameter substitution issues
    if "parameter_substitution" in error_patterns:
        count = error_patterns["parameter_substitution"]["count"]
        
        if count > 0:
            root_causes.append({
                "cause": "Parameter substitution failures in SQL queries",
                "impact": f"{count} errors related to parameter substitution",
                "affected_services": ["SQLGenerator"],
                "solution": "Fix parameter handling in the SQL Generator to properly substitute query parameters"
            })
    
    # Check for syntax errors
    if "syntax_error" in error_patterns:
        count = error_patterns["syntax_error"]["count"]
        
        if count > 0:
            root_causes.append({
                "cause": "SQL syntax generation issues",
                "impact": f"{count} errors related to SQL syntax",
                "affected_services": ["SQLGenerator"],
                "solution": "Improve SQL syntax generation in the SQL Generator"
            })
    
    # Check for empty queries
    if "empty_query" in error_patterns:
        count = error_patterns["empty_query"]["count"]
        
        if count > 0:
            root_causes.append({
                "cause": "SQL Generator fails to produce queries for certain scenarios",
                "impact": f"{count} errors related to empty queries",
                "affected_services": ["SQLGenerator"],
                "solution": "Enhance the SQL Generator to handle all query types and ensure it always produces a valid query"
            })
    
    # Check for hallucinations
    if "potential_hallucination" in error_patterns:
        count = error_patterns["potential_hallucination"]["count"]
        
        if count > 0:
            root_causes.append({
                "cause": "Response Generator may be generating hallucinated information",
                "impact": f"{count} responses with potential hallucinations",
                "affected_services": ["ResponseGenerator"],
                "solution": "Improve the Response Generator to only include information from the SQL results"
            })
    
    # Check for empty responses
    if "empty_response" in error_patterns:
        count = error_patterns["empty_response"]["count"]
        
        if count > 0:
            root_causes.append({
                "cause": "Response Generator fails to produce responses for certain scenarios",
                "impact": f"{count} errors related to empty responses",
                "affected_services": ["ResponseGenerator"],
                "solution": "Fix the Response Generator to always produce a valid response, even when SQL results are empty"
            })
    
    return root_causes


def assess_service_health(service_diagnostics):
    """
    Assess service health based on service diagnostics.
    
    Args:
        service_diagnostics: Service diagnostics dictionary
        
    Returns:
        dict: Service health assessment
    """
    service_health = {}
    
    for service_name, service_info in service_diagnostics.items():
        error_count = service_info["error_count"]
        status = service_info["status"]
        
        service_health[service_name] = {
            "error_count": error_count,
            "status": status
        }
    
    return service_health


def get_priority_recommendations(service_diagnostics, root_cause_analysis):
    """
    Get priority recommendations based on service diagnostics and root cause analysis.
    
    Args:
        service_diagnostics: Service diagnostics dictionary
        root_cause_analysis: Root cause analysis list
        
    Returns:
        list: Priority recommendations
    """
    recommendations = []
    
    # Add recommendations from root cause analysis
    for cause in root_cause_analysis:
        recommendations.append(cause["solution"])
    
    # Add recommendations from service diagnostics
    for service_name, service_info in service_diagnostics.items():
        if service_info["status"] == "critical":
            recommendations.append(f"Critical issues found in {service_name}. Address these issues immediately.")
        
        # Add remediation suggestions if available
        for suggestion in service_info.get("remediation", []):
            recommendations.append(suggestion)
    
    # Remove duplicates
    unique_recommendations = list(set(recommendations))
    
    # Prioritize recommendations
    priority_recommendations = []
    other_recommendations = []
    
    for recommendation in unique_recommendations:
        if "critical" in recommendation.lower() or "immediately" in recommendation.lower():
            priority_recommendations.append(recommendation)
        else:
            other_recommendations.append(recommendation)
    
    return priority_recommendations + other_recommendations 