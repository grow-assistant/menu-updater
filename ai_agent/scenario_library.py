"""
Scenario Library for AI Testing

This module provides the ScenarioLibrary class and related utilities for managing
test scenarios for the AI testing agent. It includes functionality for organizing,
prioritizing, and generating test scenarios.
"""

import os
import json
import logging
import random
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Default categories of test scenarios
SCENARIO_CATEGORIES = {
    'menu_query': {
        'description': 'Scenarios focused on menu inquiries and item information',
        'priority': 'high',
        'tags': ['menu', 'food', 'price', 'ingredients', 'options']
    },
    'order_history': {
        'description': 'Scenarios related to past order inquiries',
        'priority': 'medium',
        'tags': ['history', 'orders', 'past', 'previous', 'receipt']
    },
    'recommendations': {
        'description': 'Scenarios asking for personalized recommendations',
        'priority': 'medium',
        'tags': ['recommend', 'suggest', 'best', 'popular', 'favorite']
    },
    'edge_cases': {
        'description': 'Unusual or boundary scenarios to test robustness',
        'priority': 'high',
        'tags': ['unusual', 'edge', 'corner', 'rare', 'boundary']
    },
    'error_recovery': {
        'description': 'Scenarios to test error handling and recovery',
        'priority': 'high',
        'tags': ['error', 'mistake', 'recover', 'correction', 'misunderstanding']
    },
    'multi_turn': {
        'description': 'Complex scenarios requiring multiple conversation turns',
        'priority': 'medium',
        'tags': ['conversation', 'multi-turn', 'complex', 'context', 'follow-up']
    },
    'special_requests': {
        'description': 'Scenarios involving special dietary needs or customizations',
        'priority': 'low',
        'tags': ['special', 'dietary', 'allergy', 'customize', 'substitute']
    }
}

# Default template for a test scenario
DEFAULT_SCENARIO_TEMPLATE = {
    "name": "",
    "category": "",
    "description": "",
    "priority": "medium",  # high, medium, or low
    "tags": [],
    "context": {
        "user_persona": "casual_diner",
        "restaurant_context": "Standard menu and operating hours"
    },
    "initial_query_hints": [],
    "expected_entities": [],
    "success_conditions": [],
    "termination_phrases": [],
    "max_turns": 5,
    "validation_requirements": {
        "database_validation": True,
        "sentiment_analysis": False,
        "response_time_threshold": 5.0  # seconds
    },
    "created_at": "",
    "last_modified": "",
    "test_history": []
}


