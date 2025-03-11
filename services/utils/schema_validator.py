import os
import re
import yaml
from typing import List, Dict, Set, Any, Optional, Tuple
from .schema_loader import SchemaLoader

class SchemaValidator:
    """
    Validator for checking rule files against the database schema.
    This class helps ensure field references in rules match the actual database structure.
    """
    
    def __init__(self, schema_loader: Optional[SchemaLoader] = None):
        """
        Initialize the SchemaValidator with a SchemaLoader.
        
        Args:
            schema_loader: SchemaLoader instance or None to create a new one
        """
        self.schema_loader = schema_loader or SchemaLoader()
        
        # Common regex patterns for field references
        self.field_ref_pattern = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    def extract_field_references(self, content: str) -> List[str]:
        """
        Extract field references from text content in the format "table.field".
        
        Args:
            content: Text content to search for field references
            
        Returns:
            List of field references found in the content
        """
        # Find all matches of table.field pattern
        matches = self.field_ref_pattern.findall(content)
        return [f"{table}.{field}" for table, field in matches]
    
    def validate_field_references_in_text(self, content: str) -> Tuple[bool, Set[str]]:
        """
        Validate field references in text content.
        
        Args:
            content: Text content to validate
            
        Returns:
            Tuple of (is_valid, invalid_references)
        """
        field_references = self.extract_field_references(content)
        invalid_references = self.schema_loader.validate_field_references(field_references)
        return len(invalid_references) == 0, invalid_references
    
    def validate_yaml_file(self, file_path: str) -> Tuple[bool, Dict[str, Set[str]]]:
        """
        Validate field references in a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Tuple of (is_valid, {yaml_path: invalid_references})
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as file:
                yaml_content = yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"Failed to load YAML file {file_path}: {str(e)}")
        
        invalid_refs = {}
        self._validate_yaml_node(yaml_content, "", invalid_refs)
        
        return len(invalid_refs) == 0, invalid_refs
    
    def _validate_yaml_node(self, node: Any, path: str, invalid_refs: Dict[str, Set[str]]) -> None:
        """
        Recursively validate field references in a YAML node.
        
        Args:
            node: YAML node to validate
            path: Current path in the YAML structure
            invalid_refs: Dictionary to collect invalid references
        """
        if isinstance(node, dict):
            for key, value in node.items():
                new_path = f"{path}.{key}" if path else key
                self._validate_yaml_node(value, new_path, invalid_refs)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                new_path = f"{path}[{i}]"
                self._validate_yaml_node(item, new_path, invalid_refs)
        elif isinstance(node, str):
            # Check string values for field references
            _, invalid = self.validate_field_references_in_text(node)
            if invalid:
                invalid_refs[path] = invalid
    
    def validate_python_file(self, file_path: str) -> Tuple[bool, Dict[int, Set[str]]]:
        """
        Validate field references in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Tuple of (is_valid, {line_number: invalid_references})
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Python file not found: {file_path}")
        
        invalid_refs = {}
        
        try:
            with open(file_path, 'r') as file:
                for i, line in enumerate(file, start=1):
                    _, invalid = self.validate_field_references_in_text(line)
                    if invalid:
                        invalid_refs[i] = invalid
        except Exception as e:
            raise ValueError(f"Failed to read Python file {file_path}: {str(e)}")
        
        return len(invalid_refs) == 0, invalid_refs
    
    def validate_directory(self, directory: str, extension: str = None) -> Dict[str, Dict]:
        """
        Validate field references in all files in a directory.
        
        Args:
            directory: Directory path to validate
            extension: Optional file extension filter (e.g., '.py', '.yml')
            
        Returns:
            Dictionary mapping file paths to validation results
        """
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Directory not found: {directory}")
        
        results = {}
        
        for root, _, files in os.walk(directory):
            for file in files:
                if extension and not file.endswith(extension):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    if file.endswith(('.yml', '.yaml')):
                        is_valid, invalid_refs = self.validate_yaml_file(file_path)
                    elif file.endswith('.py'):
                        is_valid, invalid_refs = self.validate_python_file(file_path)
                    else:
                        # Skip unsupported file types
                        continue
                    
                    results[file_path] = {
                        'is_valid': is_valid,
                        'invalid_references': invalid_refs
                    }
                except Exception as e:
                    results[file_path] = {
                        'is_valid': False,
                        'error': str(e)
                    }
        
        return results 