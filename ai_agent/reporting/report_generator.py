"""
Report generation utilities for the test runner.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

def generate_test_report(test_results, output_path=None, logger=None):
    """
    Generate a test report from test results.
    
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
        output_path = os.path.join(reports_dir, f"test_report_{timestamp}.json")
    
    # Count successful tests
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    # Calculate passing percentage
    passing_percentage = successful_tests / total_tests if total_tests > 0 else 0
    
    # Prepare summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "passing_percentage": passing_percentage,
        "failed_tests": [name for name, result in test_results.items() if not result.get("success", False)],
        "passed_tests": [name for name, result in test_results.items() if result.get("success", False)]
    }
    
    # Prepare scenario details
    scenarios = {}
    for scenario_name, result in test_results.items():
        # Remove verbose fields for report
        scenario_result = {
            "success": result.get("success", False),
            "status": result.get("status", "unknown"),
            "query": result.get("query", ""),
            "intent": result.get("intent", "unknown"),
            "sql_executed": result.get("sql_executed"),
            "response": result.get("response"),
            "follow_up": result.get("follow_up"),
            "critique": result.get("critique"),
            "sql_validation": result.get("sql_validation"),
            "response_validation": result.get("response_validation")
        }
        
        # Include errors if present
        if "sql_errors" in result and result["sql_errors"]:
            scenario_result["sql_errors"] = [{
                "error_type": error.get("error_type", "unknown"),
                "error_message": error.get("error_message", "Unknown error"),
                "root_cause": error.get("root_cause", "Unknown"),
                "suggestion": error.get("suggestion", "No suggestion available")
            } for error in result["sql_errors"]]
        
        if "response_issues" in result and result["response_issues"]:
            scenario_result["response_issues"] = result["response_issues"]
        
        if "error" in result and result["error"]:
            scenario_result["error"] = result["error"]
        
        scenarios[scenario_name] = scenario_result
    
    # Prepare report
    report = {
        "summary": summary,
        "scenarios": scenarios
    }
    
    # Write report to file
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Test report generated: {output_path}")
    logger.info(f"Summary: {successful_tests}/{total_tests} tests passed ({passing_percentage:.2%})")
    
    return output_path


