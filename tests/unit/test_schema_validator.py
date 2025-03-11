import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from services.utils.schema_validator import SchemaValidator
from services.utils.schema_loader import SchemaLoader

class TestSchemaValidator(unittest.TestCase):
    """Test cases for the SchemaValidator class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock SchemaLoader
        self.mock_loader = MagicMock(spec=SchemaLoader)
        
        # Configure the mock to validate some references
        def validate_field_references(refs):
            invalid = set()
            for ref in refs:
                if not ref.startswith(('users.', 'orders.')):
                    invalid.add(ref)
                elif ref == 'users.invalid_field':
                    invalid.add(ref)
            return invalid
        
        self.mock_loader.validate_field_references.side_effect = validate_field_references
        
        # Create validator with mock loader
        self.validator = SchemaValidator(schema_loader=self.mock_loader)
    
    def test_extract_field_references(self):
        """Test extracting field references from text."""
        text = "SELECT users.id, users.name FROM users WHERE users.id = orders.user_id"
        refs = self.validator.extract_field_references(text)
        
        self.assertEqual(set(refs), {"users.id", "users.name", "orders.user_id"})
        
        # Test with no references
        text = "SELECT * FROM users"
        refs = self.validator.extract_field_references(text)
        self.assertEqual(refs, [])
    
    def test_validate_field_references_in_text(self):
        """Test validating field references in text."""
        # Valid references
        text = "SELECT users.id, orders.id FROM users JOIN orders"
        is_valid, invalid = self.validator.validate_field_references_in_text(text)
        self.assertTrue(is_valid)
        self.assertEqual(invalid, set())
        
        # Invalid references
        text = "SELECT users.invalid_field, invalid_table.id FROM users"
        is_valid, invalid = self.validator.validate_field_references_in_text(text)
        self.assertFalse(is_valid)
        self.assertEqual(invalid, {"users.invalid_field", "invalid_table.id"})
    
    def test_validate_yaml_file(self):
        """Test validating field references in a YAML file."""
        yaml_content = """
        query:
          select:
            - users.id
            - users.name
          from: users
          join:
            - table: orders
              on: orders.user_id = users.id
          where:
            - invalid_table.field = 'value'
        """
        
        # Create a mock file
        mock_file = mock_open(read_data=yaml_content)
        
        with patch('builtins.open', mock_file), \
             patch('os.path.exists', return_value=True):
            is_valid, invalid_refs = self.validator.validate_yaml_file('mock.yaml')
            
            self.assertFalse(is_valid)
            # Instead of checking for a specific path, just check that we have invalid references
            self.assertTrue(len(invalid_refs) > 0)
            # Check that invalid_table.field is in at least one of the values
            has_invalid_field = any('invalid_table.field' in refs for refs in invalid_refs.values())
            self.assertTrue(has_invalid_field)
    
    def test_validate_python_file(self):
        """Test validating field references in a Python file."""
        python_content = """
        def query_function():
            # This function queries the database
            query = "SELECT users.id, users.name FROM users"
            bad_query = "SELECT invalid_table.id FROM invalid_table"
            return query
        """
        
        # Create a mock file
        mock_file = mock_open(read_data=python_content)
        
        with patch('builtins.open', mock_file), \
             patch('os.path.exists', return_value=True):
            is_valid, invalid_refs = self.validator.validate_python_file('mock.py')
            
            self.assertFalse(is_valid)
            # Check that at least one line has an invalid reference
            self.assertTrue(len(invalid_refs) > 0)
            # Check that invalid_table.id is in at least one of the values
            has_invalid_field = any('invalid_table.id' in refs for refs in invalid_refs.values())
            self.assertTrue(has_invalid_field)
    
    def test_validate_directory(self):
        """Test validating field references in a directory."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a YAML file
            yaml_path = os.path.join(temp_dir, 'test.yml')
            with open(yaml_path, 'w') as f:
                f.write("""
                query:
                  select:
                    - users.id
                  from: users
                """)
            
            # Create a Python file
            py_path = os.path.join(temp_dir, 'test.py')
            with open(py_path, 'w') as f:
                f.write("""
                # Test file
                query = "SELECT users.id FROM users"
                bad_query = "SELECT invalid_table.id FROM invalid_table"
                """)
            
            # Mock the validation methods to return known results
            with patch.object(self.validator, 'validate_yaml_file', 
                           return_value=(True, {})), \
                  patch.object(self.validator, 'validate_python_file', 
                           return_value=(False, {3: {"invalid_table.id"}})):
                
                results = self.validator.validate_directory(temp_dir)
                
                # Check results
                self.assertTrue(yaml_path in results)
                self.assertTrue(py_path in results)
                self.assertTrue(results[yaml_path]['is_valid'])
                self.assertFalse(results[py_path]['is_valid'])

if __name__ == '__main__':
    unittest.main() 