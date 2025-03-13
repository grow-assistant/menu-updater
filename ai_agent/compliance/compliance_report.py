"""
Compliance Tracking Report Generator

This module implements compliance tracking report generation as specified in the 
AI Agent Development Plan, including service component status and test scenario 
verification tracking.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_agent.compliance.compliance_tracker import get_compliance_data, save_compliance_data


def generate_compliance_tracking_report(
    report_path: Optional[str],
    config: Dict[str, Any],
    logger: logging.Logger
) -> str:
    """
    Generate a compliance tracking report based on current compliance data.
    
    Args:
        report_path: Path to save the compliance report, or None to use default
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        Path to the generated compliance report
    """
    logger.info("Generating compliance tracking report")
    
    # Get compliance data
    compliance_data = get_compliance_data()
    
    # If no report path provided, use a default
    if not report_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = config.get("output_dir", os.getcwd())
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"{timestamp}_compliance_report.json")
    
    # Save compliance data to the report path
    report_path = save_compliance_data(report_path, logger)
    
    # Generate an HTML version of the report
    html_report_path = generate_html_compliance_tracking_report(report_path, compliance_data, logger)
    
    return report_path


def generate_html_compliance_tracking_report(
    json_report_path: str,
    compliance_data: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> str:
    """
    Generate an HTML version of the compliance tracking report.
    
    Args:
        json_report_path: Path to the JSON compliance report
        compliance_data: Compliance data dictionary, or None to load from json_report_path
        logger: Logger instance, or None
        
    Returns:
        Path to the generated HTML compliance report
    """
    if logger:
        logger.info("Generating HTML compliance tracking report")
    
    # If compliance data not provided, load from the JSON report
    if not compliance_data:
        try:
            with open(json_report_path, 'r') as f:
                compliance_data = json.load(f)
        except Exception as e:
            if logger:
                logger.error(f"Error loading compliance data from {json_report_path}: {str(e)}")
            return ""
    
    # Create HTML file path
    html_report_path = os.path.splitext(json_report_path)[0] + ".html"
    
    # Create HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Compliance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .section {{ background-color: #fff; padding: 15px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; }}
        .compliant {{ color: green; }}
        .non-compliant {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>AI Agent Compliance Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Last Updated:</strong> {compliance_data.get("last_updated", "Unknown")}</p>
        <p><strong>Overall Compliance:</strong> <span class="{'compliant' if compliance_data.get('overall_compliance', False) else 'non-compliant'}">{compliance_data.get('overall_compliance', False)}</span></p>
        <p><strong>Service Compliance:</strong> <span class="{'compliant' if compliance_data.get('service_compliance', False) else 'non-compliant'}">{compliance_data.get('service_compliance', False)}</span></p>
        <p><strong>Test Compliance:</strong> <span class="{'compliant' if compliance_data.get('test_compliance', False) else 'non-compliant'}">{compliance_data.get('test_compliance', False)}</span></p>
        <p><strong>Test Passing Rate:</strong> {compliance_data.get('test_passing_rate', 0.0) * 100:.1f}%</p>
    </div>
    
    <div class="section">
        <h2>Service Component Status</h2>
        <table>
            <tr>
                <th>Service Component</th>
                <th>Current Status</th>
                <th>Required Status</th>
                <th>Compliance</th>
            </tr>
"""
    
    # Add service component status rows
    for component, status in compliance_data.get("service_component_status", {}).items():
        compliance_class = "compliant" if status.get("compliance", False) else "non-compliant"
        html_content += f"""
            <tr>
                <td>{component}</td>
                <td>{status.get("current_status", "Unknown")}</td>
                <td>{status.get("required_status", "Unknown")}</td>
                <td class="{compliance_class}">{status.get("compliance", False)}</td>
            </tr>
"""
    
    html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Test Scenario Verification</h2>
        <table>
            <tr>
                <th>Test Scenario</th>
                <th>Current Status</th>
                <th>Success Criteria Met</th>
                <th>SQL Validation</th>
                <th>Phrase Validation</th>
            </tr>
"""
    
    # Add test scenario verification rows
    for scenario, status in compliance_data.get("test_scenario_verification", {}).items():
        success_class = "compliant" if status.get("success_criteria_met", False) else "non-compliant"
        sql_class = "compliant" if status.get("sql_validation", False) else "non-compliant"
        phrase_class = "compliant" if status.get("phrase_validation", False) else "non-compliant"
        
        html_content += f"""
            <tr>
                <td>{scenario}</td>
                <td>{status.get("current_status", "Not Run")}</td>
                <td class="{success_class}">{status.get("success_criteria_met", False)}</td>
                <td class="{sql_class}">{status.get("sql_validation", False)}</td>
                <td class="{phrase_class}">{status.get("phrase_validation", False)}</td>
            </tr>
"""
    
    html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Compliance Requirements</h2>
        <ul>
            <li><strong>Zero Tolerance for Mock Services:</strong> All services must be implemented using real, production-ready code.</li>
            <li><strong>Mandatory Test Success:</strong> Minimum passing rate of 90% across all test scenarios.</li>
            <li><strong>100% SQL Validation:</strong> Every response must be fully supported by and directly traceable to SQL query results.</li>
            <li><strong>Response Format Compliance:</strong> All responses must adhere to the required format and include mandated phrases.</li>
        </ul>
    </div>
</body>
</html>
"""
    
    # Save HTML report
    try:
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        if logger:
            logger.info(f"HTML compliance tracking report saved to {html_report_path}")
        return html_report_path
    except Exception as e:
        if logger:
            logger.error(f"Error saving HTML compliance tracking report: {str(e)}")
        return "" 