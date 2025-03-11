"""
Service for managing business rules and SQL examples.
"""
import logging
import os
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RulesManager:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the rules manager."""
        self.examples_path = config["services"]["sql_generator"]["examples_path"]
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict[str, Any]:
        """
        Load all rules and examples from the data directory.
        
        This method strictly loads SQL examples only from examples.json files,
        not from individual .pgsql or .sql files.
        """
        rules = {}
        
        # Load SQL examples
        for category in os.listdir(self.examples_path):
            category_path = os.path.join(self.examples_path, category)
            if os.path.isdir(category_path):
                rules[category] = {
                    "sql_examples": [],
                    "response_rules": {}
                }
                
                # Load SQL examples only from JSON files, not from PostgreSQL files
                examples_file = os.path.join(category_path, "examples.json")
                if os.path.exists(examples_file):
                    with open(examples_file, "r") as f:
                        rules[category]["sql_examples"] = json.load(f)
                
                # Load response rules
                rules_file = os.path.join(category_path, "rules.json")
                if os.path.exists(rules_file):
                    with open(rules_file, "r") as f:
                        rules[category]["response_rules"] = json.load(f)
                        
        return rules
        
    def get_rules_and_examples(self, category: str) -> Dict[str, Any]:
        """
        Get rules and examples for a specific category.
        
        Args:
            category: The query category
            
        Returns:
            Dict containing SQL examples and response rules
        """
        if category in self.rules:
            return self.rules[category]
        else:
            logger.warning(f"No rules found for category: {category}")
            return {"sql_examples": [], "response_rules": {}} 