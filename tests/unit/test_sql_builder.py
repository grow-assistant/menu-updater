import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import the modules
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from services.utils.sql_builder import SQLBuilder


class TestSQLBuilder(unittest.TestCase):
    """Test cases for the SQLBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock RulesManager
        self.mock_rules_manager = MagicMock()
        
        # Configure mock behavior
        self.mock_rules_manager.get_sql_pattern.return_value = "SELECT * FROM items WHERE location_id = [LOCATION_ID]"
        self.mock_rules_manager.substitute_variables.return_value = "SELECT * FROM items WHERE location_id = 62"
        
        # Sample schema for testing
        self.test_schema = {
            "tables": {
                "items": {
                    "description": "Menu items table",
                    "columns": {
                        "id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "price": "NUMERIC(10,2)",
                        "category_id": "INTEGER",
                        "disabled": "BOOLEAN"
                    }
                },
                "categories": {
                    "description": "Item categories",
                    "columns": {
                        "id": "INTEGER PRIMARY KEY",
                        "name": "TEXT"
                    }
                }
            }
        }
        
        self.mock_rules_manager.get_schema_for_type.return_value = self.test_schema
        
        # Create SQLBuilder with the mock RulesManager
        self.sql_builder = SQLBuilder(rules_manager=self.mock_rules_manager)

    def test_build_query(self):
        """Test building a query from a pattern."""
        result = self.sql_builder.build_query("menu", "active_items", {"LOCATION_ID": 62})
        
        # Verify RulesManager methods were called correctly
        self.mock_rules_manager.get_sql_pattern.assert_called_once_with("menu", "active_items")
        self.mock_rules_manager.substitute_variables.assert_called_once()
        
        # Check the result
        self.assertEqual(result, "SELECT * FROM items WHERE location_id = 62")

    def test_get_schema_info(self):
        """Test getting schema information."""
        result = self.sql_builder.get_schema_info("menu")
        
        # Verify RulesManager methods were called correctly
        self.mock_rules_manager.get_schema_for_type.assert_called_once_with("menu")
        
        # Check the result
        self.assertEqual(result, self.test_schema)

    def test_get_table_columns(self):
        """Test getting column information for a specific table."""
        result = self.sql_builder.get_table_columns("menu", "items")
        
        # Verify result
        expected_columns = {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
            "price": "NUMERIC(10,2)",
            "category_id": "INTEGER",
            "disabled": "BOOLEAN"
        }
        self.assertEqual(result, expected_columns)

    def test_build_select_query(self):
        """Test building a SELECT query from components."""
        result = self.sql_builder.build_select_query(
            pattern_type="menu",
            tables=["items"],
            columns=["id", "name", "price"],
            where_conditions=["category_id = 5", "disabled = FALSE"],
            order_by=["price DESC"]
        )
        
        expected = "SELECT id, name, price FROM items WHERE category_id = 5 AND disabled = FALSE ORDER BY price DESC;"
        self.assertEqual(result, expected)

    def test_build_select_query_with_joins(self):
        """Test building a SELECT query with JOIN clauses."""
        result = self.sql_builder.build_select_query(
            pattern_type="menu",
            tables=["items"],
            columns=["items.id", "items.name", "categories.name AS category_name"],
            where_conditions=["items.disabled = FALSE"],
            joins=["JOIN categories ON items.category_id = categories.id"],
            order_by=["categories.name", "items.name"]
        )
        
        expected = "SELECT items.id, items.name, categories.name AS category_name FROM items JOIN categories ON items.category_id = categories.id WHERE items.disabled = FALSE ORDER BY categories.name, items.name;"
        self.assertEqual(result, expected)

    def test_build_update_query(self):
        """Test building an UPDATE query."""
        result = self.sql_builder.build_update_query(
            pattern_type="menu",
            table="items",
            set_values={"price": 12.99, "updated_at": "NOW()"},
            where_conditions=["id = 42", "disabled = FALSE"]
        )
        
        expected = "UPDATE items SET price = 12.99, updated_at = NOW() WHERE id = 42 AND disabled = FALSE;"
        self.assertEqual(result, expected)

    def test_build_update_query_with_strings(self):
        """Test building an UPDATE query with string values."""
        result = self.sql_builder.build_update_query(
            pattern_type="menu",
            table="items",
            set_values={"name": "Caesar Salad", "description": "Fresh romaine lettuce with Caesar dressing"},
            where_conditions=["id = 42"]
        )
        
        expected = "UPDATE items SET name = 'Caesar Salad', description = 'Fresh romaine lettuce with Caesar dressing' WHERE id = 42;"
        self.assertEqual(result, expected)

    def test_build_insert_query(self):
        """Test building an INSERT query."""
        result = self.sql_builder.build_insert_query(
            pattern_type="menu",
            table="items",
            values={
                "name": "Greek Salad",
                "price": 11.99,
                "category_id": 3,
                "disabled": False,
                "created_at": "NOW()"
            }
        )
        
        expected = "INSERT INTO items (name, price, category_id, disabled, created_at) VALUES ('Greek Salad', 11.99, 3, False, NOW());"
        self.assertEqual(result, expected)

    def test_validate_query_valid(self):
        """Test validating a valid query."""
        valid_query = "SELECT * FROM items WHERE id = 42;"
        self.assertTrue(self.sql_builder.validate_query(valid_query))

    def test_validate_query_invalid_placeholders(self):
        """Test validating a query with unsubstituted placeholders."""
        invalid_query = "SELECT * FROM items WHERE location_id = [LOCATION_ID];"
        self.assertFalse(self.sql_builder.validate_query(invalid_query))

    def test_validate_query_invalid_quotes(self):
        """Test validating a query with mismatched quotes."""
        invalid_query = "SELECT * FROM items WHERE name = 'Caesar Salad;"
        self.assertFalse(self.sql_builder.validate_query(invalid_query))

    def test_validate_query_invalid_parentheses(self):
        """Test validating a query with mismatched parentheses."""
        invalid_query = "SELECT * FROM items WHERE (id = 42 AND (price > 10;"
        self.assertFalse(self.sql_builder.validate_query(invalid_query))


if __name__ == "__main__":
    unittest.main() 