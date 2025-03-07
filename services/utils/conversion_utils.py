"""
Utility functions for the migration process.

This module provides utilities for converting Python files with dictionaries
to YAML format, which is used in the migration of prompt files.
"""

import yaml
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional


def import_module_from_file(file_path: str) -> Any:
    """
    Dynamically import a Python module from a file path.
    
    Args:
        file_path: Path to the Python file to import
        
    Returns:
        The imported module object
    """
    file_path = Path(file_path)
    module_name = file_path.stem
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for module {module_name} from {file_path}")
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module


def extract_dictionaries_from_module(module: Any) -> Dict[str, Dict]:
    """
    Extract all uppercase dictionaries from a module.
    
    Args:
        module: The module to extract dictionaries from
        
    Returns:
        A dictionary mapping lowercase names to the original dictionaries
    """
    result = {}
    
    for name in dir(module):
        if name.isupper() and isinstance(getattr(module, name), dict):
            result[name.lower()] = getattr(module, name)
            
    return result


def convert_py_to_yaml(py_file: str, yaml_file: str, 
                       custom_processor: Optional[callable] = None) -> None:
    """
    Convert a Python file with dictionaries to a YAML file.
    
    Args:
        py_file: Path to the Python file to convert
        yaml_file: Path where the YAML file should be written
        custom_processor: Optional function to process the dictionaries before writing
                          Should take and return a dictionary
    """
    try:
        # Import the module dynamically
        module = import_module_from_file(py_file)
        
        # Extract dictionaries
        data = extract_dictionaries_from_module(module)
        
        # Apply custom processing if provided
        if custom_processor and callable(custom_processor):
            data = custom_processor(data)
        
        # Create directory if it doesn't exist
        yaml_path = Path(yaml_file)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to YAML file
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        print(f"Successfully converted {py_file} to {yaml_file}")
    
    except Exception as e:
        print(f"Error converting {py_file} to {yaml_file}: {e}")


def extract_sql_patterns(py_file: str, output_dir: str) -> Dict[str, str]:
    """
    Extract SQL patterns from a Python file and save them as individual SQL files.
    
    Args:
        py_file: Path to the Python file containing SQL patterns
        output_dir: Directory where SQL files should be saved
        
    Returns:
        A dictionary mapping pattern names to file paths
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Import the module
    module = import_module_from_file(py_file)
    
    # Find SQL pattern dictionaries
    pattern_files = {}
    sql_patterns = {}
    
    # Look for SQL_PATTERNS or PATTERNS dictionaries
    for name in dir(module):
        if name.upper() in ('SQL_PATTERNS', 'PATTERNS') and isinstance(getattr(module, name), dict):
            sql_patterns = getattr(module, name)
            break
    
    # Write each pattern to a separate file
    for idx, (pattern_name, sql_query) in enumerate(sql_patterns.items(), 1):
        if not isinstance(sql_query, str):
            continue
            
        # Format filename with sequence number for ordering
        file_name = f"{idx:02d}_{pattern_name.lower().replace(' ', '_')}.pgsql"
        file_path = Path(output_dir) / file_name
        
        with open(file_path, "w") as f:
            # Add a comment header
            f.write(f"-- {pattern_name}\n")
            f.write(sql_query.strip() + "\n")
        
        pattern_files[pattern_name] = file_name
        print(f"Saved SQL pattern '{pattern_name}' to {file_path}")
    
    return pattern_files 