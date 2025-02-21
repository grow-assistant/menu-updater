"""Tests for operation pattern matching"""
import pytest
from utils.operation_patterns import match_operation, handle_operation_step

def test_match_operation():
    """Test operation pattern matching"""
    # Test disable patterns
    assert match_operation("disable the menu item")["type"] == "disable_item"
    assert match_operation("turn off item")["type"] == "disable_item"
    assert match_operation("deactivate menu item")["type"] == "disable_item"
    
    assert match_operation("disable the menu option")["type"] == "disable_option"
    assert match_operation("turn off option")["type"] == "disable_option"
    
    assert match_operation("disable option item")["type"] == "disable_option_item"
    assert match_operation("turn off option item")["type"] == "disable_option_item"
    
    # Test price update patterns
    assert match_operation("update the price")["type"] == "update_price"
    assert match_operation("change price")["type"] == "update_price"
    assert match_operation("set price")["type"] == "update_price"
    
    # Test time range patterns
    assert match_operation("update time range")["type"] == "update_time_range"
    assert match_operation("change the time range")["type"] == "update_time_range"
    
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

if __name__ == "__main__":
    pytest.main([__file__])
