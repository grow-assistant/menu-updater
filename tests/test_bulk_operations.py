"""Tests for bulk menu operations"""
import pytest
from utils.operation_patterns import match_operation, handle_operation_step
from utils.menu_operations import (
    disable_by_pattern,
    disable_options_by_pattern,
    disable_option_items_by_pattern
)
from utils.chat_functions import process_chat_message

def test_bulk_operation_matching():
    """Test bulk operation pattern matching"""
    # Test disable all items
    operation = match_operation("disable all Club Made Chips")
    assert operation == {
        "type": "disable_bulk",
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {"pattern": "Club Made Chips"}
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

def test_bulk_operation_flow(mocker):
    """Test bulk operation conversation flow"""
    # Mock database functions
    mock_db = mocker.patch("utils.menu_operations.postgres_connection")
    mock_cursor = mocker.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Mock item results
    mock_cursor.fetchall.return_value = [
        (1, "Club Made Chips", "Appetizers"),
        (2, "Club Made Chips - Large", "Appetizers")
    ]
    
    # Test initial request
    response = process_chat_message("disable all Club Made Chips", [], [])
    assert response["role"] == "assistant"
    assert "Found these items" in response["content"]
    assert "Club Made Chips" in response["content"]
    assert "Would you like to proceed" in response["content"]
    
    # Test first confirmation
    response = process_chat_message("yes", [], [])
    assert response["role"] == "assistant"
    assert "Are you absolutely sure" in response["content"]
    
    # Test final confirmation
    response = process_chat_message("yes", [], [])
    assert response["role"] == "function"
    assert response["name"] == "disable_by_pattern"
    assert response["params"]["pattern"] == "Club Made Chips"

def test_error_handling(mocker):
    """Test error handling in bulk operations"""
    # Mock database error
    mock_db = mocker.patch("utils.menu_operations.postgres_connection")
    mock_db.cursor.side_effect = Exception("Database error")
    
    # Test database error
    response = process_chat_message("disable all Club Made Chips", [], [])
    assert response["role"] == "assistant"
    assert "error" in response["content"].lower()
    
    # Test empty response
    mock_db.cursor.side_effect = None
    mock_cursor = mocker.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    
    response = process_chat_message("disable all Club Made Chips", [], [])
    assert response["role"] == "assistant"
    assert "No active items found" in response["content"]

if __name__ == "__main__":
    pytest.main([__file__])
