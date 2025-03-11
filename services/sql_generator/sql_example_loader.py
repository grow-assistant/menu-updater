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
    
    def __init__(self, examples_dir: str = "./services/sql_generator/sql_files"):
        """
        Initialize the SQL Example Loader.
        
        Args:
            examples_dir: Directory path where SQL examples are stored
        """
        self.examples_dir = examples_dir
        self._examples_cache: Dict[str, List[Dict[str, str]]] = {}
        logger.info(f"SQLExampleLoader initialized with examples directory: {examples_dir}")
    
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
        logger.info(f"Files in {query_examples_dir}: {os.listdir(query_examples_dir) if os.path.exists(query_examples_dir) else 'directory not found'}")
        
        # Look for JSON files containing examples
        for filename in os.listdir(query_examples_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(query_examples_dir, filename)
                logger.info(f"Processing JSON example file: {file_path}")
                try:
                    with open(file_path, 'r') as f:
                        file_examples = json.load(f)
                        
                    # Validate the examples format
                    for example in file_examples:
                        if 'query' in example and 'sql' in example:
                            examples.append(example)
                            logger.debug(f"Added example query: {example['query'][:30]}...")
                        else:
                            logger.warning(f"Invalid example in {file_path}: {example}")
                            
                except Exception as e:
                    logger.error(f"Error loading examples from {file_path}: {str(e)}")
        
        # Cache the examples
        self._examples_cache[query_type] = examples
        
        logger.info(f"Loaded {len(examples)} examples for query type: {query_type}")
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
            return "No examples available."
        
        # Format examples for inclusion in the prompt
        formatted_examples = ""
        for i, example in enumerate(examples):
            formatted_examples += f"Example {i+1}:\n"
            formatted_examples += f"Question: {example['query']}\n"
            formatted_examples += f"SQL: {example['sql']}\n\n"
        
        return formatted_examples
    
    def clear_cache(self) -> None:
        """Clear the examples cache."""
        self._examples_cache = {}
        logger.info("Cleared SQL examples cache")


# Singleton instance
sql_example_loader = SQLExampleLoader() 