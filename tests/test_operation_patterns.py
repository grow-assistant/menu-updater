"""Tests for operation pattern matching"""
import pytest
from utils.operation_patterns import match_operation, handle_operation_step

def test_match_operation():
    """Test operation pattern matching"""
    # Test disable patterns
    assert match_operation("disable the menu item") == {
        "type": "disable_item",
        "steps": ["get_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {}
    }
    assert match_operation("turn off item") == {
        "type": "disable_item",
        "steps": ["get_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {}
    }
    assert match_operation("deactivate menu item") == {
        "type": "disable_item",
        "steps": ["get_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {}
    }
    
    assert match_operation("disable the menu option")["type"] == "disable_option"
    assert match_operation("turn off option")["type"] == "disable_option"
    
    # Test option disable patterns
    assert match_operation("disable the menu option") == {
        "type": "disable_option",
        "steps": ["get_option_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Item Option",
        "current_step": 0,
        "params": {}
    }
    
    # Test option item disable patterns
    assert match_operation("disable option item") == {
        "type": "disable_option_item",
        "steps": ["get_option_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Option Item",
        "current_step": 0,
        "params": {}
    }
    
    # Test price update patterns
    assert match_operation("update the price") == {
        "type": "update_price",
        "steps": ["get_item_name", "get_new_price", "confirm_price", "execute_price_update"],
        "function": "update_menu_item_price",
        "item_type": None,
        "current_step": 0,
        "params": {}
    }
    
    # Test time range patterns
    assert match_operation("update time range") == {
        "type": "update_time_range",
        "steps": ["get_category_name", "get_start_time", "get_end_time", "confirm_time_range", "execute_time_update"],
        "function": "update_category_time_range",
        "item_type": None,
        "current_step": 0,
        "params": {}
    }
    
    # Test no match
    assert match_operation("unknown command") is None
    assert match_operation("") is None

def test_handle_operation_step():
    """Test operation step handling"""
    # Test get item name
    operation = {
        "type": "disable_item",
        "steps": ["get_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "item_type": "Menu Item",
        "current_step": 0,
        "params": {}
    }
    
    response = handle_operation_step(operation, "")
    assert response["role"] == "assistant"
    assert "Which menu item?" in response["content"]
    
    # Test confirm disable
    operation["current_step"] = 1
    response = handle_operation_step(operation, "Burger")
    assert response["role"] == "assistant"
    assert "Are you sure" in response["content"]
    assert "Burger" in response["content"]
    
    # Test execute disable
    operation["current_step"] = 2
    response = handle_operation_step(operation, "yes")
    assert response["role"] == "function"
    assert response["name"] == "disable_by_name"
    
    # Test cancel operation
    response = handle_operation_step(operation, "no")
    assert response["role"] == "assistant"
    assert "cancelled" in response["content"]

    # Test price update steps
    operation = {
        "type": "update_price",
        "steps": ["get_item_name", "get_new_price", "confirm_price", "execute_price_update"],
        "function": "update_menu_item_price",
        "current_step": 0,
        "params": {}
    }
    
    response = handle_operation_step(operation, "")
    assert response["role"] == "assistant"
    assert "Which menu item?" in response["content"]
    
    operation["current_step"] = 1
    response = handle_operation_step(operation, "Burger")
    assert response["role"] == "assistant"
    assert "new price" in response["content"].lower()
    
    operation["current_step"] = 2
    response = handle_operation_step(operation, "12.99")
    assert response["role"] == "assistant"
    assert "12.99" in response["content"]
    
    # Test unknown command
    assert match_operation("unknown command") is None
    assert match_operation("") is None
    
    # Test invalid step
    operation["current_step"] = 99
    response = handle_operation_step(operation, "")
    assert response["role"] == "assistant"
    assert "didn't understand" in response["content"].lower()

if __name__ == "__main__":
    pytest.main([__file__])
