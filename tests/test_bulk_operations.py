"""Tests for bulk menu operations"""
import pytest
from unittest.mock import patch, MagicMock
from tests.mocks import mock_streamlit, mock_database, mock_openai

# Mock dependencies before importing modules that use them
mock_streamlit()
mock_openai()

# Import modules
from utils.operation_patterns import match_operation, handle_operation_step
from utils.menu_operations import (
    disable_by_pattern,
    disable_options_by_pattern,
    disable_option_items_by_pattern
)

def test_bulk_operation_matching():
    """Test bulk operation pattern matching"""
    # Test disable all items
    operation = match_operation("disable all club made chips")
    assert operation == {
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {"pattern": "club made chips"}
    }
    
    # Test disable all options
    operation = match_operation("disable all options for Club Made Chips")
    assert operation == {
        "type": "disable_bulk_options",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_options_by_pattern",
        "item_type": "Item Option",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
    }
    
    # Test disable all option items
    operation = match_operation("disable all option items for Club Made Chips")
    assert operation == {
        "type": "disable_bulk_option_items",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_option_items_by_pattern",
        "item_type": "Option Item",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
    }

@patch("utils.database_functions.get_db_connection")
def test_bulk_operation_flow(mock_get_conn):
    """Test bulk operation conversation flow"""
    # Set up mock database
    mock_connection, mock_cursor = mock_database()
    mock_get_conn.return_value = mock_connection
    
    # Mock item results
    mock_cursor.fetchall.return_value = [
        (1, "Club Made Chips", "Appetizers"),
        (2, "Club Made Chips - Large", "Appetizers")
    ]
    
    # Test initial request
    response = handle_operation_step({
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
    }, "")
    assert response["role"] == "assistant"
    assert "Found these items" in response["content"]
    assert "Club Made Chips" in response["content"]
    assert "Would you like to proceed" in response["content"]
    
    # Test first confirmation
    response = handle_operation_step({
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 1,
        "params": {"pattern": "Club Made Chips"}
    }, "yes")
    assert response["role"] == "assistant"
    assert "Are you absolutely sure" in response["content"]
    
    # Test final confirmation
    response = handle_operation_step({
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 2,
        "params": {"pattern": "Club Made Chips"}
    }, "yes")
    assert response["role"] == "function"
    assert response["name"] == "disable_by_pattern"
    assert response["params"]["pattern"] == "club made chips"

@patch("utils.database_functions.get_db_connection")
def test_error_handling(mock_get_conn):
    """Test error handling in bulk operations"""
    # Mock database error
    mock_get_conn.side_effect = Exception("Database error")
    
    # Test database error
    response = handle_operation_step({
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
    }, "")
    assert response["role"] == "assistant"
    assert "error" in response["content"].lower()
    
    # Test empty response
    mock_db.side_effect = None
    mock_connection, mock_cursor = mock_database()
    mock_db.return_value = mock_connection
    mock_cursor.fetchall.return_value = []
    
    response = handle_operation_step({
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
    }, "")
    assert response["role"] == "assistant"
    assert "No active items found" in response["content"]

if __name__ == "__main__":
    pytest.main([__file__])
