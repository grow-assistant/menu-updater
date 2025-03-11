#!/usr/bin/env python3
"""
Relationship Validator for Rule Files.

This utility validates that relationships defined in rule files match
the actual database schema.
"""

import os
import re
import yaml
import json
from typing import Dict, List, Set, Tuple, Any, Optional

from services.utils.schema_loader import SchemaLoader

class RelationshipValidator:
    """
    Validates relationship declarations in rule files against the actual schema.
    
    This class checks that all relationships referenced in rule files (both in
    'relationships' fields and in rule descriptions) match the actual DB schema.
    """
    
    def __init__(self, schema_loader: Optional[SchemaLoader] = None):
        """
        Initialize the RelationshipValidator.
        
        Args:
            schema_loader: Optional SchemaLoader instance, created if not provided
        """
        self.schema_loader = schema_loader or SchemaLoader()
        
        # Regex patterns
        self.fk_pattern = re.compile(r"FOREIGN\s+KEY\s+\((\w+)\)\s+REFERENCES\s+(\w+)\((\w+)\)", re.IGNORECASE)
        self.join_pattern = re.compile(r"JOIN\s+(\w+)(?:\s+\w+)?\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", re.IGNORECASE)
        
    def validate_foreign_key(self, table_name: str, field_name: str, ref_table: str, ref_field: str) -> bool:
        """
        Validate a foreign key declaration.
        
        Args:
            table_name: Name of the table containing the foreign key
            field_name: Name of the foreign key field
            ref_table: Name of the referenced table
            ref_field: Name of the referenced field
            
        Returns:
            True if the relationship is valid, False otherwise
        """
        # Check table and field existence
        if not self.schema_loader.table_exists(table_name):
            return False
            
        if not self.schema_loader.field_exists(table_name, field_name):
            return False
            
        if not self.schema_loader.table_exists(ref_table):
            return False
            
        if not self.schema_loader.field_exists(ref_table, ref_field):
            return False
            
        # Check if the relationship matches the schema
        field_info = self.schema_loader.get_field_info(table_name, field_name)
        if not field_info or 'references' not in field_info:
            return False
            
        # Compare with the schema's reference
        expected_reference = f"{ref_table}.{ref_field}"
        return field_info['references'] == expected_reference
    
    def validate_relationship_declaration(self, relationship: str) -> Tuple[bool, str]:
        """
        Validate a relationship declaration string.
        
        Args:
            relationship: Relationship declaration string (e.g., "FOREIGN KEY (user_id) REFERENCES users(id)")
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        match = self.fk_pattern.match(relationship)
        if not match:
            return False, f"Invalid relationship format: {relationship}"
            
        field_name, ref_table, ref_field = match.groups()
        
        # We don't know the table name from just the declaration
        # This will be provided by the context when used in validate_relationships_in_rule
        return True, ""
    
    def validate_relationships_in_rule(self, rule_data: Dict[str, Any], context_table: str) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate all relationships in a rule definition.
        
        Args:
            rule_data: Dictionary containing rule data
            context_table: The table name that provides context for this rule
            
        Returns:
            Tuple of (is_valid, {category: [error_messages]})
        """
        all_valid = True
        errors: Dict[str, List[str]] = {}
        
        # Check for explicit relationships array
        if 'relationships' in rule_data:
            errors['relationships'] = []
            for rel in rule_data['relationships']:
                match = self.fk_pattern.match(rel)
                if not match:
                    all_valid = False
                    errors['relationships'].append(f"Invalid relationship format: {rel}")
                    continue
                    
                field_name, ref_table, ref_field = match.groups()
                if not self.validate_foreign_key(context_table, field_name, ref_table, ref_field):
                    all_valid = False
                    errors['relationships'].append(
                        f"Invalid relationship: {context_table}.{field_name} -> {ref_table}.{ref_field}"
                    )
        
        # Recursively check nested dictionaries
        for key, value in rule_data.items():
            if isinstance(value, dict):
                sub_valid, sub_errors = self.validate_relationships_in_rule(value, context_table)
                if not sub_valid:
                    all_valid = False
                    for category, messages in sub_errors.items():
                        if category not in errors:
                            errors[category] = []
                        errors[category].extend(messages)
            
        return all_valid, errors
    
    def validate_rule_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate all relationships in a rule file.
        
        Args:
            file_path: Path to the rule file (Python or YAML)
            
        Returns:
            Tuple of (is_valid, detailed_errors)
        """
        if file_path.endswith(('.yml', '.yaml')):
            return self._validate_yaml_rule_file(file_path)
        elif file_path.endswith('.py'):
            return self._validate_python_rule_file(file_path)
        else:
            return False, {"error": f"Unsupported file type: {file_path}"}
    
    def _validate_yaml_rule_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate relationships in a YAML rule file."""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                
            all_valid = True
            errors = {}
            
            for table_name, table_data in data.get('tables', {}).items():
                valid, table_errors = self.validate_relationships_in_rule(table_data, table_name)
                if not valid:
                    all_valid = False
                    errors[table_name] = table_errors
                    
            return all_valid, errors
        except Exception as e:
            return False, {"error": f"Error processing {file_path}: {str(e)}"}
    
    def _validate_python_rule_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate relationships in a Python rule file.
        
        Args:
            file_path: Path to the Python rule file
            
        Returns:
            Tuple of (is_valid, detailed_errors)
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # First, find all schema dictionaries in the file
            schemas = self._extract_schema_dictionaries(content, file_path)
            if not schemas:
                return False, {"warning": f"No schema dictionaries found in {file_path}"}
                
            all_valid = True
            errors = {}
            
            # Validate each schema dictionary
            for schema_name, schema_data in schemas.items():
                for table_name, table_data in schema_data.items():
                    valid, table_errors = self.validate_relationships_in_rule(table_data, table_name)
                    if not valid:
                        all_valid = False
                        if schema_name not in errors:
                            errors[schema_name] = {}
                        errors[schema_name][table_name] = table_errors
            
            # Also look for relationship declarations in rule dictionaries
            rules = self._extract_rule_dictionaries(content, file_path)
            for rule_name, rule_data in rules.items():
                if "join_structure" in rule_data:
                    # Hard to validate join structures without knowing the tables
                    # Just flag them for manual review
                    if rule_name not in errors:
                        errors[rule_name] = {}
                    errors[rule_name]["join_structure"] = [
                        f"Manual review needed for join structure: {rule_data['join_structure']}"
                    ]
                    all_valid = False
            
            return all_valid, errors
        except Exception as e:
            return False, {"error": f"Error processing {file_path}: {str(e)}"}
    
    def _extract_schema_dictionaries(self, content: str, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract schema dictionaries from Python file content.
        
        Args:
            content: Python file content as string
            file_path: Path to the file (for error reporting)
            
        Returns:
            Dictionary mapping schema names to schema data
        """
        schemas = {}
        
        # Look for schema variable assignments like XXX_SCHEMA = { ... }
        schema_pattern = re.compile(r'([A-Z_]+_SCHEMA)\s*=\s*{', re.MULTILINE)
        matches = schema_pattern.finditer(content)
        
        for match in matches:
            schema_name = match.group(1)
            start_pos = match.end() - 1  # Position of opening {
            
            # Find matching closing bracket
            bracket_count = 1
            end_pos = start_pos + 1
            
            while bracket_count > 0 and end_pos < len(content):
                if content[end_pos] == '{':
                    bracket_count += 1
                elif content[end_pos] == '}':
                    bracket_count -= 1
                end_pos += 1
            
            if bracket_count == 0:
                try:
                    # Extract the schema dictionary and parse it
                    schema_str = content[start_pos:end_pos]
                    
                    # Since we can't safely eval Python code, we'll use a regex-based approach
                    schema_data = {}
                    
                    # Extract top-level keys (table names)
                    table_pattern = re.compile(r'\s*"([^"]+)"\s*:\s*{', re.MULTILINE)
                    table_matches = table_pattern.finditer(schema_str)
                    
                    # Process each table section
                    for table_match in table_matches:
                        table_name = table_match.group(1)
                        table_start = table_match.end() - 1  # Position of opening {
                        
                        # Find the matching closing brace for this table
                        table_bracket_count = 1
                        table_end = table_start + 1
                        
                        while table_bracket_count > 0 and table_end < len(schema_str):
                            if schema_str[table_end] == '{':
                                table_bracket_count += 1
                            elif schema_str[table_end] == '}':
                                table_bracket_count -= 1
                            table_end += 1
                        
                        if table_bracket_count == 0:
                            # Extract and parse the table definition
                            table_str = schema_str[table_start:table_end]
                            table_data = self._parse_dict_structure(table_str)
                            schema_data[table_name] = table_data
                    
                    schemas[schema_name] = schema_data
                except Exception as e:
                    print(f"Error parsing schema {schema_name} in {file_path}: {str(e)}")
        
        return schemas
    
    def _extract_rule_dictionaries(self, content: str, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract rule dictionaries from Python file content.
        
        Args:
            content: Python file content as string
            file_path: Path to the file (for error reporting)
            
        Returns:
            Dictionary mapping rule names to rule data
        """
        rules = {}
        
        # Look for rule variable assignments like XXX_RULES = { ... }
        rule_pattern = re.compile(r'([A-Z_]+_RULES)\s*=\s*{', re.MULTILINE)
        matches = rule_pattern.finditer(content)
        
        for match in matches:
            rule_name = match.group(1)
            start_pos = match.end() - 1  # Position of opening {
            
            # Find matching closing bracket
            bracket_count = 1
            end_pos = start_pos + 1
            
            while bracket_count > 0 and end_pos < len(content):
                if content[end_pos] == '{':
                    bracket_count += 1
                elif content[end_pos] == '}':
                    bracket_count -= 1
                end_pos += 1
            
            if bracket_count == 0:
                try:
                    # Extract the rule dictionary and parse it
                    rule_str = content[start_pos:end_pos]
                    
                    # Look for the "general" section specifically
                    general_pattern = re.compile(r'\s*"general"\s*:\s*{', re.MULTILINE)
                    general_match = general_pattern.search(rule_str)
                    
                    if general_match:
                        general_start = general_match.end() - 1  # Position of opening {
                        
                        # Find the matching closing brace for the general section
                        general_bracket_count = 1
                        general_end = general_start + 1
                        
                        while general_bracket_count > 0 and general_end < len(rule_str):
                            if rule_str[general_end] == '{':
                                general_bracket_count += 1
                            elif rule_str[general_end] == '}':
                                general_bracket_count -= 1
                            general_end += 1
                        
                        if general_bracket_count == 0:
                            # Extract and parse the general section
                            general_str = rule_str[general_start:general_end]
                            general_data = self._parse_dict_structure(general_str)
                            rules[rule_name] = general_data
                    else:
                        # If there's no general section, parse the whole thing
                        rule_data = self._parse_dict_structure(rule_str)
                        rules[rule_name] = rule_data
                except Exception as e:
                    print(f"Error parsing rules {rule_name} in {file_path}: {str(e)}")
        
        return rules
    
    def _parse_dict_structure(self, dict_str: str) -> Dict[str, Any]:
        """
        Parse a Python dictionary string into a structured dictionary.
        
        This is a simplified parser for extracting key-value pairs from a dictionary string.
        For our purposes, we're mainly looking for "relationships" arrays and specific rule fields.
        
        Args:
            dict_str: Dictionary string to parse
            
        Returns:
            Parsed dictionary structure
        """
        result = {}
        
        # First pass: extract all keys and their string values
        # This regex matches "key": "string value" or "key": any_value
        key_value_pattern = re.compile(r'"([^"]+)"\s*:\s*(?:"([^"]*)"|\{|\[|([^,\}\]]*))', re.MULTILINE)
        
        for match in key_value_pattern.finditer(dict_str):
            key = match.group(1)
            string_value = match.group(2)
            other_value = match.group(3)
            
            if string_value is not None:
                # We found a string value
                result[key] = string_value
            elif other_value is not None:
                # We found some other simple value
                result[key] = other_value.strip()
            else:
                # We found the start of a complex value (dict or list)
                start_pos = match.end()
                
                # Find the end of this value by counting braces/brackets
                brace_count = 0
                bracket_count = 0
                
                # Count opening braces/brackets at the beginning
                value_prefix = dict_str[start_pos-1:start_pos+1]
                if '{' in value_prefix:
                    brace_count = 1
                elif '[' in value_prefix:
                    bracket_count = 1
                
                # Find the matching closing brace/bracket
                end_pos = start_pos
                while (brace_count > 0 or bracket_count > 0) and end_pos < len(dict_str):
                    if dict_str[end_pos] == '{':
                        brace_count += 1
                    elif dict_str[end_pos] == '}':
                        brace_count -= 1
                    elif dict_str[end_pos] == '[':
                        bracket_count += 1
                    elif dict_str[end_pos] == ']':
                        bracket_count -= 1
                    end_pos += 1
                
                # Extract the complex value
                complex_value = dict_str[start_pos-1:end_pos].strip()
                
                if complex_value.startswith('{'):
                    # Nested dictionary
                    try:
                        result[key] = self._parse_dict_structure(complex_value)
                    except Exception as e:
                        print(f"Error parsing nested dict for key {key}: {str(e)}")
                        result[key] = complex_value
                elif complex_value.startswith('['):
                    # Array
                    if '"' in complex_value:
                        # Extract quoted strings from array
                        string_pattern = re.compile(r'"([^"]*)"')
                        result[key] = string_pattern.findall(complex_value)
                    else:
                        result[key] = complex_value
        
        return result
    
    def validate_directory(self, directory: str, extension: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Validate all rule files in a directory.
        
        Args:
            directory: Directory to scan for rule files
            extension: Optional file extension filter
            
        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}
        
        for root, _, files in os.walk(directory):
            for file in files:
                if extension and not file.endswith(extension):
                    continue
                    
                file_path = os.path.join(root, file)
                is_valid, errors = self.validate_rule_file(file_path)
                results[file_path] = {
                    "is_valid": is_valid,
                    "errors": errors if not is_valid else {}
                }
                
        return results

# Example usage
if __name__ == "__main__":
    validator = RelationshipValidator()
    # Example validation
    result = validator.validate_foreign_key(
        "orders", "customer_id", "users", "id"
    )
    print(f"Validation result: {result}") 