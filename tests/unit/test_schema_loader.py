import unittest
import os
import yaml
from unittest.mock import patch, mock_open
from services.utils.schema_loader import SchemaLoader

class TestSchemaLoader(unittest.TestCase):
    """Test cases for the SchemaLoader class."""
    
    def setUp(self):
        """Set up the test environment with a sample schema."""
        self.sample_schema = {
            'tables': {
                'users': {
                    'fields': {
                        'id': {
                            'type': 'integer',
                            'nullable': False
                        },
                        'name': {
                            'type': 'text'
                        },
                        'email': {
                            'type': 'text'
                        }
                    }
                },
                'orders': {
                    'fields': {
                        'id': {
                            'type': 'integer',
                            'nullable': False
                        },
                        'user_id': {
                            'type': 'integer',
                            'nullable': False,
                            'references': 'users.id'
                        },
                        'total': {
                            'type': 'numeric',
                            'nullable': False
                        }
                    }
                }
            }
        }
        
        # Convert sample schema to YAML
        self.sample_yaml = yaml.dump(self.sample_schema)
        
        # Create a mock for the open function used by SchemaLoader
        self.mock_open_patcher = patch('builtins.open', mock_open(read_data=self.sample_yaml))
        self.mock_open = self.mock_open_patcher.start()
    
    def tearDown(self):
        """Clean up after each test."""
        self.mock_open_patcher.stop()
    
    def test_load_schema(self):
        """Test that the schema is loaded correctly."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        self.assertEqual(loader.schema, self.sample_schema)
    
    def test_get_tables(self):
        """Test getting the list of tables."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        tables = loader.get_tables()
        self.assertEqual(set(tables), {'users', 'orders'})
    
    def test_table_exists(self):
        """Test checking if a table exists."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        self.assertTrue(loader.table_exists('users'))
        self.assertTrue(loader.table_exists('orders'))
        self.assertFalse(loader.table_exists('non_existent_table'))
    
    def test_get_table_fields(self):
        """Test getting fields for a table."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        user_fields = loader.get_table_fields('users')
        self.assertEqual(set(user_fields), {'id', 'name', 'email'})
        
        # Test with non-existent table
        non_existent_fields = loader.get_table_fields('non_existent_table')
        self.assertEqual(non_existent_fields, [])
    
    def test_field_exists(self):
        """Test checking if a field exists in a table."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        self.assertTrue(loader.field_exists('users', 'id'))
        self.assertTrue(loader.field_exists('users', 'name'))
        self.assertFalse(loader.field_exists('users', 'non_existent_field'))
        self.assertFalse(loader.field_exists('non_existent_table', 'id'))
    
    def test_get_field_info(self):
        """Test getting information about a field."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        user_id_info = loader.get_field_info('users', 'id')
        self.assertEqual(user_id_info, {'type': 'integer', 'nullable': False})
        
        # Test with non-existent field
        self.assertIsNone(loader.get_field_info('users', 'non_existent_field'))
    
    def test_get_foreign_keys(self):
        """Test getting foreign key relationships for a table."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        order_foreign_keys = loader.get_foreign_keys('orders')
        self.assertEqual(order_foreign_keys, {'user_id': 'users.id'})
        
        # Test with table that has no foreign keys
        user_foreign_keys = loader.get_foreign_keys('users')
        self.assertEqual(user_foreign_keys, {})
    
    def test_get_referencing_fields(self):
        """Test getting fields that reference a table."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        references_to_users = loader.get_referencing_fields('users')
        self.assertEqual(references_to_users, {'orders': ['user_id']})
        
        # Test with table that is not referenced
        references_to_orders = loader.get_referencing_fields('orders')
        self.assertEqual(references_to_orders, {})
    
    def test_validate_field_references(self):
        """Test validating field references."""
        loader = SchemaLoader(schema_path='mock_path.yaml')
        
        # Valid references
        valid_references = ['users.id', 'orders.total']
        invalid_refs = loader.validate_field_references(valid_references)
        self.assertEqual(invalid_refs, set())
        
        # Invalid references
        invalid_references = ['users.non_existent', 'non_existent_table.id', 'invalid_format']
        invalid_refs = loader.validate_field_references(invalid_references)
        self.assertEqual(invalid_refs, set(invalid_references))

if __name__ == '__main__':
    unittest.main() 