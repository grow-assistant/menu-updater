"""
Query-specific rules for the Swoop AI application.

This package contains rule sets for different types of queries.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Import utility functions from rules_service to make them available to rule modules
from services.rules.rules_service import RulesService

# Forward the utility functions needed by query rules modules
def load_sql_patterns_from_directory(directory, file_to_pattern_map, default_patterns=None):
    """Proxy function to RulesService.load_sql_patterns_from_directory"""
    # This is a simple forwarding implementation that will be replaced at runtime
    # with the actual method from the RulesService instance
    return {}

def replace_placeholders(patterns, replacements):
    """Proxy function to RulesService.replace_placeholders"""
    # This is a simple forwarding implementation that will be replaced at runtime
    # with the actual method from the RulesService instance
    return patterns.copy()

def load_all_sql_files_from_directory(directory_name: str) -> Dict[str, str]:
    """
    Proxy function to RulesService.load_all_sql_files_from_directory
    
    This will be replaced at runtime with the actual method from the RulesService instance.
    
    Args:
        directory_name: Name of the directory to load SQL files from
        
    Returns:
        Dictionary mapping file names (without extension) to SQL content
    """
    # This is a simple forwarding implementation that will be replaced at runtime
    # with the actual method from the RulesService instance
    return {} 