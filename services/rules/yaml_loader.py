"""
Utility for loading and parsing YAML rule files.

This module provides functionality to load YAML configuration files
for business rules, SQL patterns, and schema definitions.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class YamlLoader:
    """
    A class for loading and managing YAML rules.
    """
    
    def __init__(self, base_dir: str = "services/rules"):
        """
        Initialize the YamlLoader with a base directory.
        
        Args:
            base_dir: The base directory where rule files are stored
        """
        self.base_dir = Path(base_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.debug(f"YamlLoader initialized with base directory: {base_dir}")
    
    def load_yaml(self, yaml_path: Union[str, Path], force_reload: bool = False) -> Dict[str, Any]:
        """
        Load a YAML file.
        
        Args:
            yaml_path: Path to the YAML file, relative to base_dir if not absolute
            force_reload: Whether to reload even if the file is cached
            
        Returns:
            The loaded YAML data as a dictionary
        """
        # Convert to Path object
        if isinstance(yaml_path, str):
            if os.path.isabs(yaml_path):
                path = Path(yaml_path)
            else:
                path = self.base_dir / yaml_path
        else:
            path = yaml_path
            
        path_str = str(path)
        
        # Check cache first
        if path_str in self._cache and not force_reload:
            return self._cache[path_str]
        
        # Load YAML file
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f)
                self._cache[path_str] = config
                return config
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing YAML file {path}: {e}")
    
    def load_rules_dir(self, directory: str) -> Dict[str, Dict[str, Any]]:
        """
        Load all YAML files in a directory.
        
        Args:
            directory: Directory containing YAML files, relative to base_dir
            
        Returns:
            Dictionary mapping file names to their contents
        """
        dir_path = self.base_dir / directory
        
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        result = {}
        
        for yaml_file in dir_path.glob("*.yml"):
            config = self.load_yaml(yaml_file)
            result[yaml_file.stem] = config
        
        return result
    
    def load_rules(self, rule_type: str) -> Dict[str, Any]:
        """
        Load rules of a specific type.
        
        Args:
            rule_type: Type of rules to load (e.g., 'business_rules', 'system_rules')
            
        Returns:
            The loaded rules as a dictionary
        """
        yaml_path = self.base_dir / f"{rule_type}.yml"
        return self.load_yaml(yaml_path)
    
    def load_sql_patterns(self, pattern_type: str) -> Dict[str, Any]:
        """
        Load SQL patterns for a specific type.
        
        Args:
            pattern_type: Type of SQL patterns to load (e.g., 'menu', 'order_history')
            
        Returns:
            Dictionary containing rules, schema, and SQL patterns
        """
        pattern_dir = self.base_dir / "sql_patterns" / pattern_type
        
        # Initialize result structure
        result = {
            "rules": {},
            "schema": {},
            "patterns": {}
        }
        
        # Load patterns config
        patterns_file = pattern_dir / "patterns.yml"
        try:
            patterns_data = self.load_yaml(patterns_file)
            result["rules"] = patterns_data.get("rules", {})
            pattern_files = patterns_data.get("pattern_files", {})
        except FileNotFoundError:
            pattern_files = {}
        
        # Load schema
        schema_file = pattern_dir / "schema.yml"
        try:
            schema_data = self.load_yaml(schema_file)
            result["schema"] = schema_data.get("tables", {})
        except FileNotFoundError:
            pass
        
        # Load SQL pattern files
        for pattern_key, sql_file in pattern_files.items():
            sql_path = self.base_dir / pattern_dir / sql_file
            if sql_path.exists():
                with open(sql_path, "r", encoding="utf-8") as f:
                    # Skip comment header if present
                    content = f.read()
                    lines = content.splitlines()
                    if lines and lines[0].strip().startswith("--"):
                        content = "\n".join(lines[1:])
                    result["patterns"][pattern_key] = content.strip()
        
        return result


# Singleton instance for global use
_yaml_loader = None

def get_yaml_loader(base_dir: Optional[str] = None) -> YamlLoader:
    """
    Get or create the global YamlLoader instance.
    
    Args:
        base_dir: Optional base directory
        
    Returns:
        The YamlLoader instance
    """
    global _yaml_loader
    
    if _yaml_loader is None:
        _yaml_loader = YamlLoader(base_dir or "services/rules")
    elif base_dir is not None:
        _yaml_loader.base_dir = Path(base_dir)
    
    return _yaml_loader 