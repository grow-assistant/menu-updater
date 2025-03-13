"""
Compliance report generation utilities for the test runner.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

def generate_compliance_report(test_results, output_path=None, passing_threshold=0.9, logger=None):
    """
    Generate a compliance report from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        output_path: Path to save the report (optional)
        passing_threshold: Minimum passing percentage (0.0-1.0)
        logger: Logger instance (optional)
        
    Returns:
        tuple: (is_compliant, path_to_report)
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
        output_path = os.path.join(reports_dir, f"compliance_report_{timestamp}.json")
    
    # Count successful tests
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    # Calculate passing percentage
    passing_percentage = successful_tests / total_tests if total_tests > 0 else 0
    
    # Check if passing threshold is met
    is_compliant = passing_percentage >= passing_threshold
    
    # Analyze service issues
    service_diagnostics = analyze_service_issues(test_results, logger)
    
    # Prepare compliance report
    compliance_report = {
        "timestamp": datetime.now().isoformat(),
        "is_compliant": is_compliant,
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "passing_percentage": passing_percentage,
        "passing_threshold": passing_threshold,
        "failed_tests": [name for name, result in test_results.items() if not result.get("success", False)],
        "passed_tests": [name for name, result in test_results.items() if result.get("success", False)],
        "development_plan_compliance": get_development_plan_compliance(test_results, passing_threshold),
        "service_diagnostics": service_diagnostics,
        "recommendations": get_recommendations(test_results, service_diagnostics, passing_percentage, passing_threshold)
    }
    
    # Write report to file
    with open(output_path, "w") as f:
        json.dump(compliance_report, f, indent=2)
    
    logger.info(f"Compliance report generated: {output_path}")
    logger.info(f"Compliance status: {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'}")
    logger.info(f"Passing percentage: {passing_percentage:.2%} (threshold: {passing_threshold:.2%})")
    
    return is_compliant, output_path


