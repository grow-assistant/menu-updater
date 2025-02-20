"""Test bulk operations functionality"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any
from unittest.mock import MagicMock, patch, call

# Mock streamlit before importing bulk_operations
sys.modules['streamlit'] = MagicMock()
from utils.bulk_operations import apply_bulk_updates, update_side_items

def test_apply_bulk_updates():
    """Test applying bulk updates to items and options"""
    # Mock connection and cursor
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Test menu item updates
    updates = {1: 9.99, 2: 12.99}
    result = apply_bulk_updates(mock_connection, updates, 'price', is_option=False)
    assert "Successfully" in result
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    mock_cursor.execute.assert_any_call("""
                    SELECT i.id 
                    FROM items i
                    JOIN categories c ON i.category_id = c.id
                    WHERE i.id IN (1,2)
                    FOR UPDATE OF i, c
                """)
    
    # Test option item updates
    updates = {3: 1.50, 4: 2.00}
    result = apply_bulk_updates(mock_connection, updates, 'price', is_option=True)
    assert "Successfully" in result
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    mock_cursor.execute.assert_any_call("""
                    SELECT oi.id 
                    FROM option_items oi
                    JOIN options o ON oi.option_id = o.id
                    WHERE oi.id IN (3,4)
                    FOR UPDATE OF oi, o
                """)
    
    # Test error handling
    mock_cursor.execute.side_effect = Exception("Test error")
    result = apply_bulk_updates(mock_connection, updates, 'price', is_option=True)
    assert "Error" in result
    mock_connection.rollback.assert_called()

def test_update_side_items():
    """Test updating side items list"""
    # Mock connection and cursor
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Test successful update
    items = ["French Fries", "Sweet Potato Fries", "Onion Rings"]
    result = update_side_items(mock_connection, items)
    assert "Successfully" in result
    
    # Verify all expected calls were made in order
    expected_calls = [
        call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"),
        call("SELECT id FROM options WHERE name = 'Choice of Side' FOR UPDATE"),
        call("UPDATE option_items oi SET disabled = true FROM options o WHERE o.id = oi.option_id AND o.name = 'Choice of Side'")
    ]
    
    # Add insert queries for each item
    for item in items:
        expected_calls.append(
            call("INSERT INTO option_items (name, option_id, price, disabled) SELECT %s, id, 0, false FROM options WHERE name = 'Choice of Side'", (item,))
        )
    
    # Verify calls were made in order
    mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)
    assert mock_cursor.execute.call_count == len(expected_calls)
    
    # Test error handling
    mock_cursor.reset_mock()
    mock_cursor.execute.side_effect = Exception("Test error")
    result = update_side_items(mock_connection, items)
    assert "Error" in result
    mock_connection.rollback.assert_called()

if __name__ == "__main__":
    test_apply_bulk_updates()
    test_update_side_items()
