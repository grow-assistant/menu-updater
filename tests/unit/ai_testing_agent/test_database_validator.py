"""
Unit tests for the DatabaseValidator class.
"""

import pytest
from unittest.mock import MagicMock, patch
import psycopg2
from ai_testing_agent.database_validator import DatabaseValidator

@pytest.fixture
def mock_db_connection():
    """Create a mock database connection for testing."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor

@pytest.fixture
def validator_with_mock_db(mock_db_connection):
    """Create a DatabaseValidator with a mock database connection."""
    mock_conn, _ = mock_db_connection
    
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.return_value = mock_conn
        validator = DatabaseValidator(db_connection_string='mock_connection_string')
        return validator

class TestDatabaseValidator:
    """Tests for the DatabaseValidator class."""
    
    def test_initialization(self):
        """Test the validator initializes with a database connection."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            with patch('os.getenv') as mock_getenv:
                mock_getenv.return_value = 'test_connection_string'
                validator = DatabaseValidator()
                
                mock_connect.assert_called_once_with('test_connection_string')
                assert validator.connection_string == 'test_connection_string'
                
    def test_initialization_with_explicit_connection_string(self):
        """Test initialization with an explicit connection string."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            validator = DatabaseValidator(db_connection_string='explicit_connection_string')
            
            mock_connect.assert_called_once_with('explicit_connection_string')
            assert validator.connection_string == 'explicit_connection_string'
    
    def test_validate_menu_item_price(self, validator_with_mock_db, mock_db_connection):
        """Test validation of menu item prices."""
        _, mock_cursor = mock_db_connection
        
        # Mock the cursor.fetchone() to return a price
        mock_cursor.fetchone.return_value = (12.99,)
        
        response_text = "The margherita pizza costs $12.99"
        result = validator_with_mock_db.validate_response(response_text, "menu_query")
        
        # Verify SQL was executed with the right parameters
        mock_cursor.execute.assert_called_once()
        assert "margherita pizza" in mock_cursor.execute.call_args[0][1]
        
        # Check validation results
        assert result["valid"] is True
        assert result["accuracy_score"] == 1.0
        assert len(result["validation_results"]) == 1
        assert result["validation_results"][0]["valid"] is True
        
    def test_validate_menu_item_price_mismatch(self, validator_with_mock_db, mock_db_connection):
        """Test validation when the claimed price doesn't match the database."""
        _, mock_cursor = mock_db_connection
        
        # Mock the cursor.fetchone() to return a different price
        mock_cursor.fetchone.return_value = (14.99,)
        
        response_text = "The margherita pizza costs $12.99"
        result = validator_with_mock_db.validate_response(response_text, "menu_query")
        
        # Check validation results
        assert result["valid"] is False
        assert result["accuracy_score"] == 0.0
        assert result["validation_results"][0]["valid"] is False
        assert "does not match" in result["validation_results"][0]["explanation"]
        
    def test_validate_menu_item_not_found(self, validator_with_mock_db, mock_db_connection):
        """Test validation when the menu item is not found in the database."""
        _, mock_cursor = mock_db_connection
        
        # Mock the cursor.fetchone() to return None (item not found)
        mock_cursor.fetchone.return_value = None
        
        response_text = "The unicorn pizza costs $19.99"
        result = validator_with_mock_db.validate_response(response_text, "menu_query")
        
        # Check validation results
        assert result["valid"] is False
        assert "not found" in result["validation_results"][0]["explanation"]
        
    def test_validate_with_entities(self, validator_with_mock_db, mock_db_connection):
        """Test validation using pre-extracted entities."""
        _, mock_cursor = mock_db_connection
        
        # Mock the cursor.fetchone() to return a price
        mock_cursor.fetchone.return_value = (12.99,)
        
        entities = {
            "menu_items": [
                {"name": "margherita pizza", "price": 12.99}
            ]
        }
        
        result = validator_with_mock_db.validate_response("", "menu_query", entities)
        
        # Verify SQL was executed with the right parameters
        mock_cursor.execute.assert_called_once()
        assert "margherita pizza" in mock_cursor.execute.call_args[0][1]
        
        # Check validation results
        assert result["valid"] is True
        assert result["accuracy_score"] == 1.0
        
    def test_order_history_validation(self, validator_with_mock_db, mock_db_connection):
        """Test validation of order history."""
        _, mock_cursor = mock_db_connection
        
        # Set up mocks for order validation
        mock_cursor.fetchall.return_value = [(2, "Pepperoni Pizza"), (1, "Garlic Bread")]
        
        entities = {
            "orders": [
                {
                    "id": 123,
                    "date": "2023-03-15",
                    "items": [
                        {"name": "Pepperoni Pizza", "quantity": 2},
                        {"name": "Garlic Bread", "quantity": 1}
                    ]
                }
            ]
        }
        
        result = validator_with_mock_db.validate_response("", "order_history", entities)
        
        # Check validation results
        assert result["valid"] is True
        assert result["accuracy_score"] == 1.0
        
    def test_check_sql_query(self, validator_with_mock_db, mock_db_connection):
        """Test the direct SQL query execution method."""
        _, mock_cursor = mock_db_connection
        
        # Set up mock return value
        mock_cursor.fetchall.return_value = [(1, "Test Item", 9.99)]
        
        # Execute a custom SQL query
        result = validator_with_mock_db.check_sql_query("SELECT * FROM menu_items WHERE id = %s", (1,))
        
        # Verify SQL was executed with the right parameters
        mock_cursor.execute.assert_called_once_with("SELECT * FROM menu_items WHERE id = %s", (1,))
        
        # Check the result
        assert result == [(1, "Test Item", 9.99)]
        
    def test_get_table_schema(self, validator_with_mock_db, mock_db_connection):
        """Test retrieving table schema information."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Create a different cursor for the DictCursor
        mock_dict_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_dict_cursor
        
        # Set up mock return value
        mock_dict_cursor.fetchall.return_value = [
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
            {"column_name": "name", "data_type": "character varying", "is_nullable": "NO"},
            {"column_name": "price", "data_type": "numeric", "is_nullable": "NO"}
        ]
        
        # Get schema for a table
        result = validator_with_mock_db.get_table_schema("menu_items")
        
        # Verify the right SQL was executed
        assert "information_schema.columns" in mock_dict_cursor.execute.call_args[0][0]
        assert "menu_items" in mock_dict_cursor.execute.call_args[0][1]
        
        # Check the result
        assert len(result) == 3
        assert result[0]["column_name"] == "id"
        assert result[1]["data_type"] == "character varying"
        assert result[2]["is_nullable"] == "NO"
        
    def test_no_facts_found(self, validator_with_mock_db):
        """Test behavior when no validatable facts are found in a response."""
        response_text = "Thank you for your inquiry!"  # No validatable facts
        
        result = validator_with_mock_db.validate_response(response_text, "menu_query")
        
        assert result["valid"] is False
        assert result["error"] == "No validatable facts found"
        assert result["validation_results"] == []
        
    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("Connection error")
            
            with pytest.raises(psycopg2.OperationalError) as excinfo:
                DatabaseValidator(db_connection_string='invalid_connection')
                
            assert "Connection error" in str(excinfo.value)
            
    def test_validation_error_handling(self, validator_with_mock_db, mock_db_connection):
        """Test error handling during validation."""
        _, mock_cursor = mock_db_connection
        
        # Make the cursor.execute raise an exception
        mock_cursor.execute.side_effect = Exception("Database error during validation")
        
        response_text = "The margherita pizza costs $12.99"
        result = validator_with_mock_db.validate_response(response_text, "menu_query")
        
        # Check validation results
        assert result["valid"] is False
        assert "Error during validation" in result["validation_results"][0]["explanation"] 