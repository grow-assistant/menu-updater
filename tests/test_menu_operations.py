from unittest.mock import MagicMock
from utils.menu_operations import disable_by_name, toggle_menu_item

def test_toggle_menu_item():
    """Test toggling menu item state"""
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Test disable
    success, message = toggle_menu_item("Test Item", True, mock_connection)
    assert success
    assert "Successfully disabled" in message
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    
    # Test enable
    success, message = toggle_menu_item("Test Item", False, mock_connection)
    assert success
    assert "Successfully enabled" in message
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    
    # Test error handling
    mock_cursor.execute.side_effect = Exception("Test error")
    success, message = toggle_menu_item("Test Item", True, mock_connection)
    assert not success
    assert "Error toggling menu item" in message
    assert "Test error" in message

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
    
    # Test option item disable
    items = [{"id": 3, "name": "Test Option Item"}]
    success, message = disable_by_name(mock_connection, "Option Item", items)
    assert success
    assert "Successfully disabled" in message
    mock_cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    mock_cursor.execute.assert_any_call("SELECT id FROM option_items WHERE id IN (3) FOR UPDATE")
    mock_cursor.execute.assert_any_call(
        "UPDATE option_items SET disabled = true WHERE id IN (3)"
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
    test_toggle_menu_item()
    test_disable_by_name()