def generate_html_report(test_results, output_path=None, logger=None):
    """
    Generate an HTML test report from test results.
    
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
        output_path = os.path.join(reports_dir, f"test_report_{timestamp}.html")
    
    # Count successful tests
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    # Calculate passing percentage
    passing_percentage = successful_tests / total_tests if total_tests > 0 else 0
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Report</title>
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
            .scenario {{
                margin-bottom: 20px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            .scenario-success {{
                border-left: 5px solid #4CAF50;
            }}
            .scenario-failure {{
                border-left: 5px solid #F44336;
            }}
            .scenario-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }}
            .scenario-title {{
                font-weight: bold;
                color: #333;
            }}
            .success-badge {{
                padding: 5px 10px;
                border-radius: 3px;
                color: white;
                background-color: #4CAF50;
            }}
            .failure-badge {{
                padding: 5px 10px;
                border-radius: 3px;
                color: white;
                background-color: #F44336;
            }}
            .details {{
                margin-top: 10px;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 3px;
            }}
            .error {{
                color: #F44336;
                margin-top: 10px;
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 3px;
                overflow-x: auto;
            }}
            .progress-bar {{
                height: 20px;
                background-color: #e0e0e0;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .progress {{
                height: 100%;
                background-color: {("#4CAF50" if passing_percentage >= 0.9 else "#FF9800" if passing_percentage >= 0.7 else "#F44336")};
                border-radius: 10px;
                width: {passing_percentage * 100}%;
                text-align: center;
                line-height: 20px;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test Report</h1>
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
            </div>
            
            <h2>Scenarios</h2>
    """
    
    # Generate scenario details
    for scenario_name, result in sorted(test_results.items()):
        success = result.get("success", False)
        status = result.get("status", "unknown")
        query = result.get("query", "")
        intent = result.get("intent", "unknown")
        sql_executed = result.get("sql_executed", "")
        response = result.get("response", "")
        follow_up = result.get("follow_up", "")
        critique = result.get("critique", "")
        
        html_content += f"""
            <div class="scenario {'scenario-success' if success else 'scenario-failure'}">
                <div class="scenario-header">
                    <div class="scenario-title">{scenario_name}</div>
                    <div class="{'success-badge' if success else 'failure-badge'}">{status.upper()}</div>
                </div>
                <div>
                    <strong>Query:</strong> {query}
                </div>
                <div>
                    <strong>Intent:</strong> {intent}
                </div>
                <div class="details">
                    <strong>SQL Executed:</strong>
                    <pre>{sql_executed or 'N/A'}</pre>
                </div>
                <div class="details">
                    <strong>Response:</strong>
                    <pre>{response or 'N/A'}</pre>
                </div>
                <div class="details">
                    <strong>Follow-up:</strong>
                    <pre>{follow_up or 'N/A'}</pre>
                </div>
                <div class="details">
                    <strong>Critique:</strong>
                    <pre>{critique or 'N/A'}</pre>
                </div>
        """
        
        # Add SQL validation if present
        if "sql_validation" in result and result["sql_validation"]:
            sql_validation = result["sql_validation"]
            html_content += f"""
                <div class="details">
                    <strong>SQL Validation:</strong>
                    <div>
            """
            
            if "expected_pattern" in sql_validation:
                pattern_matched = sql_validation.get("matched", False)
                html_content += f"""
                        <div>
                            <strong>Expected Pattern:</strong> {sql_validation["expected_pattern"]}
                            <span class="{'success-badge' if pattern_matched else 'failure-badge'}">{pattern_matched}</span>
                        </div>
                """
            
            if "expected_tables" in sql_validation:
                all_tables_found = sql_validation.get("all_tables_found", False)
                html_content += f"""
                        <div>
                            <strong>Expected Tables:</strong> {', '.join(sql_validation["expected_tables"])}
                        </div>
                        <div>
                            <strong>Tables Found:</strong> {', '.join(sql_validation.get("tables_found", []))}
                            <span class="{'success-badge' if all_tables_found else 'failure-badge'}">{all_tables_found}</span>
                        </div>
                """
            
            html_content += """
                    </div>
                </div>
            """
        
        # Add response validation if present
        if "response_validation" in result and result["response_validation"]:
            response_validation = result["response_validation"]
            all_phrases_found = response_validation.get("all_phrases_found", False)
            
            html_content += f"""
                <div class="details">
                    <strong>Response Validation:</strong>
                    <div>
                        <strong>Expected Phrases:</strong> {', '.join(response_validation.get("expected_phrases", []))}
                    </div>
                    <div>
                        <strong>Phrases Found:</strong> {', '.join(response_validation.get("phrases_found", []))}
                        <span class="{'success-badge' if all_phrases_found else 'failure-badge'}">{all_phrases_found}</span>
                    </div>
                </div>
            """
        
        # Add SQL errors if present
        if "sql_errors" in result and result["sql_errors"]:
            html_content += """
                <div class="error">
                    <strong>SQL Errors:</strong>
                    <ul>
            """
            
            for error in result["sql_errors"]:
                html_content += f"""
                        <li>
                            <div><strong>Type:</strong> {error.get("error_type", "unknown")}</div>
                            <div><strong>Message:</strong> {error.get("error_message", "Unknown error")}</div>
                            <div><strong>Root Cause:</strong> {error.get("root_cause", "Unknown")}</div>
                            <div><strong>Suggestion:</strong> {error.get("suggestion", "No suggestion available")}</div>
                        </li>
                """
            
            html_content += """
                    </ul>
                </div>
            """
        
        # Add response issues if present
        if "response_issues" in result and result["response_issues"]:
            html_content += """
                <div class="error">
                    <strong>Response Issues:</strong>
                    <ul>
            """
            
            for issue in result["response_issues"]:
                html_content += f"""
                        <li>
                            <div><strong>Type:</strong> {issue.get("type", "unknown")}</div>
                            <div><strong>Description:</strong> {issue.get("description", "Unknown issue")}</div>
                            <div><strong>Severity:</strong> {issue.get("severity", "medium")}</div>
                            <div><strong>Suggestion:</strong> {issue.get("suggestion", "No suggestion available")}</div>
                        </li>
                """
            
            html_content += """
                    </ul>
                </div>
            """
        
        # Add general error if present
        if "error" in result and result["error"]:
            html_content += f"""
                <div class="error">
                    <strong>Error:</strong> {result["error"]}
                </div>
            """
        
        html_content += """
            </div>
        """
    
    # Close HTML
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Write HTML to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"HTML test report generated: {output_path}")
    
    return output_path 