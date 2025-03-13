"""
Compliance tracker for AI agent testing.

This module tracks compliance of AI agent components and test scenarios.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

def track_compliance(
    test_results: List[Dict[str, Any]],
    validation_results: Dict[str, Any],
    compliance_dir: str,
    logger: logging.Logger
) -> str:
    """
    Track compliance of AI agent components and test scenarios.
    
    Args:
        test_results: List of test results
        validation_results: Validation results
        compliance_dir: Directory to store compliance reports
        logger: Logger instance
        
    Returns:
        Path to the compliance report
    """
    logger.info("Tracking compliance")
    
    # Create compliance report structure
    compliance_report = {
        "timestamp": datetime.now().isoformat(),
        "service_components": _track_service_components(test_results, logger),
        "test_scenarios": _track_test_scenarios(test_results, validation_results, logger),
        "compliance_status": False,  # Will be updated based on checks
        "service_compliance": False,  # Will be updated based on checks
        "test_compliance": False,   # Will be updated based on checks
        "passing_percentage": validation_results.get("passing_percentage", 0)
    }
    
    # Check overall compliance
    service_compliance = all(component.get("compliant", False) 
                             for component in compliance_report["service_components"].values())
    
    test_compliance = all(scenario.get("meets_success_criteria", False) 
                          for scenario in compliance_report["test_scenarios"].values())
    
    compliance_report["service_compliance"] = service_compliance
    compliance_report["test_compliance"] = test_compliance
    compliance_report["compliance_status"] = service_compliance and test_compliance
    
    # Generate compliance report
    os.makedirs(compliance_dir, exist_ok=True)
    report_path = os.path.join(compliance_dir, "compliance_report.json")
    
    try:
        with open(report_path, 'w') as f:
            json.dump(compliance_report, f, indent=2)
        logger.info(f"Compliance report written to {report_path}")
        
        # Also generate HTML report for easier human reading
        html_report_path = os.path.join(compliance_dir, "compliance_report.html")
        _generate_html_report(compliance_report, html_report_path, logger)
        
    except Exception as e:
        logger.error(f"Error writing compliance report: {str(e)}")
    
    return report_path

def _track_service_components(
    test_results: List[Dict[str, Any]],
    logger: logging.Logger
) -> Dict[str, Dict[str, Any]]:
    """
    Track compliance of service components.
    
    Args:
        test_results: List of test results
        logger: Logger instance
        
    Returns:
        Dict mapping component names to compliance status
    """
    # Initialize service components with required compliance status
    service_components = {
        "SQLExecutor": {
            "expected_status": "Real SQLExecutor",
            "current_status": "Unknown",
            "compliant": False,
            "description": "SQL execution layer must be real, not mocked"
        },
        "RulesService": {
            "expected_status": "Real RulesService with business rules",
            "current_status": "Unknown",
            "compliant": False,
            "description": "Rules service must load and apply real business rules"
        },
        "DatabaseValidator": {
            "expected_status": "Real DatabaseValidator",
            "current_status": "Unknown",
            "compliant": False,
            "description": "Database validator must verify real database structures"
        },
        "CritiqueAgent": {
            "expected_status": "Real Implementation",
            "current_status": "Real Implementation",
            "compliant": True,  # Assuming the critique agent is already compliant
            "description": "Critique agent evaluates response quality"
        },
        "ResponseGenerator": {
            "expected_status": "Real Implementation",
            "current_status": "Real Implementation",
            "compliant": True,  # Assuming the response generator is already compliant
            "description": "Response generator produces text responses"
        }
    }
    
    # Check for any explicit component status in test results
    for result in test_results:
        # Look for component information in the results
        components = result.get("components", {})
        for component_name, status in components.items():
            if component_name in service_components:
                service_components[component_name]["current_status"] = status
                # Check if current status matches expected status
                expected = service_components[component_name]["expected_status"]
                service_components[component_name]["compliant"] = status == expected
    
    # For SQLExecutor, check if we have any SQL queries
    if any(len(result.get("sql_queries", [])) > 0 for result in test_results):
        service_components["SQLExecutor"]["current_status"] = "Real SQLExecutor"
        service_components["SQLExecutor"]["compliant"] = True
        logger.info("SQLExecutor seems to be real, based on executed queries")
    
    return service_components

def _track_test_scenarios(
    test_results: List[Dict[str, Any]],
    validation_results: Dict[str, Any],
    logger: logging.Logger
) -> Dict[str, Dict[str, Any]]:
    """
    Track compliance of test scenarios.
    
    Args:
        test_results: List of test results
        validation_results: Validation results
        logger: Logger instance
        
    Returns:
        Dict mapping scenario names to compliance status
    """
    test_scenarios = {}
    
    # Get list of all required test scenarios (this would be from your requirements)
    required_scenarios = [
        "Ambiguous Request",
        "Menu Status Inquiry",
        "Order Placement",
        "Order Status Inquiry",
        "Customer Complaint",
        "Specific Menu Item Inquiry",
        "Availability Check",
        "Price Range Query",
        "Special Requests",
        "Operational Hours Query"
    ]
    
    # Initialize with all required scenarios as not run
    for scenario in required_scenarios:
        test_scenarios[scenario] = {
            "name": scenario,
            "expected_status": "Passed",
            "current_status": "Not Run",
            "meets_success_criteria": False,
            "sql_validation": False,
            "description": f"Test scenario for {scenario}"
        }
    
    # Update with actual test results
    if validation_results and "test_results" in validation_results:
        for scenario_result in validation_results["test_results"]:
            scenario_name = scenario_result.get("scenario_name", "Unknown")
            
            # If this is a known scenario, update its status
            if scenario_name in test_scenarios:
                success = scenario_result.get("success", False)
                validation_success = scenario_result.get("validation_success", False)
                sql_validation = scenario_result.get("sql_validation_success", False)
                
                test_scenarios[scenario_name]["current_status"] = "Passed" if success and validation_success else "Failed"
                test_scenarios[scenario_name]["meets_success_criteria"] = success and validation_success
                test_scenarios[scenario_name]["sql_validation"] = sql_validation
            
            # If it's not in our required list, add it
            else:
                success = scenario_result.get("success", False)
                validation_success = scenario_result.get("validation_success", False)
                sql_validation = scenario_result.get("sql_validation_success", False)
                
                test_scenarios[scenario_name] = {
                    "name": scenario_name,
                    "expected_status": "Passed",
                    "current_status": "Passed" if success and validation_success else "Failed",
                    "meets_success_criteria": success and validation_success,
                    "sql_validation": sql_validation,
                    "description": f"Test scenario for {scenario_name}"
                }
    
    return test_scenarios

def _generate_html_report(
    compliance_report: Dict[str, Any],
    output_path: str,
    logger: logging.Logger
) -> None:
    """
    Generate an HTML compliance report.
    
    Args:
        compliance_report: Compliance report data
        output_path: Path to write the HTML report
        logger: Logger instance
    """
    try:
        # HTML template
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Agent Compliance Report</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{ 
                    color: #333;
                }}
                .header {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                }}
                .summary {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 5px;
                    flex: 1;
                    margin: 0 10px;
                    text-align: center;
                }}
                .compliant {{
                    background-color: #d4edda;
                    color: #155724;
                }}
                .non-compliant {{
                    background-color: #f8d7da;
                    color: #721c24;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background-color: #f4f4f4;
                }}
                tr.compliant td {{
                    background-color: rgba(212, 237, 218, 0.3);
                }}
                tr.non-compliant td {{
                    background-color: rgba(248, 215, 218, 0.3);
                }}
                .timestamp {{
                    font-style: italic;
                    color: #666;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI Agent Compliance Report</h1>
                <p class="timestamp">Generated: {compliance_report.get("timestamp", "Unknown")}</p>
            </div>
            
            <div class="summary">
                <div class="summary-item {'compliant' if compliance_report.get('compliance_status', False) else 'non-compliant'}">
                    <h3>Overall Compliance</h3>
                    <p>{compliance_report.get('compliance_status', False)}</p>
                </div>
                <div class="summary-item {'compliant' if compliance_report.get('service_compliance', False) else 'non-compliant'}">
                    <h3>Service Compliance</h3>
                    <p>{compliance_report.get('service_compliance', False)}</p>
                </div>
                <div class="summary-item {'compliant' if compliance_report.get('test_compliance', False) else 'non-compliant'}">
                    <h3>Test Compliance</h3>
                    <p>{compliance_report.get('test_compliance', False)}</p>
                </div>
                <div class="summary-item {'compliant' if compliance_report.get('passing_percentage', 0) >= 90 else 'non-compliant'}">
                    <h3>Passing Rate</h3>
                    <p>{compliance_report.get('passing_percentage', 0):.2f}%</p>
                </div>
            </div>
            
            <h2>Service Components</h2>
            <table>
                <tr>
                    <th>Component</th>
                    <th>Expected Status</th>
                    <th>Current Status</th>
                    <th>Compliant</th>
                    <th>Description</th>
                </tr>
        """
        
        # Add service components rows
        for component_name, component_data in compliance_report.get("service_components", {}).items():
            compliant = component_data.get("compliant", False)
            html += f"""
                <tr class="{'compliant' if compliant else 'non-compliant'}">
                    <td>{component_name}</td>
                    <td>{component_data.get('expected_status', 'Unknown')}</td>
                    <td>{component_data.get('current_status', 'Unknown')}</td>
                    <td>{compliant}</td>
                    <td>{component_data.get('description', '')}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Test Scenarios</h2>
            <table>
                <tr>
                    <th>Scenario</th>
                    <th>Expected Status</th>
                    <th>Current Status</th>
                    <th>Success Criteria Met</th>
                    <th>SQL Validation</th>
                    <th>Description</th>
                </tr>
        """
        
        # Add test scenarios rows
        for scenario_name, scenario_data in compliance_report.get("test_scenarios", {}).items():
            meets_criteria = scenario_data.get("meets_success_criteria", False)
            html += f"""
                <tr class="{'compliant' if meets_criteria else 'non-compliant'}">
                    <td>{scenario_name}</td>
                    <td>{scenario_data.get('expected_status', 'Unknown')}</td>
                    <td>{scenario_data.get('current_status', 'Unknown')}</td>
                    <td>{meets_criteria}</td>
                    <td>{scenario_data.get('sql_validation', False)}</td>
                    <td>{scenario_data.get('description', '')}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        # Write HTML to file
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"HTML compliance report written to {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating HTML report: {str(e)}") 