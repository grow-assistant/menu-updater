#!/usr/bin/env python3
"""
Unit tests for the RelationshipValidator class.
"""

import os
import sys
import unittest
import tempfile
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from services.utils.schema_loader import SchemaLoader
from services.utils.relationship_validator import RelationshipValidator

class TestRelationshipValidator(unittest.TestCase):
    """
    Unit tests for the RelationshipValidator class.
    """
    
    def setUp(self):
        """Set up test cases."""
        # Create a mock SchemaLoader that will return predictable results
        self.schema_loader = SchemaLoader()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        
        # Create the validator
        self.validator = RelationshipValidator(self.schema_loader)
        
        # Create a test Python file
        self.test_py_path = os.path.join(self.test_dir, "test_rules.py")
        with open(self.test_py_path, "w") as f:
            f.write('''
# Test rules file
TEST_SCHEMA = {
    "orders": {
        "description": "Main orders table",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "customer_id": "INTEGER - Foreign key to users table"
        },
        "relationships": [
            "FOREIGN KEY (customer_id) REFERENCES users(id)"
        ],
        "primary_key": "id",
        "indexes": ["customer_id"],
        "referenced_by": {
            "order_items": "order_id"
        }
    }
}

TEST_RULES = {
    "general": {
        "location_filter": "ALWAYS filter by orders.location_id = [LOCATION_ID]",
        "join_structure": "Join orders to order_items to items for complete order details"
    }
}
''')
        
        # Create a test YAML file
        self.test_yaml_path = os.path.join(self.test_dir, "test_rules.yaml")
        with open(self.test_yaml_path, "w") as f:
            f.write('''
tables:
  orders:
    columns:
      id: "INTEGER PRIMARY KEY - Unique identifier"
      customer_id: "INTEGER - Foreign key to users table"
    relationships:
      - "FOREIGN KEY (customer_id) REFERENCES users(id)"
''')
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_validate_foreign_key(self):
        """Test validating a foreign key relationship."""
        # Mock the schema_loader's field_exists and get_field_info methods
        original_field_exists = self.schema_loader.field_exists
        original_table_exists = self.schema_loader.table_exists
        original_get_field_info = self.schema_loader.get_field_info
        
        try:
            # Mock field_exists to always return True
            self.schema_loader.field_exists = lambda table, field: True
            self.schema_loader.table_exists = lambda table: True
            
            # Mock get_field_info to return a references field for specific cases
            def mock_get_field_info(table, field):
                if table == "orders" and field == "customer_id":
                    return {"type": "integer", "references": "users.id"}
                return {}
            
            self.schema_loader.get_field_info = mock_get_field_info
            
            # Test valid foreign key
            result = self.validator.validate_foreign_key(
                "orders", "customer_id", "users", "id"
            )
            self.assertTrue(result)
            
            # Test invalid foreign key (wrong reference field)
            result = self.validator.validate_foreign_key(
                "orders", "customer_id", "users", "user_id"
            )
            self.assertFalse(result)
        finally:
            # Restore original methods
            self.schema_loader.field_exists = original_field_exists
            self.schema_loader.table_exists = original_table_exists
            self.schema_loader.get_field_info = original_get_field_info
    
    def test_validate_relationship_declaration(self):
        """Test validating a relationship declaration."""
        # Valid relationship
        valid, _ = self.validator.validate_relationship_declaration(
            "FOREIGN KEY (customer_id) REFERENCES users(id)"
        )
        self.assertTrue(valid)
        
        # Invalid relationship
        valid, _ = self.validator.validate_relationship_declaration(
            "INVALID SYNTAX"
        )
        self.assertFalse(valid)
    
    def test_parse_dict_structure(self):
        """Test parsing a dictionary structure from a string."""
        # Simple dictionary
        dict_str = '{\n    "key1": "value1",\n    "key2": "value2"\n}'
        result = self.validator._parse_dict_structure(dict_str)
        self.assertEqual(result.get("key1"), "value1")
        self.assertEqual(result.get("key2"), "value2")
        
        # Nested dictionary
        dict_str = '{\n    "key1": {\n        "nested": "value"\n    }\n}'
        result = self.validator._parse_dict_structure(dict_str)
        self.assertIsInstance(result.get("key1"), dict)
        self.assertEqual(result.get("key1").get("nested"), "value")
        
        # List of strings
        dict_str = '{\n    "key1": [\n        "value1",\n        "value2"\n    ]\n}'
        result = self.validator._parse_dict_structure(dict_str)
        self.assertIsInstance(result.get("key1"), list)
        self.assertEqual(len(result.get("key1")), 2)
    
    def test_extract_schema_dictionaries(self):
        """Test extracting schema dictionaries from Python code."""
        # Read the test file
        with open(self.test_py_path, "r") as f:
            content = f.read()
        
        # Extract schemas
        schemas = self.validator._extract_schema_dictionaries(content, self.test_py_path)
        self.assertIn("TEST_SCHEMA", schemas)
        self.assertIn("orders", schemas["TEST_SCHEMA"])
    
    def test_extract_rule_dictionaries(self):
        """Test extracting rule dictionaries from Python code."""
        # Read the test file
        with open(self.test_py_path, "r") as f:
            content = f.read()
        
        # Extract rules
        rules = self.validator._extract_rule_dictionaries(content, self.test_py_path)
        self.assertIn("TEST_RULES", rules)
        self.assertIn("location_filter", rules["TEST_RULES"])
        self.assertIn("join_structure", rules["TEST_RULES"])

if __name__ == "__main__":
    unittest.main() 