def generate_html_compliance_report(test_results, output_path=None, passing_threshold=0.9, logger=None):
    """
    Generate an HTML compliance report from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        output_path: Path to save the report (optional)
        passing_threshold: Minimum passing percentage (0.0-1.0)
        logger: Logger instance (optional)
        
    Returns:
        tuple: (is_compliant, path_to_report)
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
        output_path = os.path.join(reports_dir, f"compliance_report_{timestamp}.html")
    
    # Count successful tests
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    # Calculate passing percentage
    passing_percentage = successful_tests / total_tests if total_tests > 0 else 0
    
    # Check if passing threshold is met
    is_compliant = passing_percentage >= passing_threshold
    
    # Analyze service issues
    service_diagnostics = analyze_service_issues(test_results, logger)
    
    # Get development plan compliance
    dev_plan_compliance = get_development_plan_compliance(test_results, passing_threshold)
    
    # Get recommendations
    recommendations = get_recommendations(test_results, service_diagnostics, passing_percentage, passing_threshold)
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Compliance Report</title>
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
            .summary {{
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }}
            .summary-item {{
                margin-bottom: 10px;
            }}
            .compliance-badge {{
                display: inline-block;
                padding: 10px 15px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                margin-bottom: 20px;
            }}
            .compliant {{
                background-color: #4CAF50;
            }}
            .non-compliant {{
                background-color: #F44336;
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
            .recommendation {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #e1f5fe;
                border-left: 3px solid #03a9f4;
                border-radius: 3px;
            }}
            .progress-bar {{
                height: 20px;
                background-color: #e0e0e0;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .progress {{
                height: 100%;
                background-color: {("#4CAF50" if passing_percentage >= passing_threshold else "#F44336")};
                border-radius: 10px;
                width: {passing_percentage * 100}%;
                text-align: center;
                line-height: 20px;
                color: white;
            }}
            .failed-test {{
                margin-bottom: 10px;
                padding: 10px;
                background-color: #ffebee;
                border-left: 3px solid #F44336;
                border-radius: 3px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Compliance Report</h1>
            
            <div class="compliance-badge {'compliant' if is_compliant else 'non-compliant'}">
                {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'}
            </div>
            
            <div class="summary">
                <h2>Summary</h2>
                <div class="progress-bar">
                    <div class="progress">{int(passing_percentage * 100)}%</div>
                </div>
                <div class="summary-item">
                    <strong>Timestamp:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </div>
                <div class="summary-item">
                    <strong>Total Tests:</strong> {total_tests}
                </div>
                <div class="summary-item">
                    <strong>Successful Tests:</strong> {successful_tests}
                </div>
                <div class="summary-item">
                    <strong>Passing Percentage:</strong> {passing_percentage:.2%}
                </div>
                <div class="summary-item">
                    <strong>Passing Threshold:</strong> {passing_threshold:.2%}
                </div>
            </div>
            
            <div class="section">
                <h2>Service Diagnostics</h2>
    """
    
    # Add service diagnostics
    for service_name, service_info in service_diagnostics.items():
        error_count = service_info.get("error_count", 0)
        status = service_info.get("status", "unknown")
        
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
                    <div>
                        <strong>Error Count:</strong> {error_count}
                    </div>
        """
        
        # Add issues
        if "issues" in service_info and service_info["issues"]:
            html_content += """
                    <h3>Issues</h3>
            """
            
            for issue in service_info["issues"]:
                html_content += f"""
                    <div class="issue">
                        <div><strong>Type:</strong> {issue.get("type", "unknown")}</div>
                        <div><strong>Description:</strong> {issue.get("description", "Unknown issue")}</div>
                        <div><strong>Count:</strong> {issue.get("count", 1)}</div>
                    </div>
                """
        
        # Add recommendations
        if "recommendations" in service_info and service_info["recommendations"]:
            html_content += """
                    <h3>Recommendations</h3>
            """
            
            for recommendation in service_info["recommendations"]:
                html_content += f"""
                    <div class="recommendation">
                        <div>{recommendation}</div>
                    </div>
                """
        
        html_content += """
                </div>
        """
    
    # Add development plan compliance
    html_content += """
            </div>
            
            <div class="section">
                <h2>Development Plan Compliance</h2>
    """
    
    for item in dev_plan_compliance:
        html_content += f"""
                <div class="summary-item">
                    <strong>{item["requirement"]}:</strong> {'Pass' if item["compliant"] else 'Fail'}
                </div>
        """
    
    # Add recommendations
    html_content += """
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
    """
    
    for recommendation in recommendations:
        html_content += f"""
                <div class="recommendation">
                    <div>{recommendation}</div>
                </div>
        """
    
    # Add failed tests
    failed_tests = [name for name, result in test_results.items() if not result.get("success", False)]
    if failed_tests:
        html_content += """
            </div>
            
            <div class="section">
                <h2>Failed Tests</h2>
        """
        
        for test_name in failed_tests:
            result = test_results[test_name]
            error_message = ""
            
            if "error" in result and result["error"]:
                error_message = result["error"]
            elif "sql_errors" in result and result["sql_errors"]:
                error_message = result["sql_errors"][0].get("error_message", "Unknown SQL error")
            
            html_content += f"""
                <div class="failed-test">
                    <div><strong>Test:</strong> {test_name}</div>
                    <div><strong>Query:</strong> {result.get("query", "")}</div>
                    <div><strong>Error:</strong> {error_message}</div>
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
    
    logger.info(f"HTML compliance report generated: {output_path}")
    
    return is_compliant, output_path


