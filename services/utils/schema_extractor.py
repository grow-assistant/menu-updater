"""
Utility to extract database schema information from query rules files.

This module provides functionality to analyze a Python module containing
database schema definitions and convert them to YAML format.
"""

import re
from pathlib import Path
import yaml
from typing import Dict, Any, List, Tuple

from services.utils.conversion_utils import import_module_from_file


def extract_schema_from_module(module: Any) -> Dict[str, Dict]:
    """
    Extract database schema information from a module.
    
    Args:
        module: The module containing schema definitions
        
    Returns:
        A dictionary containing the extracted schema information
    """
    schema = {"tables": {}}
    
    # Look for schema-related attributes in the module
    for name in dir(module):
        # Extract table schemas
        if name.upper() in ("DB_SCHEMA", "SCHEMA", "TABLE_SCHEMA"):
            if isinstance(getattr(module, name), dict):
                schema_dict = getattr(module, name)
                for table_name, table_info in schema_dict.items():
                    schema["tables"][table_name] = table_info
    
    # If there's a TABLE_COLUMNS or COLUMNS dictionary, add that info
    for name in dir(module):
        if name.upper().endswith("_COLUMNS") or name.upper() == "COLUMNS":
            columns_dict = getattr(module, name)
            if isinstance(columns_dict, dict):
                # If it's a mapping of table name to columns
                for table, columns in columns_dict.items():
                    if table not in schema["tables"]:
                        schema["tables"][table] = {}
                    
                    if "columns" not in schema["tables"][table]:
                        schema["tables"][table]["columns"] = {}
                    
                    schema["tables"][table]["columns"].update(columns)
    
    # Look for relationship information
    for name in dir(module):
        if "RELATION" in name.upper() or "FOREIGN_KEY" in name.upper():
            relations = getattr(module, name)
            if isinstance(relations, (list, tuple)):
                for rel in relations:
                    _add_relationship_to_schema(schema, rel)
            elif isinstance(relations, dict):
                for table, rels in relations.items():
                    if isinstance(rels, (list, tuple)):
                        for rel in rels:
                            _add_relationship_to_schema(schema, rel, table)
    
    return schema


def _add_relationship_to_schema(schema: Dict, relationship: str, table_name: str = None) -> None:
    """
    Add a relationship definition to the schema dictionary.
    
    Args:
        schema: The schema dictionary to update
        relationship: The relationship definition string
        table_name: Optional table name if not included in the relationship string
    """
    # If table name is provided, add relationship to that table
    if table_name and table_name in schema["tables"]:
        if "relationships" not in schema["tables"][table_name]:
            schema["tables"][table_name]["relationships"] = []
        
        schema["tables"][table_name]["relationships"].append(relationship)
    else:
        # Try to extract table name from the relationship string
        match = re.search(r'FOREIGN KEY \((\w+)\)', relationship)
        if match:
            fk_column = match.group(1)
            # Look for tables with this column
            for table, info in schema["tables"].items():
                if "columns" in info and fk_column in info["columns"]:
                    if "relationships" not in info:
                        info["relationships"] = []
                    
                    info["relationships"].append(relationship)
                    break


def extract_schema_from_file(py_file: str) -> Dict[str, Dict]:
    """
    Extract schema information from a Python file.
    
    Args:
        py_file: Path to the Python file containing schema definitions
        
    Returns:
        A dictionary containing the extracted schema information
    """
    module = import_module_from_file(py_file)
    return extract_schema_from_module(module)


def extract_and_save_schema(py_file: str, yaml_file: str) -> None:
    """
    Extract schema from a Python file and save it as YAML.
    
    Args:
        py_file: Path to the Python file containing schema definitions
        yaml_file: Path where the YAML file should be written
    """
    schema = extract_schema_from_file(py_file)
    
    # Create directory if it doesn't exist
    yaml_path = Path(yaml_file)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to YAML file
    with open(yaml_path, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
    
    print(f"Successfully extracted schema from {py_file} and saved to {yaml_file}")


def extract_rules_from_file(py_file: str) -> Dict[str, Any]:
    """
    Extract query rules from a Python file.
    
    Args:
        py_file: Path to the Python file containing query rules
        
    Returns:
        A dictionary containing the extracted rules
    """
    module = import_module_from_file(py_file)
    rules = {"rules": {}}
    
    # Look for rules-related dictionaries
    for name in dir(module):
        if "RULE" in name.upper() and isinstance(getattr(module, name), dict):
            rules_dict = getattr(module, name)
            rules["rules"].update(rules_dict)
    
    # Look for pattern files mapping
    pattern_files = {}
    for name in dir(module):
        if name.upper() in ("PATTERN_FILES", "SQL_FILES", "QUERY_FILES") and isinstance(getattr(module, name), dict):
            pattern_files = getattr(module, name)
            break
    
    if pattern_files:
        rules["pattern_files"] = pattern_files
    
    return rules


def extract_and_save_rules(py_file: str, yaml_file: str) -> None:
    """
    Extract query rules from a Python file and save as YAML.
    
    Args:
        py_file: Path to the Python file containing query rules
        yaml_file: Path where the YAML file should be written
    """
    rules = extract_rules_from_file(py_file)
    
    # Create directory if it doesn't exist
    yaml_path = Path(yaml_file)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to YAML file
    with open(yaml_path, "w") as f:
        yaml.dump(rules, f, default_flow_style=False, sort_keys=False)
    
    print(f"Successfully extracted rules from {py_file} and saved to {yaml_file}") 