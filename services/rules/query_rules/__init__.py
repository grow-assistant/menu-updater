"""
Query Rules Package

Contains rule modules for different query categories.
"""

# This file ensures that the directory is recognized as a Python package

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
    """
    Proxy function to RulesService.replace_placeholders
    
    Handles both string patterns and dictionary of patterns.
    
    Args:
        patterns: Either a single string pattern or a dictionary of patterns
        replacements: Dictionary of placeholder replacements
        
    Returns:
        Either the modified string or a dictionary of modified strings
    """
    # Handle the case where patterns is a single string
    if isinstance(patterns, str):
        result = patterns
        for placeholder, value in replacements.items():
            result = result.replace(f"{{{{${placeholder}}}}}", str(value))
        return result
    
    # If it's a dictionary, process each string in the dictionary
    if isinstance(patterns, dict):
        result = patterns.copy()
        for key, pattern in patterns.items():
            if isinstance(pattern, str):
                for placeholder, value in replacements.items():
                    pattern = pattern.replace(f"{{{{${placeholder}}}}}", str(value))
                result[key] = pattern
        return result
    
    # Fall back to returning unchanged input for other types
    return patterns

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