"""
Enhanced Rules Service for managing business rules and SQL examples.
"""
import logging
import os
import json
import time
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from services.rules.yaml_loader import get_yaml_loader, YamlLoader

logger = logging.getLogger(__name__)

class RulesService:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the RulesService.
        
        Args:
            config: Configuration for the rules service
        """
        self.config = config
        self.rules_path = config.get("services", {}).get("rules", {}).get("rules_path", "./services/rules")
        self.resources_dir = config["services"]["rules"].get("resources_dir", "resources")
        # Set up SQL files path - pointing to existing sql_generator module
        self.sql_files_path = config["services"]["rules"].get("sql_files_path", "services/sql_generator/sql_files")
        
        # Initialize caching
        self.cached_rules = {}
        self.cache_ttl = config["services"]["rules"].get("cache_ttl", 3600)  # Default 1 hour TTL
        self.cache_timestamps = {}
        self.cached_sql_patterns = {}  # Add cache for SQL patterns
        
        # Initialize YAML loader
        self.yaml_loader = get_yaml_loader(self.resources_dir)
        
        # Query rules mapping
        self.query_rules_modules = {}
        self.query_rules_mapping = {
            # Default mappings from classification categories to rule modules
            "order_history": "order_history_rules",
            "trend_analysis": "trend_analysis_rules",
            "popular_items": "popular_items_rules",
            "order_ratings": "order_ratings_rules",
            "menu_inquiry": "menu_inquiry_rules",
            # Maintain general_question as a fallback
            "general_question": "general_question_rules"
        }
        
        # Load custom category to module mappings if provided in config
        if "query_rules_mapping" in config["services"]["rules"]:
            self.query_rules_mapping.update(config["services"]["rules"]["query_rules_mapping"])
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Load rules
        self.load_rules()
    
    def load_rules(self):
        """Load all rules from file or database."""
        logger.info("Loading rules from storage")
        try:
            # For now, we'll support both YAML and JSON loading
            # This provides backward compatibility
            self._load_rules_from_files()
            self._load_yaml_rules()
            self._load_query_rules_modules()
        except Exception as e:
            logger.error(f"Error loading rules: {str(e)}")
            raise
    
    def _load_rules_from_files(self):
        """Load rules from the file system (JSON format)."""
        base_rules = {}
        
        # Check if rules path exists
        if not os.path.exists(self.rules_path):
            logger.warning(f"Rules path does not exist: {self.rules_path}")
            self.base_rules = {}
            return
        
        # Load rules for each category
        for category in os.listdir(self.rules_path):
            category_path = os.path.join(self.rules_path, category)
            if os.path.isdir(category_path):
                base_rules[category] = {
                    "sql_examples": [],
                    "response_rules": {}
                }
                
                # Load SQL examples
                examples_file = os.path.join(category_path, "examples.json")
                if os.path.exists(examples_file):
                    with open(examples_file, "r") as f:
                        base_rules[category]["sql_examples"] = json.load(f)
                
                # Load response rules
                rules_file = os.path.join(category_path, "rules.json")
                if os.path.exists(rules_file):
                    with open(rules_file, "r") as f:
                        base_rules[category]["response_rules"] = json.load(f)
        
        # Store the base rules (unprocessed)
        self.base_rules = base_rules
    
    def _load_yaml_rules(self):
        """Load rules from YAML files."""
        # Load system rules
        try:
            system_rules = self.yaml_loader.load_rules("system_rules")
            self.system_rules = system_rules
        except FileNotFoundError:
            logger.warning("System rules file not found")
            self.system_rules = {}
        
        # Load business rules
        try:
            business_rules = self.yaml_loader.load_rules("business_rules")
            self.business_rules = business_rules
        except FileNotFoundError:
            logger.warning("Business rules file not found")
            self.business_rules = {}
        
        # Add YAML-based rules to base_rules
        if not hasattr(self, 'base_rules'):
            self.base_rules = {}
            
        if "system" not in self.base_rules:
            self.base_rules["system"] = {
                "sql_examples": [],
                "response_rules": self.system_rules.get("rules", {})
            }
            
        if "business" not in self.base_rules:
            self.base_rules["business"] = {
                "sql_examples": [],
                "response_rules": self.business_rules.get("rules", {})
            }
    
    def _load_query_rules_modules(self):
        """
        Load all query rules modules from the rules directory.
        Each module should have a standardized interface including get_X_rules() functions.
        """
        try:
            # Get a list of all modules in the current directory
            self.query_rules_modules = {}
            
            # Add core modules that should always be loaded if they exist
            core_modules = [
                "menu_inquiry_rules", 
                "order_history_rules", 
                "order_ratings_rules", 
                "popular_items_rules", 
                "trend_analysis_rules",
            ]
            
            for module_name in core_modules:
                try:
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                    else:
                        module = importlib.import_module(f"services.rules.query_rules.{module_name}")
                    
                    self.query_rules_modules[module_name] = module
                    self.logger.info(f"Loaded query rules module: {module_name}")
                except ImportError as e:
                    self.logger.warning(f"Could not import {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error loading query rules modules: {str(e)}")
    
    def get_rules_and_examples(self, category: str) -> Dict[str, Any]:
        """
        Get rules and examples for a specific category with caching.
        
        Args:
            category: The query category
            
        Returns:
            Dict containing SQL examples and response rules
        """
        # Check if we have a valid cached version
        current_time = time.time()
        if (category in self.cached_rules and 
            category in self.cache_timestamps and 
            current_time - self.cache_timestamps[category] < self.cache_ttl):
            logger.debug(f"Using cached rules for category: {category}")
            return self.cached_rules[category]
        
        # Process and cache the rules
        logger.info(f"Processing rules for category: {category}")
        rules = self._process_rules_for_category(category)
        self.cached_rules[category] = rules
        self.cache_timestamps[category] = current_time
        return rules
    
    def _process_rules_for_category(self, category: str) -> Dict[str, Any]:
        """
        Process rules for a specific category.
        This allows for any transformations or enrichments before returning.
        
        Args:
            category: The query category
            
        Returns:
            Processed rules for the category
        """
        # Start with base rules if available
        if category in self.base_rules:
            rules = self.base_rules[category].copy()
        else:
            rules = {"sql_examples": [], "response_rules": {}}
        
        # Add query-specific rules if available
        module_name = self.query_rules_mapping.get(category, None)
        if module_name and module_name in self.query_rules_modules:
            try:
                module = self.query_rules_modules[module_name]
                query_rules = module.get_rules(self)
                
                # Merge query rules into the result
                if "query_rules" in query_rules:
                    rules["query_rules"] = query_rules["query_rules"]
                
                if "schema" in query_rules:
                    rules["schema"] = query_rules["schema"]
                
                if "query_patterns" in query_rules:
                    rules["query_patterns"] = query_rules["query_patterns"]
                
                logger.info(f"Added query-specific rules for category '{category}' from module '{module_name}'")
            except Exception as e:
                logger.error(f"Error getting query rules for category '{category}' from module '{module_name}': {str(e)}")
        
        return rules
    
    def get_sql_patterns(self, pattern_type: str) -> Dict[str, Any]:
        """
        Get SQL patterns for a specific type.
        
        Args:
            pattern_type: Type of SQL patterns to load
            
        Returns:
            Dictionary containing rules, schema, and SQL patterns
        """
        try:
            # First try to load from YAML patterns (legacy approach)
            try:
                return self.yaml_loader.load_sql_patterns(pattern_type)
            except Exception as yaml_error:
                logger.debug(f"Could not load SQL patterns from YAML for {pattern_type}: {str(yaml_error)}")
            
            # If YAML loading fails, try to load from SQL files directory
            sql_dir = f"query_{pattern_type}"
            pattern_dir = Path(self.sql_files_path) / sql_dir
            
            if not pattern_dir.exists():
                logger.warning(f"SQL patterns directory not found: {pattern_dir}")
                return {"rules": {}, "schema": {}, "patterns": {}}
            
            # Load all SQL files in the directory
            patterns = {}
            # Note: Previously loaded individual .pgsql files, but this has been disabled
            # to ensure consistency with only loading SQL examples from examples.json files
            logger.info(f"Skipping loading individual .pgsql files from {pattern_dir}. "
                      "Only using examples.json files per updated requirements.")
            
            # Load schema information
            schema_file = os.path.join(pattern_dir, "schema.json")
            if os.path.exists(schema_file):
                try:
                    with open(schema_file, "r") as f:
                        schema = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading schema file {schema_file}: {str(e)}")
                    schema = {}
            else:
                schema = {}
            
            # Return the patterns with empty rules and populated schema
            return {"rules": {}, "schema": schema, "patterns": patterns}
            
        except Exception as e:
            logger.error(f"Error loading SQL patterns: {str(e)}")
            return {"rules": {}, "schema": {}, "patterns": {}}
    
    def get_schema_for_type(self, pattern_type: str) -> Dict[str, Any]:
        """
        Get database schema for a specific type.
        
        Args:
            pattern_type: Type of schema to load
            
        Returns:
            Dictionary containing schema definition
        """
        # Try to get schema from query rules first
        rules = self.get_rules_and_examples(pattern_type)
        if "schema" in rules:
            return rules["schema"]
        
        # Fall back to YAML-based patterns
        patterns = self.get_sql_patterns(pattern_type)
        return patterns.get("schema", {})
    
    def get_sql_pattern(self, pattern_type: str, pattern_name: str) -> str:
        """
        Get a specific SQL pattern.
        
        Args:
            pattern_type: Type of SQL patterns
            pattern_name: Name of the specific pattern
            
        Returns:
            SQL pattern string or empty string if not found
        """
        patterns = self.get_sql_patterns(pattern_type)
        return patterns.get("patterns", {}).get(pattern_name, "")
    
    def load_sql_patterns_from_directory(self, directory: str, file_to_pattern_map: Dict[str, str], 
                                       default_patterns: Dict[str, str] = None) -> Dict[str, str]:
        """
        Load SQL patterns from a directory.
        Maps files to pattern names using the provided mapping.
        
        Args:
            directory: Directory containing SQL pattern files
            file_to_pattern_map: Mapping of file names to pattern names
            default_patterns: Default patterns to use if file not found
            
        Returns:
            Dictionary of pattern names to SQL patterns
        """
        # Check if patterns for this directory are already cached
        if directory in self.cached_sql_patterns:
            logger.debug(f"Using cached SQL patterns for directory: {directory}")
            return self.cached_sql_patterns[directory]
            
        patterns = {}
        
        if default_patterns:
            patterns.update(default_patterns)
        
        base_dir = os.path.join(self.sql_files_path, directory)
        
        if not os.path.exists(base_dir):
            logger.warning(f"SQL patterns directory not found: {base_dir}")
            self.cached_sql_patterns[directory] = patterns  # Cache even empty results
            return patterns
        
        # Load each file and map to pattern name
        for file_name, pattern_name in file_to_pattern_map.items():
            file_path = os.path.join(base_dir, file_name)
            
            if not os.path.exists(file_path):
                logger.debug(f"SQL pattern file not found: {file_path}")
                continue
                
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    patterns[pattern_name] = content
            except Exception as e:
                logger.error(f"Error loading SQL pattern file {file_path}: {str(e)}")
        
        # Load all remaining .sql files from the directory
        for file_name in os.listdir(base_dir):
            if file_name.endswith('.sql') and file_name not in file_to_pattern_map:
                # Use the file name (without extension) as the pattern name
                pattern_name = os.path.splitext(file_name)[0]
                file_path = os.path.join(base_dir, file_name)
                
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                        patterns[pattern_name] = content
                except Exception as e:
                    logger.error(f"Error loading SQL pattern file {file_path}: {str(e)}")
        
        logger.info(f"Loaded {len(patterns)} SQL patterns from directory: {directory}")
        
        # Cache the patterns
        self.cached_sql_patterns[directory] = patterns
        
        return patterns
    
    def load_all_sql_files_from_directory(self, directory: str, default_patterns: Dict[str, str] = None) -> Dict[str, str]:
        """
        Load all SQL files from a directory without hard-coding file names.
        
        Args:
            directory: Name of the directory to load SQL files from
            default_patterns: Optional default patterns to use if no files are found
            
        Returns:
            Dictionary mapping file names (without extension) to SQL content
        """
        patterns = {}
        
        # Directory path within sql_generator/sql_files
        directory_path = Path(self.sql_files_path) / directory
        
        if not directory_path.exists():
            logger.warning(f"SQL directory {directory_path} not found.")
            return patterns
            
        # Previously loaded .pgsql and .sql files, but this has been disabled
        # to ensure consistency with only loading SQL examples from examples.json files
        logger.info(f"Skipping loading individual .pgsql and .sql files from {directory_path}. "
                   "Only using examples.json files per updated requirements.")
        
        # If default patterns are provided, use them
        if default_patterns:
            patterns.update(default_patterns)
        
        return patterns
    
    def replace_placeholders(self, patterns: Dict[str, str], replacements: Dict[str, Any]) -> Dict[str, str]:
        """
        Replace placeholders in SQL patterns with actual values.
        
        Args:
            patterns: Dictionary mapping pattern names to SQL queries
            replacements: Dictionary mapping placeholder names to values
            
        Returns:
            Dictionary with placeholders replaced
        """
        result = {}
        
        for pattern_name, sql in patterns.items():
            replaced_sql = sql
            for placeholder, value in replacements.items():
                replaced_sql = replaced_sql.replace(f"{{{placeholder}}}", str(value))
            result[pattern_name] = replaced_sql
        
        return result
    
    def get_base_rules(self) -> Dict[str, Any]:
        """
        Get the base business rules.
        
        Returns:
            Dictionary containing base business rules
        """
        return self.business_rules.get("rules", {})
    
    def format_rules_for_prompt(self, rules: Dict[str, Any]) -> str:
        """
        Format rules for inclusion in a prompt.
        
        Args:
            rules: Rules dictionary
            
        Returns:
            Formatted rules string
        """
        formatted = []
        
        for rule_category, rule_list in rules.items():
            formatted.append(f"\n{rule_category.upper()}:")
            if isinstance(rule_list, list):
                for i, rule in enumerate(rule_list):
                    formatted.append(f"{i+1}. {rule}")
            elif isinstance(rule_list, dict):
                for key, value in rule_list.items():
                    formatted.append(f"- {key}: {value}")
            else:
                formatted.append(str(rule_list))
        
        return "\n".join(formatted)
    
    def invalidate_cache(self, category: Optional[str] = None):
        """
        Invalidate the cache for a specific category or all categories.
        
        Args:
            category: The category to invalidate, or None for all categories
        """
        if category:
            if category in self.cached_rules:
                del self.cached_rules[category]
                if category in self.cache_timestamps:
                    del self.cache_timestamps[category]
                logger.info(f"Cache invalidated for category: {category}")
        else:
            self.cached_rules = {}
            self.cache_timestamps = {}
            logger.info("Cache invalidated for all categories")
    
    def reload_rules(self):
        """Reload all rules from storage and invalidate cache."""
        self.load_rules()
        self.invalidate_cache()
        logger.info("Rules reloaded from storage")
    
    def health_check(self) -> bool:
        """
        Verify rules file/database is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if rules directory exists
            if not os.path.exists(self.rules_path) or not os.path.isdir(self.rules_path):
                logger.warning(f"Rules path does not exist or is not a directory: {self.rules_path}")
                
            # Try to load system rules as a basic check
            self.yaml_loader.load_rules("system_rules")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def get_sql_examples(self, classification):
        """Get SQL examples for the given classification."""
        try:
            # Get examples from the rules module
            examples = []
            module_name = f"{classification}_rules"
            if module_name in self.query_rules_modules:
                module = self.query_rules_modules[module_name]
                if hasattr(module, 'get_sql_examples'):
                    logger.info(f"Getting SQL examples from {module_name}.get_sql_examples()")
                    examples = module.get_sql_examples()
                    if examples:
                        logger.info(f"Found {len(examples)} examples from {module_name}.get_sql_examples()")
                        return examples
            
            # No examples from module, log a warning
            logger.warning(f"No SQL examples found for classification: {classification}")
            return []
        except Exception as e:
            logger.error(f"Error getting SQL examples for {classification}: {e}")
            return []
    
    def get_rules(self, category: str, query: str = None) -> Dict[str, Any]:
        """
        Get rules for a specific category (compatibility method for orchestrator).
        
        Args:
            category: The query category
            query: Optional query text for context-specific rules
            
        Returns:
            Dict containing rules for the category
        """
        # Get the rules and examples using the existing method
        rules_and_examples = self.get_rules_and_examples(category)
        
        # If we have query rules modules, try to use those first
        if category in self.query_rules_mapping:
            module_name = self.query_rules_mapping[category]
            if module_name in self.query_rules_modules:
                try:
                    # Call the module's get_rules function with self as the rules_service parameter
                    module_rules = self.query_rules_modules[module_name].get_rules(self)
                    if module_rules:
                        return module_rules
                except Exception as e:
                    self.logger.error(f"Error getting rules from module {module_name}: {str(e)}")
        
        return rules_and_examples
    
    def load_database_schema(self):
        """
        Load the database schema definition from resources/database_fields.md
        or from a structured JSON/YAML representation of the same data.
        """
        try:
            schema_path = os.path.join(self.resources_dir, "database_schema.yml")
            if os.path.exists(schema_path):
                self.database_schema = self.yaml_loader.load_yaml(schema_path)
                logger.info(f"Loaded database schema from {schema_path}")
            else:
                # Fall back to parsing markdown file if structured file doesn't exist
                md_path = os.path.join(self.resources_dir, "database_fields.md")
                if os.path.exists(md_path):
                    self.database_schema = self._parse_schema_from_markdown(md_path)
                    logger.info(f"Parsed database schema from {md_path}")
                else:
                    logger.warning("Database schema definition not found")
                    self.database_schema = {}
        except Exception as e:
            logger.error(f"Error loading database schema: {str(e)}")
            self.database_schema = {}

    def _parse_schema_from_markdown(self, md_path):
        """
        Parse the database schema from a markdown file.
        """
        schema = {}
        current_table = None
        
        with open(md_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith('## '):
                # New table definition
                current_table = line[3:].strip()
                schema[current_table] = {"fields": []}
            elif line.startswith('- ') and current_table:
                # Field definition
                field_def = line[2:].strip()
                if '(' in field_def:
                    field_name = field_def.split('(')[0].strip()
                    field_type = field_def[field_def.find('(')+1:field_def.find(')')]
                    schema[current_table]["fields"].append({
                        "name": field_name,
                        "type": field_type,
                        "nullable": "NOT NULL" not in field_def,
                        "primary_key": "primary key" in field_def.lower() or "NOT NULL" in field_def
                    })
        
        return schema

    def get_database_schema(self):
        """
        Get the database schema.
        
        Returns:
            Dictionary containing the database schema
        """
        if not hasattr(self, 'database_schema') or not self.database_schema:
            self.load_database_schema()
        
        return self.database_schema 