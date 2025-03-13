"""
Compliance tracker module for tracking service component status and test scenario verification.

This module implements compliance tracking as specified in the AI Agent Development Plan,
including service component status tracking and test scenario verification tracking.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Initialize global state for the compliance tracker
_compliance_data = {
    "service_component_status": {
        "SQLExecutor": {"current_status": "Unknown", "required_status": "Real SQLExecutor", "compliance": False},
        "RulesService": {"current_status": "Unknown", "required_status": "Real Implementation", "compliance": False},
        "DatabaseValidator": {"current_status": "Unknown", "required_status": "Real Implementation", "compliance": False},
        "CritiqueAgent": {"current_status": "Unknown", "required_status": "Real Implementation", "compliance": False},
        "ResponseGenerator": {"current_status": "Unknown", "required_status": "Real Implementation", "compliance": False}
    },
    "test_scenario_verification": {
        "Ambiguous Request": {"current_status": "Not Run", "success_criteria_met": False, "sql_validation": False},
        "Menu Status Inquiry": {"current_status": "Not Run", "success_criteria_met": False, "sql_validation": False},
        "Category Performance": {"current_status": "Not Run", "success_criteria_met": False, "sql_validation": False},
        "Comparative Analysis": {"current_status": "Not Run", "success_criteria_met": False, "sql_validation": False},
        "Historical Performance": {"current_status": "Not Run", "success_criteria_met": False, "sql_validation": False}
    },
    "last_updated": datetime.now().isoformat(),
    "overall_compliance": False
}

def initialize_compliance_tracker(config: Dict[str, Any]) -> None:
    """
    Initialize the compliance tracker with config settings.
    
    Args:
        config: Configuration dictionary containing compliance settings
    """
    global _compliance_data
    
    # If there's an existing compliance report, load it
    compliance_report_path = config.get("compliance", {}).get("report_path")
    if compliance_report_path and os.path.exists(compliance_report_path):
        try:
            with open(compliance_report_path, 'r') as f:
                existing_data = json.load(f)
                _compliance_data.update(existing_data)
                logging.info(f"Loaded existing compliance data from {compliance_report_path}")
        except Exception as e:
            logging.error(f"Error loading existing compliance data: {str(e)}")
    
    # Update last updated timestamp
    _compliance_data["last_updated"] = datetime.now().isoformat()

def update_service_status(
    orchestrator: Any, 
    follow_up_agent: Any, 
    critique_agent: Any
) -> None:
    """
    Update the service component status based on the actual instances provided.
    
    Args:
        orchestrator: The service orchestrator instance
        follow_up_agent: The follow-up agent instance
        critique_agent: The critique agent instance
    """
    global _compliance_data
    
    # Determine SQLExecutor status
    if hasattr(orchestrator, "sql_executor"):
        sql_executor = getattr(orchestrator, "sql_executor")
        sql_executor_type = type(sql_executor).__name__
        if sql_executor_type == "SQLExecutor" or sql_executor_type == "RealSQLExecutor":
            _compliance_data["service_component_status"]["SQLExecutor"]["current_status"] = "Real SQLExecutor"
            _compliance_data["service_component_status"]["SQLExecutor"]["compliance"] = True
        else:
            _compliance_data["service_component_status"]["SQLExecutor"]["current_status"] = f"Mock: {sql_executor_type}"
            _compliance_data["service_component_status"]["SQLExecutor"]["compliance"] = False
    
    # Determine RulesService status
    if hasattr(orchestrator, "rules_service"):
        rules_service = getattr(orchestrator, "rules_service")
        rules_service_type = type(rules_service).__name__
        if rules_service_type == "RulesService" or rules_service_type == "RealRulesService":
            _compliance_data["service_component_status"]["RulesService"]["current_status"] = "Real Implementation"
            _compliance_data["service_component_status"]["RulesService"]["compliance"] = True
        else:
            _compliance_data["service_component_status"]["RulesService"]["current_status"] = f"Mock: {rules_service_type}"
            _compliance_data["service_component_status"]["RulesService"]["compliance"] = False
    
    # Determine DatabaseValidator status
    if hasattr(orchestrator, "database_validator"):
        db_validator = getattr(orchestrator, "database_validator")
        db_validator_type = type(db_validator).__name__
        if db_validator_type == "DatabaseValidator" or db_validator_type == "RealDatabaseValidator":
            _compliance_data["service_component_status"]["DatabaseValidator"]["current_status"] = "Real Implementation"
            _compliance_data["service_component_status"]["DatabaseValidator"]["compliance"] = True
        else:
            _compliance_data["service_component_status"]["DatabaseValidator"]["current_status"] = f"Mock: {db_validator_type}"
            _compliance_data["service_component_status"]["DatabaseValidator"]["compliance"] = False
    
    # Determine CritiqueAgent status
    critique_agent_type = type(critique_agent).__name__
    if critique_agent_type == "CritiqueAgent" or critique_agent_type == "RealCritiqueAgent":
        _compliance_data["service_component_status"]["CritiqueAgent"]["current_status"] = "Real Implementation"
        _compliance_data["service_component_status"]["CritiqueAgent"]["compliance"] = True
    else:
        _compliance_data["service_component_status"]["CritiqueAgent"]["current_status"] = f"Mock: {critique_agent_type}"
        _compliance_data["service_component_status"]["CritiqueAgent"]["compliance"] = False
    
    # Determine ResponseGenerator status
    if hasattr(orchestrator, "response_generator"):
        response_generator = getattr(orchestrator, "response_generator")
        response_generator_type = type(response_generator).__name__
        if response_generator_type == "ResponseGenerator" or response_generator_type == "RealResponseGenerator":
            _compliance_data["service_component_status"]["ResponseGenerator"]["current_status"] = "Real Implementation"
            _compliance_data["service_component_status"]["ResponseGenerator"]["compliance"] = True
        else:
            _compliance_data["service_component_status"]["ResponseGenerator"]["current_status"] = f"Mock: {response_generator_type}"
            _compliance_data["service_component_status"]["ResponseGenerator"]["compliance"] = False
    
    # Update last updated timestamp
    _compliance_data["last_updated"] = datetime.now().isoformat()
    
    # Update overall compliance
    update_overall_compliance()

def update_test_scenario_status(
    scenario_name: str,
    success: bool,
    sql_validation_passed: bool,
    phrase_validation_passed: bool
) -> None:
    """
    Update the test scenario verification status.
    
    Args:
        scenario_name: Name of the test scenario
        success: Whether the test scenario was successful
        sql_validation_passed: Whether SQL validation passed
        phrase_validation_passed: Whether phrase validation passed
    """
    global _compliance_data
    
    # Normalize scenario name to match the ones in the compliance tracker
    normalized_name = None
    for key in _compliance_data["test_scenario_verification"].keys():
        if scenario_name.lower() in key.lower() or key.lower() in scenario_name.lower():
            normalized_name = key
            break
    
    # If no matching scenario name was found, use the original
    if normalized_name is None:
        normalized_name = scenario_name
    
    # Add the scenario to the tracker if it doesn't exist
    if normalized_name not in _compliance_data["test_scenario_verification"]:
        _compliance_data["test_scenario_verification"][normalized_name] = {
            "current_status": "Not Run",
            "success_criteria_met": False,
            "sql_validation": False
        }
    
    # Update the scenario status
    _compliance_data["test_scenario_verification"][normalized_name]["current_status"] = "Passing" if success else "Failing"
    _compliance_data["test_scenario_verification"][normalized_name]["success_criteria_met"] = success
    _compliance_data["test_scenario_verification"][normalized_name]["sql_validation"] = sql_validation_passed
    _compliance_data["test_scenario_verification"][normalized_name]["phrase_validation"] = phrase_validation_passed
    
    # Update last updated timestamp
    _compliance_data["last_updated"] = datetime.now().isoformat()
    
    # Update overall compliance
    update_overall_compliance()

def update_overall_compliance() -> None:
    """
    Update the overall compliance status based on service status and test verification.
    """
    global _compliance_data
    
    # Check service component compliance
    service_compliance = all(_compliance_data["service_component_status"][component]["compliance"] 
                          for component in _compliance_data["service_component_status"])
    
    # Check test scenario compliance - at least 90% of tests must be passing
    scenario_statuses = [scenario["success_criteria_met"] and scenario["sql_validation"] 
                        for scenario in _compliance_data["test_scenario_verification"].values()]
    
    if not scenario_statuses:
        test_compliance = False
    else:
        passing_rate = sum(1 for status in scenario_statuses if status) / len(scenario_statuses)
        test_compliance = passing_rate >= 0.9  # 90% passing threshold
    
    # Update overall compliance
    _compliance_data["overall_compliance"] = service_compliance and test_compliance
    _compliance_data["service_compliance"] = service_compliance
    _compliance_data["test_compliance"] = test_compliance
    _compliance_data["test_passing_rate"] = passing_rate if scenario_statuses else 0.0

def get_compliance_data() -> Dict[str, Any]:
    """
    Get the current compliance tracking data.
    
    Returns:
        Dict containing the compliance tracking data
    """
    return _compliance_data.copy()

def save_compliance_data(output_path: str, logger: logging.Logger) -> str:
    """
    Save the compliance tracking data to a JSON file.
    
    Args:
        output_path: Path to save the compliance data
        logger: Logger instance
        
    Returns:
        Path to the saved compliance data file
    """
    global _compliance_data
    
    # Update timestamp before saving
    _compliance_data["last_updated"] = datetime.now().isoformat()
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the compliance data
    try:
        with open(output_path, 'w') as f:
            json.dump(_compliance_data, f, indent=2)
        logger.info(f"Compliance tracking data saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error saving compliance tracking data: {str(e)}")
        # Save to a fallback location
        fallback_path = os.path.join(os.getcwd(), "compliance_data.json")
        try:
            with open(fallback_path, 'w') as f:
                json.dump(_compliance_data, f, indent=2)
            logger.info(f"Compliance tracking data saved to fallback location: {fallback_path}")
            return fallback_path
        except Exception as e2:
            logger.error(f"Error saving compliance tracking data to fallback location: {str(e2)}")
            return "" 