def analyze_service_issues(test_results, logger):
    """
    Analyze service issues from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        logger: Logger instance
        
    Returns:
        dict: Service diagnostics
    """
    service_diagnostics = {
        "SQLExecutor": {
            "error_count": 0,
            "issues": [],
            "status": "healthy",
            "recommendations": []
        },
        "SQLGenerator": {
            "error_count": 0,
            "issues": [],
            "status": "healthy",
            "recommendations": []
        },
        "ResponseGenerator": {
            "error_count": 0,
            "issues": [],
            "status": "healthy",
            "recommendations": []
        },
        "RulesService": {
            "error_count": 0,
            "issues": [],
            "status": "healthy",
            "recommendations": []
        },
        "ClassificationService": {
            "error_count": 0,
            "issues": [],
            "status": "healthy",
            "recommendations": []
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
                
                # Check if this issue already exists
                issue_exists = False
                for issue in service_diagnostics[service]["issues"]:
                    if issue["type"] == error_type:
                        issue["count"] += 1
                        issue_exists = True
                        break
                
                if not issue_exists:
                    service_diagnostics[service]["issues"].append({
                        "type": error_type,
                        "description": description,
                        "count": 1
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
                
                # Check if this issue already exists
                issue_exists = False
                for svc_issue in service_diagnostics[service]["issues"]:
                    if svc_issue["type"] == issue_type:
                        svc_issue["count"] += 1
                        issue_exists = True
                        break
                
                if not issue_exists:
                    service_diagnostics[service]["issues"].append({
                        "type": issue_type,
                        "description": description,
                        "count": 1
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
        
        # Generate recommendations based on issues
        if service_info["issues"]:
            for issue in service_info["issues"]:
                if issue["type"] == "column_does_not_exist" or issue["type"] == "table_does_not_exist":
                    service_info["recommendations"].append(
                        "Ensure the SQL Generator has up-to-date schema information for all database tables."
                    )
                elif issue["type"] == "parameter_substitution":
                    service_info["recommendations"].append(
                        "Improve parameter handling in the SQL Generator to properly substitute query parameters."
                    )
                elif issue["type"] == "syntax_error":
                    service_info["recommendations"].append(
                        "Review and fix SQL syntax generation in the SQL Generator."
                    )
                elif issue["type"] == "empty_query":
                    service_info["recommendations"].append(
                        "Enhance SQL Generator to handle all query types and ensure it always produces a valid query."
                    )
                elif issue["type"] == "potential_hallucination":
                    service_info["recommendations"].append(
                        "Improve the Response Generator to only include information from the SQL results."
                    )
                elif issue["type"] == "empty_response":
                    service_info["recommendations"].append(
                        "Fix the Response Generator to always produce a valid response, even when SQL results are empty."
                    )
            
            # Remove duplicate recommendations
            service_info["recommendations"] = list(set(service_info["recommendations"]))
    
    return service_diagnostics


def get_development_plan_compliance(test_results, passing_threshold):
    """
    Get development plan compliance from test results.
    
    Args:
        test_results: Dictionary of test results by scenario name
        passing_threshold: Minimum passing percentage (0.0-1.0)
        
    Returns:
        list: Development plan compliance items
    """
    # Count successful tests
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    # Calculate passing percentage
    passing_percentage = successful_tests / total_tests if total_tests > 0 else 0
    
    # Define requirements
    requirements = [
        {
            "requirement": "Overall passing rate >= 90%",
            "compliant": passing_percentage >= 0.9
        },
        {
            "requirement": "SQL Generator produces valid SQL for all scenarios",
            "compliant": all(result.get("sql_executed") is not None for result in test_results.values())
        },
        {
            "requirement": "Response Generator produces responses for all non-ambiguous scenarios",
            "compliant": all(
                result.get("response") is not None 
                for name, result in test_results.items() 
                if "ambiguous" not in name.lower() and "ambiguous" not in result.get("intent", "").lower()
            )
        },
        {
            "requirement": "Ambiguous requests result in clarification responses",
            "compliant": all(
                (isinstance(result.get("response", ""), str) and 
                 ("clarify" in result.get("response", "").lower() or 
                  "could you please provide" in result.get("response", "").lower() or
                  "more information" in result.get("response", "").lower()))
                for name, result in test_results.items() 
                if "ambiguous" in name.lower() or "ambiguous" in result.get("intent", "").lower()
            )
        }
    ]
    
    return requirements


def get_recommendations(test_results, service_diagnostics, passing_percentage, passing_threshold):
    """
    Get recommendations based on test results and service diagnostics.
    
    Args:
        test_results: Dictionary of test results by scenario name
        service_diagnostics: Service diagnostics dictionary
        passing_percentage: Passing percentage (0.0-1.0)
        passing_threshold: Minimum passing percentage (0.0-1.0)
        
    Returns:
        list: Recommendations
    """
    recommendations = []
    
    # Add recommendations based on passing percentage
    if passing_percentage < passing_threshold:
        recommendations.append(
            f"Increase the passing rate from {passing_percentage:.2%} to at least {passing_threshold:.2%} by fixing the issues below."
        )
    
    # Add recommendations based on service diagnostics
    for service_name, service_info in service_diagnostics.items():
        if service_info["status"] == "critical":
            recommendations.append(
                f"Critical issues found in {service_name}. Address these issues immediately."
            )
        
        # Add service-specific recommendations
        for recommendation in service_info.get("recommendations", []):
            if recommendation not in recommendations:
                recommendations.append(recommendation)
    
    # Add specific recommendations based on failed tests
    failed_tests = [name for name, result in test_results.items() if not result.get("success", False)]
    if failed_tests:
        sql_errors = []
        response_issues = []
        
        for test_name in failed_tests:
            result = test_results[test_name]
            
            if "sql_errors" in result and result["sql_errors"]:
                for error in result["sql_errors"]:
                    sql_errors.append(error.get("error_type", "unknown"))
            
            if "response_issues" in result and result["response_issues"]:
                for issue in result["response_issues"]:
                    response_issues.append(issue.get("type", "unknown"))
        
        # Count and sort error types
        sql_error_counts = {}
        for error_type in sql_errors:
            sql_error_counts[error_type] = sql_error_counts.get(error_type, 0) + 1
        
        response_issue_counts = {}
        for issue_type in response_issues:
            response_issue_counts[issue_type] = response_issue_counts.get(issue_type, 0) + 1
        
        # Add recommendations for the most common errors
        if sql_error_counts:
            most_common_error = max(sql_error_counts.items(), key=lambda x: x[1])
            if most_common_error[0] == "column_does_not_exist" or most_common_error[0] == "table_does_not_exist":
                recommendations.append(
                    "Update the database schema information provided to the SQL Generator."
                )
            elif most_common_error[0] == "parameter_substitution":
                recommendations.append(
                    "Fix parameter substitution in the SQL Generator to correctly handle query parameters."
                )
            elif most_common_error[0] == "syntax_error":
                recommendations.append(
                    "Improve SQL syntax generation in the SQL Generator to avoid syntax errors."
                )
            elif most_common_error[0] == "empty_query":
                recommendations.append(
                    "Ensure the SQL Generator always produces a valid query for all query types."
                )
        
        if response_issue_counts:
            most_common_issue = max(response_issue_counts.items(), key=lambda x: x[1])
            if most_common_issue[0] == "potential_hallucination":
                recommendations.append(
                    "Improve the Response Generator to avoid hallucinations by strictly using data from SQL results."
                )
            elif most_common_issue[0] == "empty_response":
                recommendations.append(
                    "Fix the Response Generator to always produce a valid response, even for empty SQL results."
                )
    
    # Remove duplicates and sort recommendations
    unique_recommendations = list(set(recommendations))
    
    # Prioritize recommendations
    priority_recommendations = []
    other_recommendations = []
    
    for recommendation in unique_recommendations:
        if "Critical" in recommendation or "immediately" in recommendation or "improve" in recommendation.lower():
            priority_recommendations.append(recommendation)
        else:
            other_recommendations.append(recommendation)
    
    return priority_recommendations + other_recommendations 