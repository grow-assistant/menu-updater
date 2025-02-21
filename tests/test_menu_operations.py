import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.menu_operations import disable_by_name

def test_disable_by_name():
    """Test disabling items/options by name"""
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Test item disable
    items = [{"id": 1, "name": "Test Item"}]
    success, message = disable_by_name(mock_connection, "Menu Item", items)
    assert success
    assert "Successfully disabled" in message
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    mock_cursor.execute.assert_any_call("SELECT id FROM items WHERE id IN (1) FOR UPDATE")
    mock_cursor.execute.assert_any_call(
        "UPDATE items SET disabled = true WHERE id IN (1)"
    )
    
    # Test option disable
    items = [{"id": 2, "name": "Test Option"}]
    success, message = disable_by_name(mock_connection, "Item Option", items)
    assert success
    assert "Successfully disabled" in message
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    mock_cursor.execute.assert_any_call("SELECT id FROM options WHERE id IN (2) FOR UPDATE")
    mock_cursor.execute.assert_any_call(
        "UPDATE options SET disabled = true WHERE id IN (2)"
    )
    
    # Test multiple items
    items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
    success, message = disable_by_name(mock_connection, "Menu Item", items)
    assert success
    assert "Successfully disabled" in message
    mock_cursor.execute.assert_any_call("SELECT id FROM items WHERE id IN (1,2) FOR UPDATE")
    mock_cursor.execute.assert_any_call(
        "UPDATE items SET disabled = true WHERE id IN (1,2)"
    )
    
    # Test error handling
    mock_cursor.execute.side_effect = Exception("Test error")
    success, message = disable_by_name(mock_connection, "Menu Item", items)
    assert not success
    assert "Error disabling" in message
    assert "Test error" in message

if __name__ == "__main__":
    test_disable_by_name()
