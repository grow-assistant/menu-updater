"""
Test context module for loading and processing test scenarios.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Define the directory where test scenarios are stored
TEST_SCENARIOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_scenarios")

def load_test_scenario(scenario_path: str, logger: logging.Logger) -> Dict[str, Any]:
    """
    Load a test scenario from a JSON file.
    
    Args:
        scenario_path: Path to the scenario JSON file or just the scenario name
        logger: Logger instance
        
    Returns:
        Dict containing the scenario data
    """
    # Check if scenario_path is a full path or just a scenario name
    if not os.path.isfile(scenario_path):
        # Try to find the scenario in the test scenarios directory
        # First check if it already has a .json extension
        if not scenario_path.endswith('.json'):
            full_path = os.path.join(TEST_SCENARIOS_DIR, f"{scenario_path}.json")
        else:
            full_path = os.path.join(TEST_SCENARIOS_DIR, scenario_path)
        
        if os.path.isfile(full_path):
            scenario_path = full_path
        else:
            # Try to find a file that starts with the scenario name
            for filename in os.listdir(TEST_SCENARIOS_DIR):
                if filename.startswith(scenario_path) and filename.endswith('.json'):
                    scenario_path = os.path.join(TEST_SCENARIOS_DIR, filename)
                    break
    
    logger.info(f"Loading test scenario from {scenario_path}")
    
    try:
        with open(scenario_path, 'r') as f:
            scenario_data = json.load(f)
        
        # Ensure scenario has a name
        if "name" in scenario_data and not "scenario_name" in scenario_data:
            scenario_data["scenario_name"] = scenario_data["name"]
        
        # Handle mapping between field names if needed
        if "initial_query_hints" in scenario_data and not "user_input" in scenario_data:
            # Map initial_query_hints to user_input
            if isinstance(scenario_data["initial_query_hints"], list):
                # Join list of hints into a single string
                scenario_data["user_input"] = " ".join(scenario_data["initial_query_hints"])
            else:
                scenario_data["user_input"] = scenario_data["initial_query_hints"]
        
        # Map success_conditions to required_phrases if needed
        if "success_conditions" in scenario_data and not "required_phrases" in scenario_data:
            if isinstance(scenario_data["success_conditions"], list):
                scenario_data["required_phrases"] = scenario_data["success_conditions"]
            elif isinstance(scenario_data["success_conditions"], dict) and "contains_phrases" in scenario_data["success_conditions"]:
                scenario_data["required_phrases"] = scenario_data["success_conditions"]["contains_phrases"]
        
        # Set validation requirements if not present
        if "validation_requirements" not in scenario_data:
            scenario_data["validation_requirements"] = {
                "sql_validation": True,
                "phrase_validation": True
            }
        
        # Set performance target if not present
        if "performance_target" not in scenario_data:
            scenario_data["performance_target"] = 5000  # Default 5000ms
        
        # Ensure test_steps exists, creating it based on user_input if not present
        if "test_steps" not in scenario_data:
            user_input = scenario_data.get("user_input", "")
            scenario_data["test_steps"] = [{"input": user_input, "expected_type": "response"}]
        
        logger.info(f"Loaded scenario {scenario_data.get('scenario_name', 'Unnamed')}")
        return scenario_data
        
    except Exception as e:
        logger.error(f"Error loading test scenario: {str(e)}")
        raise

def load_all_test_scenarios(logger: logging.Logger) -> Dict[str, Dict[str, Any]]:
    """
    Load all test scenarios from the test scenarios directory.
    
    Args:
        logger: Logger instance
        
    Returns:
        Dict mapping scenario names to scenario data
    """
    test_scenarios = {}
    
    if not os.path.exists(TEST_SCENARIOS_DIR):
        logger.warning(f"Test scenarios directory not found: {TEST_SCENARIOS_DIR}")
        return test_scenarios
    
    # Load all JSON files in the test scenarios directory
    for filename in os.listdir(TEST_SCENARIOS_DIR):
        if filename.lower().endswith(".json"):
            scenario_name = os.path.splitext(filename)[0]
            try:
                scenario_path = os.path.join(TEST_SCENARIOS_DIR, filename)
                scenario_data = load_test_scenario(scenario_path, logger)
                test_scenarios[scenario_name] = scenario_data
            except Exception as e:
                logger.error(f"Error loading test scenario {filename}: {str(e)}")
    
    logger.info(f"Loaded {len(test_scenarios)} test scenarios")
    return test_scenarios

def build_test_context(
    scenario_name: str,
    scenario_data: Dict[str, Any],
    validation_config: Dict[str, Any] = None,
    logger: logging.Logger = None
) -> Dict[str, Any]:
    """
    Build a test context for a test scenario.
    
    Args:
        scenario_name: Name of the scenario
        scenario_data: Dictionary containing the scenario data
        validation_config: Dictionary containing validation configuration
        logger: Logger instance
        
    Returns:
        Dictionary containing the test context
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    test_context = {}
    
    try:
        # If scenario_data is a path, load it first
        if isinstance(scenario_data, str):
            scenario_data = load_test_scenario(scenario_data, logger)
        
        # Extract intent to determine query type
        query_type = map_intent_to_query_type(scenario_name)
        
        # Extract expected results
        expected_results = get_expected_results(scenario_data)
        
        # Build the test context
        test_context = {
            "scenario_name": scenario_name,
            "query_type": query_type,
            "user_input": scenario_data.get("user_input", ""),
            "expected_results": expected_results,
            "validation": {
                "sql_validation": validation_config.get("sql_validation", True) if validation_config else True,
                "phrase_validation": validation_config.get("validate_phrases", True) if validation_config else True,
                "required_phrases": scenario_data.get("required_phrases", []),
                "block_invalid": validation_config.get("block_invalid", True) if validation_config else True
            },
            "max_turns": scenario_data.get("max_turns", 3),
            "performance_target": scenario_data.get("performance_target", 5000)  # in milliseconds
        }
        
        return test_context
    except Exception as e:
        logger.error(f"Error building test context: {str(e)}")
        raise

def map_intent_to_query_type(intent):
    """
    Map an intent to a query type.
    
    Args:
        intent: Intent string
        
    Returns:
        str: Query type
    """
    intent_lower = intent.lower()
    
    # Define mapping of intents to query types
    mapping = {
        "menu": "menu_query",
        "availability": "availability_query",
        "price": "price_query",
        "reservation": "reservation_query",
        "hours": "hours_query",
        "status": "status_query",
        "ambiguous": "clarification_query"
    }
    
    # Find matching query type
    for key, query_type in mapping.items():
        if key in intent_lower:
            return query_type
    
    # Default to generic query
    return "information_query"

def get_expected_results(scenario_data):
    """
    Get expected results from a test scenario.
    
    Args:
        scenario_data: Test scenario data
        
    Returns:
        dict: Expected results
    """
    expected = {
        "expected_sql_pattern": scenario_data.get("expected_sql_pattern", None),
        "expected_tables": scenario_data.get("expected_tables", []),
        "expected_response_contains": scenario_data.get("expected_response_contains", []),
        "expected_response_type": scenario_data.get("expected_response_type", "information"),
        "expected_clarification": scenario_data.get("is_ambiguous", False)
    }
    
    return expected 