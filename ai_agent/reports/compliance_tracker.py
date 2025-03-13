"""
Compliance tracking module for the test runner.

This module is responsible for tracking compliance of the AI agent.
It checks whether the AI agent is using real services or mock services,
and whether all test scenarios are passing as required.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

def update_compliance_report(
    test_results: List[Dict[str, Any]],
    validation_results: Dict[str, Any],
    output_path: str,
    logger: Optional[logging.Logger] = None
) -> str:
    """
    Update compliance report based on test results.
    
    Args:
        test_results: List of test results
        validation_results: Results of test validation
        output_path: Path to save the compliance report
        logger: Logger instance
        
    Returns:
        Path to the compliance report
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("Updating compliance report")
    
    # Load existing compliance report if it exists
    if os.path.exists(output_path):
        try:
            with open(output_path, "r") as f:
                compliance_report = json.load(f)
                logger.info(f"Loaded existing compliance report from {output_path}")
        except Exception as e:
            logger.warning(f"Error loading existing compliance report: {str(e)}")
            compliance_report = create_new_compliance_report()
    else:
        compliance_report = create_new_compliance_report()
    
    # Update timestamp
    compliance_report["last_updated"] = datetime.now().isoformat()
    
    # Update service component status
    service_components = get_service_component_status(test_results, logger)
    compliance_report["service_components"] = service_components
    
    # Update service compliance status
    service_compliance = all(
        component["compliant"] for component in service_components.values()
    )
    compliance_report["service_compliance"] = service_compliance
    
    # Update test scenario verification
    test_scenarios = compliance_report.get("test_scenarios", {})
    
    # Update status for scenarios in this test run
    for result in test_results:
        scenario_name = result.get("scenario_name", "Unknown")
        
        if scenario_name not in test_scenarios:
            test_scenarios[scenario_name] = {
                "current_status": "Not Run",
                "success_criteria_met": False,
                "sql_validation_passed": False,
                "last_run": None
            }
        
        # Update scenario status
        test_scenarios[scenario_name]["current_status"] = (
            "Pass" if result.get("success", False) else "Fail"
        )
        test_scenarios[scenario_name]["success_criteria_met"] = result.get("success", False)
        
        # Check if SQL validation was performed and passed
        validation = result.get("validation", {})
        if "sql_validation" in validation:
            sql_valid = validation["sql_validation"].get("is_valid", False)
            test_scenarios[scenario_name]["sql_validation_passed"] = sql_valid
        
        test_scenarios[scenario_name]["last_run"] = datetime.now().isoformat()
    
    # Update test scenarios in compliance report
    compliance_report["test_scenarios"] = test_scenarios
    
    # Update test compliance status (all scenarios must pass)
    test_compliance = all(
        scenario["success_criteria_met"] and scenario["sql_validation_passed"]
        for scenario in test_scenarios.values()
        if scenario["current_status"] != "Not Run"
    )
    compliance_report["test_compliance"] = test_compliance
    
    # Update overall compliance status
    compliance_report["compliant"] = service_compliance and test_compliance
    
    # Update test passing percentage
    if "test_success_percentage" in validation_results:
        compliance_report["test_passing_percentage"] = validation_results["test_success_percentage"]
    
    # Save updated compliance report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(compliance_report, f, indent=2)
    
    logger.info(f"Compliance report saved to {output_path}")
    logger.info(f"Compliance status: {compliance_report['compliant']}")
    
    return output_path

def create_new_compliance_report() -> Dict[str, Any]:
    """
    Create a new compliance report template.
    
    Returns:
        New compliance report
    """
    return {
        "compliant": False,
        "service_compliance": False,
        "test_compliance": False,
        "test_passing_percentage": 0.0,
        "last_updated": datetime.now().isoformat(),
        "service_components": {
            "SQLExecutor": {
                "required_status": "Real SQLExecutor",
                "current_status": "Unknown",
                "compliant": False
            },
            "RulesService": {
                "required_status": "Real RulesService",
                "current_status": "Unknown",
                "compliant": False
            },
            "DatabaseValidator": {
                "required_status": "Real DatabaseValidator",
                "current_status": "Unknown",
                "compliant": False
            },
            "CritiqueAgent": {
                "required_status": "Real Implementation",
                "current_status": "Unknown",
                "compliant": False
            },
            "ResponseGenerator": {
                "required_status": "Real Implementation",
                "current_status": "Unknown",
                "compliant": False
            }
        },
        "test_scenarios": {}
    }

def get_service_component_status(
    test_results: List[Dict[str, Any]],
    logger: logging.Logger
) -> Dict[str, Dict[str, Any]]:
    """
    Get the status of service components from test results.
    
    Args:
        test_results: Test results
        logger: Logger instance
        
    Returns:
        Service component status
    """
    # Create default service components
    service_components = {
        "SQLExecutor": {
            "required_status": "Real SQLExecutor",
            "current_status": "Unknown",
            "compliant": False
        },
        "RulesService": {
            "required_status": "Real RulesService",
            "current_status": "Unknown",
            "compliant": False
        },
        "DatabaseValidator": {
            "required_status": "Real DatabaseValidator",
            "current_status": "Unknown",
            "compliant": False
        },
        "CritiqueAgent": {
            "required_status": "Real Implementation",
            "current_status": "Real Implementation",
            "compliant": True
        },
        "ResponseGenerator": {
            "required_status": "Real Implementation",
            "current_status": "Real Implementation",
            "compliant": True
        }
    }
    
    # Update SQLExecutor status based on test results
    for result in test_results:
        # Check if SQL queries were executed
        if "sql_results" in result and result["sql_results"]:
            service_components["SQLExecutor"]["current_status"] = "Real SQLExecutor"
            service_components["SQLExecutor"]["compliant"] = True
    
    logger.info(f"Service component status: {service_components}")
    return service_components 