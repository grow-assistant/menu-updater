import unittest
import os
import tempfile
import subprocess
import sys
from pathlib import Path

# Adjust path to import from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.utils.schema_loader import SchemaLoader
from services.utils.schema_validator import SchemaValidator

class TestSchemaValidationIntegration(unittest.TestCase):
    """Integration tests for schema validation system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Create a schema file
        self.schema_path = self.test_dir / 'test_schema.yaml'
        with open(self.schema_path, 'w') as f:
            f.write("""tables:
  users:
    fields:
      id:
        type: integer
        nullable: false
      name:
        type: text
      email:
        type: text
  orders:
    fields:
      id:
        type: integer
        nullable: false
      user_id:
        type: integer
        nullable: false
        references: users.id
      total:
        type: numeric
        nullable: false
""")
        
        # Create a valid YAML file
        self.valid_yaml_path = self.test_dir / 'valid.yml'
        with open(self.valid_yaml_path, 'w') as f:
            f.write("""query:
  select:
    - users.id
    - users.name
    - orders.total
  from: users
  join:
    - table: orders
      on: orders.user_id = users.id
""")
        
        # Create an invalid YAML file
        self.invalid_yaml_path = self.test_dir / 'invalid.yml'
        with open(self.invalid_yaml_path, 'w') as f:
            f.write("""query:
  select:
    - users.id
    - users.invalid_field
    - nonexistent_table.field
  from: users
""")
        
        # Create a valid Python file
        self.valid_py_path = self.test_dir / 'valid.py'
        with open(self.valid_py_path, 'w') as f:
            f.write("""
def get_user_orders():
    query = "SELECT users.id, users.name, orders.total FROM users JOIN orders ON orders.user_id = users.id"
    return query
""")
        
        # Create an invalid Python file
        self.invalid_py_path = self.test_dir / 'invalid.py'
        with open(self.invalid_py_path, 'w') as f:
            f.write("""
def get_user_data():
    query = "SELECT users.id, users.nonexistent_field FROM users"
    return query
""")
    
    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
    
    def test_schema_loader_with_custom_path(self):
        """Test that SchemaLoader can load a schema from a custom path."""
        loader = SchemaLoader(schema_path=str(self.schema_path))
        
        # Verify the schema is loaded correctly
        self.assertEqual(set(loader.get_tables()), {'users', 'orders'})
        self.assertEqual(set(loader.get_table_fields('users')), {'id', 'name', 'email'})
        self.assertEqual(set(loader.get_table_fields('orders')), {'id', 'user_id', 'total'})
    
    def test_schema_validator_with_valid_file(self):
        """Test that SchemaValidator correctly validates a valid file."""
        loader = SchemaLoader(schema_path=str(self.schema_path))
        validator = SchemaValidator(schema_loader=loader)
        
        # Test valid YAML file
        is_valid, _ = validator.validate_yaml_file(str(self.valid_yaml_path))
        self.assertTrue(is_valid)
        
        # Test valid Python file
        is_valid, _ = validator.validate_python_file(str(self.valid_py_path))
        self.assertTrue(is_valid)
    
    def test_schema_validator_with_invalid_file(self):
        """Test that SchemaValidator correctly identifies invalid references."""
        loader = SchemaLoader(schema_path=str(self.schema_path))
        validator = SchemaValidator(schema_loader=loader)
        
        # Test invalid YAML file
        is_valid, invalid_refs = validator.validate_yaml_file(str(self.invalid_yaml_path))
        self.assertFalse(is_valid)
        
        # Check that invalid references were found (we don't check the exact keys)
        invalid_fields = set()
        for refs in invalid_refs.values():
            invalid_fields.update(refs)
        
        self.assertTrue('users.invalid_field' in invalid_fields)
        self.assertTrue('nonexistent_table.field' in invalid_fields)
        
        # Test invalid Python file
        is_valid, invalid_refs = validator.validate_python_file(str(self.invalid_py_path))
        self.assertFalse(is_valid)
        
        # Check that invalid references were found
        invalid_fields = set()
        for refs in invalid_refs.values():
            invalid_fields.update(refs)
        
        self.assertTrue('users.nonexistent_field' in invalid_fields)
    
    def test_directory_validation(self):
        """Test validating an entire directory."""
        loader = SchemaLoader(schema_path=str(self.schema_path))
        validator = SchemaValidator(schema_loader=loader)
        
        # Create a subdirectory with test files to validate
        test_subdir = self.test_dir / 'test_subdir'
        test_subdir.mkdir()
        
        # Copy the test files to the subdirectory
        import shutil
        shutil.copy(self.valid_yaml_path, test_subdir)
        shutil.copy(self.invalid_yaml_path, test_subdir)
        
        # Validate only the subdirectory
        results = validator.validate_directory(str(test_subdir))
        
        # Check that the correct number of files were processed
        self.assertEqual(len(results), 2)  # 2 YAML files
        
        # Get the full paths of the files in the subdirectory
        valid_yaml_in_subdir = str(test_subdir / self.valid_yaml_path.name)
        invalid_yaml_in_subdir = str(test_subdir / self.invalid_yaml_path.name)
        
        # Check that valid files are identified as valid
        self.assertTrue(results[valid_yaml_in_subdir]['is_valid'])
        
        # Check that invalid files are identified as invalid
        self.assertFalse(results[invalid_yaml_in_subdir]['is_valid'])

if __name__ == '__main__':
    unittest.main() 