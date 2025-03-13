"""
SQL Example Loader for the SQL Generator Service.

This module provides functions for loading and managing SQL examples
that are used for few-shot learning in the SQL Generator.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

class SQLExampleLoader:
    """
    A class for loading SQL examples from files and providing them to the SQL Generator.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the SQL Example Loader.
        
        Args:
            config: Configuration dictionary (optional)
        """
        # Default examples directory
        default_examples_dir = "./services/sql_generator/sql_files"
        
        # Get examples directory from config if available
        if config and isinstance(config, dict):
            self.examples_dir = config.get("services", {}).get("sql_generator", {}).get("examples_dir", default_examples_dir)
        else:
            self.examples_dir = default_examples_dir
            
        self._examples_cache: Dict[str, List[Dict[str, str]]] = {}
        logger.info(f"SQLExampleLoader initialized with examples directory: {self.examples_dir}")
        
        # Verify the directory exists
        if not os.path.exists(self.examples_dir):
            logger.warning(f"Examples directory does not exist: {self.examples_dir}")
        else:
            # Log available directories for debugging
            logger.info(f"Available query types: {', '.join(os.listdir(self.examples_dir))}")
    
    def load_examples_for_query_type(self, query_type: str) -> List[Dict[str, str]]:
        """
        Load SQL examples for a specific query type.
        
        Args:
            query_type: Type of query (e.g., 'menu', 'order_history')
            
        Returns:
            List of example dictionaries containing 'query' and 'sql' keys
        """
        # Check cache first
        if query_type in self._examples_cache:
            logger.debug(f"Returning cached examples for query type: {query_type}")
            return self._examples_cache[query_type]
        
        # Build the path to the examples directory for this query type
        query_examples_dir = os.path.join(self.examples_dir, query_type)
        logger.info(f"Looking for examples in directory: {query_examples_dir}")
        
        # Check if directory exists
        if not os.path.exists(query_examples_dir):
            logger.warning(f"No examples directory found for query type: {query_type}")
            return []
        
        examples = []
        
        # Log what files exist in the directory
        all_files = os.listdir(query_examples_dir) if os.path.exists(query_examples_dir) else []
        logger.info(f"Files in {query_examples_dir}: {all_files}")
        
        # Flag to check if examples.json was found
        examples_json_found = False
        
        # Look for examples.json file first
        examples_json_path = os.path.join(query_examples_dir, "examples.json")
        if os.path.exists(examples_json_path):
            examples_json_found = True
            logger.info(f"Found examples.json at {examples_json_path}")
            try:
                with open(examples_json_path, 'r') as f:
                    file_examples = json.load(f)
                
                # Validate the examples format
                valid_examples = 0
                for example in file_examples:
                    if 'query' in example and 'sql' in example:
                        examples.append(example)
                        valid_examples += 1
                    else:
                        logger.warning(f"Invalid example in {examples_json_path}: missing 'query' or 'sql' field")
                
                logger.info(f"Loaded {valid_examples} valid examples from examples.json for {query_type}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in {examples_json_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading examples from {examples_json_path}: {str(e)}")
        
        # If no examples.json or no valid examples, try individual SQL files
        if not examples_json_found or not examples:
            logger.warning(f"No examples.json found or no valid examples for {query_type}. " 
                          f"Per updated requirements, only loading from examples.json is supported.")
            # Note: We used to fall back to individual SQL files, but this has been disabled
            # to ensure consistency with the RulesManager approach.
        
        # Cache the examples
        self._examples_cache[query_type] = examples
        
        logger.info(f"Loaded a total of {len(examples)} examples for query type: {query_type}")
        
        # Print first example for debugging if available
        if examples and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"First example query: {examples[0]['query']}")
            logger.debug(f"First example SQL: {examples[0]['sql'][:100]}...")
        
        return examples
    
    def get_formatted_examples(self, query_type: str) -> str:
        """
        Get examples formatted for inclusion in a prompt.
        
        Args:
            query_type: Type of query
            
        Returns:
            String with formatted examples
        """
        examples = self.load_examples_for_query_type(query_type)
        
        if not examples:
            logger.warning(f"No examples available for query type: {query_type}")
            return "No examples available."
        
        # Format examples for inclusion in the prompt
        formatted_examples = ""
        for i, example in enumerate(examples):
            formatted_examples += f"Example {i+1}:\n"
            formatted_examples += f"Question: {example['query']}\n"
            formatted_examples += f"SQL: {example['sql']}\n\n"
        
        logger.info(f"Formatted {len(examples)} examples for query type: {query_type}")
        return formatted_examples
    
    def clear_cache(self) -> None:
        """Clear the examples cache."""
        self._examples_cache = {}
        logger.info("Cleared SQL examples cache")

# Don't create a singleton instance here as it causes initialization issues
# Instead, let the factory or adapter create instances as needed 