class ScenarioLibrary:
    """Manages a library of test scenarios for the AI testing agent."""
    
    def __init__(self, scenarios_dir: str = "test_scenarios"):
        """Initialize the scenario library.
        
        Args:
            scenarios_dir: Directory path for storing scenario files
        """
        self.scenarios_dir = scenarios_dir
        self.scenarios = {}
        self.categories = SCENARIO_CATEGORIES.copy()
        
        os.makedirs(scenarios_dir, exist_ok=True)
        self._load_scenarios()
        logger.info(f"Initialized ScenarioLibrary with {len(self.scenarios)} scenarios")
    
    def _load_scenarios(self) -> None:
        """Load all scenario files from the scenarios directory."""
        scenario_files = Path(self.scenarios_dir).glob("*.json")
        for file_path in scenario_files:
            try:
                with open(file_path, 'r') as f:
                    scenario = json.load(f)
                    if self._validate_scenario(scenario):
                        self.scenarios[scenario["name"]] = scenario
                        logger.debug(f"Loaded scenario: {scenario['name']}")
                    else:
                        logger.warning(f"Invalid scenario file: {file_path}")
            except Exception as e:
                logger.error(f"Error loading scenario file {file_path}: {str(e)}")
    
    def _validate_scenario(self, scenario: Dict[str, Any]) -> bool:
        """Validate that a scenario has all required fields.
        
        Args:
            scenario: The scenario dictionary to validate
            
        Returns:
            True if the scenario is valid, False otherwise
        """
        required_fields = ["name", "category", "description", "context", "max_turns"]
        return all(field in scenario for field in required_fields)
    
    def get_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a scenario by name.
        
        Args:
            name: The name of the scenario to retrieve
            
        Returns:
            The scenario dictionary or None if not found
        """
        return self.scenarios.get(name)
    
    def get_all_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Get all scenarios.
        
        Returns:
            Dictionary of all scenarios
        """
        return self.scenarios
    
    def get_scenarios_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all scenarios in a specific category.
        
        Args:
            category: The category to filter by
            
        Returns:
            List of scenarios in the specified category
        """
        return [s for s in self.scenarios.values() if s.get("category") == category]
    
    def get_scenarios_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all scenarios with a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            List of scenarios with the specified tag
        """
        return [s for s in self.scenarios.values() if tag in s.get("tags", [])]
    
    def get_scenarios_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get all scenarios with a specific priority.
        
        Args:
            priority: The priority to filter by ('high', 'medium', or 'low')
            
        Returns:
            List of scenarios with the specified priority
        """
        return [s for s in self.scenarios.values() if s.get("priority") == priority]
    
    def add_scenario(self, scenario: Dict[str, Any], save_to_file: bool = True) -> bool:
        """Add a new scenario to the library.
        
        Args:
            scenario: The scenario to add
            save_to_file: Whether to save the scenario to a file
            
        Returns:
            True if successful, False otherwise
        """
        # Fill in missing fields with defaults
        now = datetime.now().isoformat()
        template = DEFAULT_SCENARIO_TEMPLATE.copy()
        template["created_at"] = now
        template["last_modified"] = now
        
        for key, value in template.items():
            if key not in scenario:
                scenario[key] = value
                
        # Ensure name is unique
        if scenario["name"] in self.scenarios:
            logger.warning(f"Scenario name '{scenario['name']}' already exists")
            return False
            
        # Validate and add
        if self._validate_scenario(scenario):
            self.scenarios[scenario["name"]] = scenario
            if save_to_file:
                self._save_scenario_to_file(scenario)
            logger.info(f"Added new scenario: {scenario['name']}")
            return True
        else:
            logger.warning(f"Invalid scenario: {scenario.get('name', 'unnamed')}")
            return False
    
    def update_scenario(self, name: str, updates: Dict[str, Any], save_to_file: bool = True) -> bool:
        """Update an existing scenario.
        
        Args:
            name: The name of the scenario to update
            updates: Dictionary of fields to update
            save_to_file: Whether to save the updated scenario to a file
            
        Returns:
            True if successful, False otherwise
        """
        if name not in self.scenarios:
            logger.warning(f"Scenario '{name}' not found")
            return False
            
        scenario = self.scenarios[name]
        for key, value in updates.items():
            if key in scenario:
                scenario[key] = value
                
        scenario["last_modified"] = datetime.now().isoformat()
        
        if save_to_file:
            self._save_scenario_to_file(scenario)
            
        logger.info(f"Updated scenario: {name}")
        return True
    
    def delete_scenario(self, name: str, delete_file: bool = True) -> bool:
        """Delete a scenario from the library.
        
        Args:
            name: The name of the scenario to delete
            delete_file: Whether to delete the scenario file
            
        Returns:
            True if successful, False otherwise
        """
        if name not in self.scenarios:
            logger.warning(f"Scenario '{name}' not found")
            return False
            
        if delete_file:
            try:
                file_path = os.path.join(self.scenarios_dir, f"{name}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting scenario file for '{name}': {str(e)}")
                
        del self.scenarios[name]
        logger.info(f"Deleted scenario: {name}")
        return True
    
    def _save_scenario_to_file(self, scenario: Dict[str, Any]) -> bool:
        """Save a scenario to a JSON file.
        
        Args:
            scenario: The scenario to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.scenarios_dir, f"{scenario['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(scenario, f, indent=2)
            logger.debug(f"Saved scenario to file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving scenario file: {str(e)}")
            return False
    
    def add_test_result(self, scenario_name: str, result: Dict[str, Any], save_to_file: bool = True) -> bool:
        """Add a test result to a scenario's history.
        
        Args:
            scenario_name: The name of the scenario
            result: The test result to add
            save_to_file: Whether to save the updated scenario to a file
            
        Returns:
            True if successful, False otherwise
        """
        if scenario_name not in self.scenarios:
            logger.warning(f"Scenario '{scenario_name}' not found")
            return False
            
        scenario = self.scenarios[scenario_name]
        if "test_history" not in scenario:
            scenario["test_history"] = []
            
        # Add timestamp if not present
        if "timestamp" not in result:
            result["timestamp"] = datetime.now().isoformat()
            
        scenario["test_history"].append(result)
        scenario["last_modified"] = datetime.now().isoformat()
        
        if save_to_file:
            self._save_scenario_to_file(scenario)
            
        logger.info(f"Added test result to scenario: {scenario_name}")
        return True
    
    def add_category(self, name: str, description: str, priority: str = "medium", tags: List[str] = None) -> bool:
        """Add a new scenario category.
        
        Args:
            name: The name of the category
            description: Description of the category
            priority: Default priority for scenarios in this category
            tags: List of related tags
            
        Returns:
            True if successful, False otherwise
        """
        if name in self.categories:
            logger.warning(f"Category '{name}' already exists")
            return False
            
        self.categories[name] = {
            "description": description,
            "priority": priority,
            "tags": tags or []
        }
        
        logger.info(f"Added new category: {name}")
        return True
    
    def get_random_scenario(self, category: Optional[str] = None, 
                         tag: Optional[str] = None, 
                         priority: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a random scenario, optionally filtered by criteria.
        
        Args:
            category: Filter by category
            tag: Filter by tag
            priority: Filter by priority
            
        Returns:
            A random scenario meeting the criteria, or None if none found
        """
        candidates = list(self.scenarios.values())
        
        if category:
            candidates = [s for s in candidates if s.get("category") == category]
            
        if tag:
            candidates = [s for s in candidates if tag in s.get("tags", [])]
            
        if priority:
            candidates = [s for s in candidates if s.get("priority") == priority]
            
        if not candidates:
            return None
            
        return random.choice(candidates)
    
    def export_scenarios(self, output_file: str) -> bool:
        """Export all scenarios to a single JSON file.
        
        Args:
            output_file: Path to the output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                json.dump({
                    "scenarios": list(self.scenarios.values()),
                    "categories": self.categories,
                    "exported_at": datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f"Exported scenarios to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting scenarios: {str(e)}")
            return False
    
    def import_scenarios(self, input_file: str, overwrite: bool = False) -> int:
        """Import scenarios from a JSON file.
        
        Args:
            input_file: Path to the input file
            overwrite: Whether to overwrite existing scenarios
            
        Returns:
            Number of scenarios imported
        """
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
                
            if "scenarios" not in data:
                logger.error("Invalid import file: missing 'scenarios' key")
                return 0
                
            imported = 0
            for scenario in data["scenarios"]:
                if scenario["name"] not in self.scenarios or overwrite:
                    if self.add_scenario(scenario):
                        imported += 1
                        
            if "categories" in data:
                for name, category in data["categories"].items():
                    if name not in self.categories:
                        self.categories[name] = category
                        
            logger.info(f"Imported {imported} scenarios from {input_file}")
            return imported
        except Exception as e:
            logger.error(f"Error importing scenarios: {str(e)}")
            return 0 