import os
import yaml
from typing import Dict, Any, Optional, List, Set

class SchemaLoader:
    """
    Utility class for loading and accessing the database schema definition.
    This class provides methods to validate field names, check table existence,
    and access schema information.
    """
    
    def __init__(self, schema_path: str = None):
        """
        Initialize the SchemaLoader with a path to the schema file.
        
        Args:
            schema_path: Path to the schema YAML file, defaults to resources/schema.yaml
        """
        if schema_path is None:
            # Default path relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            schema_path = os.path.join(base_dir, 'resources', 'schema.yaml')
        
        self.schema_path = schema_path
        self.schema: Dict[str, Any] = {}
        self.load_schema()
    
    def load_schema(self) -> None:
        """Load the schema from the YAML file."""
        try:
            with open(self.schema_path, 'r') as file:
                self.schema = yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"Failed to load schema from {self.schema_path}: {str(e)}")
    
    def get_tables(self) -> List[str]:
        """
        Get a list of all tables in the schema.
        
        Returns:
            List of table names
        """
        if not self.schema or 'tables' not in self.schema:
            return []
        return list(self.schema['tables'].keys())
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the schema.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if the table exists, False otherwise
        """
        if not self.schema or 'tables' not in self.schema:
            return False
        return table_name in self.schema['tables']
    
    def get_table_fields(self, table_name: str) -> List[str]:
        """
        Get all fields for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of field names for the table, or empty list if table doesn't exist
        """
        if not self.table_exists(table_name):
            return []
        
        fields = self.schema['tables'][table_name].get('fields', {})
        return list(fields.keys())
    
    def field_exists(self, table_name: str, field_name: str) -> bool:
        """
        Check if a field exists in a table.
        
        Args:
            table_name: Name of the table
            field_name: Name of the field to check
            
        Returns:
            True if the field exists in the table, False otherwise
        """
        if not self.table_exists(table_name):
            return False
        
        fields = self.schema['tables'][table_name].get('fields', {})
        return field_name in fields
    
    def get_field_info(self, table_name: str, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific field.
        
        Args:
            table_name: Name of the table
            field_name: Name of the field
            
        Returns:
            Dictionary with field information or None if field doesn't exist
        """
        if not self.field_exists(table_name, field_name):
            return None
        
        return self.schema['tables'][table_name]['fields'][field_name]
    
    def get_foreign_keys(self, table_name: str) -> Dict[str, str]:
        """
        Get all foreign key relationships for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping field names to referenced tables/fields
        """
        if not self.table_exists(table_name):
            return {}
        
        foreign_keys = {}
        fields = self.schema['tables'][table_name].get('fields', {})
        
        for field_name, field_info in fields.items():
            if 'references' in field_info:
                foreign_keys[field_name] = field_info['references']
        
        return foreign_keys
    
    def get_referencing_fields(self, table_name: str) -> Dict[str, List[str]]:
        """
        Get fields from other tables that reference this table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping table names to lists of fields that reference this table
        """
        if not self.table_exists(table_name):
            return {}
        
        references = {}
        
        for other_table, table_info in self.schema['tables'].items():
            fields = table_info.get('fields', {})
            referencing_fields = []
            
            for field_name, field_info in fields.items():
                reference = field_info.get('references', '')
                referenced_table = reference.split('.')[0] if '.' in reference else ''
                
                if referenced_table == table_name:
                    referencing_fields.append(field_name)
            
            if referencing_fields:
                references[other_table] = referencing_fields
        
        return references
    
    def validate_field_references(self, field_references: List[str]) -> Set[str]:
        """
        Validate a list of field references in format "table.field".
        
        Args:
            field_references: List of field references to validate
            
        Returns:
            Set of invalid field references
        """
        invalid_references = set()
        
        for reference in field_references:
            if '.' not in reference:
                invalid_references.add(reference)
                continue
                
            table_name, field_name = reference.split('.', 1)
            
            if not self.field_exists(table_name, field_name):
                invalid_references.add(reference)
        
        return invalid_references 