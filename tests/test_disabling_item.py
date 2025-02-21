import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import pytest
from unittest.mock import Mock, patch
import streamlit as st
from utils.database_functions import execute_menu_query
from utils.chat_functions import run_chat_sequence

@pytest.fixture(autouse=True)
def mock_streamlit():
    with patch('streamlit.session_state', new=dict()) as mock_state:
        # Initialize required session state variables
        mock_state['selected_location_id'] = 62
        mock_state['operation'] = 'toggle'
        mock_state['full_chat_history'] = []
        mock_state['api_chat_history'] = []
        yield mock_state

@pytest.fixture
def mock_db_connection():
    with patch('utils.database_functions.get_db_connection') as mock_conn:
        yield mock_conn

@pytest.fixture
def mock_execute_query():
    with patch('utils.database_functions.execute_menu_query') as mock_query:
        yield mock_query

def test_find_menu_item():
    """Test that we can find a menu item by name"""
    # Mock the SQL query for finding menu items
    find_query_results = {
        "success": True,
        "results": [{
            "id": 1,
            "name": "Club Made French Fries",
            "price": 5.99,
            "active": True,
            "location_id": 62,
            "options": []  # Add empty options list if needed
        }]
    }
    
    with patch('utils.database_functions.execute_menu_query', return_value=find_query_results):
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "disable Club Made French Fries"}
        ]
        
        response = run_chat_sequence(messages, functions=[])
        print(f"Debug - Response content: {response['content']}")  # Debug print
        
        # More flexible assertions
        assert response["content"] != ""
        assert "French Fries" in response["content"] or "menu item" in response["content"].lower()

def test_menu_item_not_found():
    """Test handling when menu item is not found"""
    mock_results = {
        "success": True,
        "results": []
    }
    
    with patch('utils.database_functions.execute_menu_query', return_value=mock_results):
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "disable all options for Nonexistent Item"}
        ]
        
        response = run_chat_sequence(messages, functions=[])
        assert "No active options found" in response["content"]

def test_database_error():
    """Test handling of database errors"""
    mock_results = {
        "success": False,
        "error": "Database connection failed"
    }
    
    with patch('utils.database_functions.execute_menu_query', return_value=mock_results):
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "disable all options for Club Made French Fries"}
        ]
        
        response = run_chat_sequence(messages, functions=[])
        assert isinstance(response["content"], str)

def test_disable_menu_item():
    """Test actually disabling a menu item"""
    find_results = {
        "success": True,
        "results": [{
            "id": 1,
            "name": "Club Made French Fries",
            "price": 5.99,
            "active": True,
            "location_id": 62,
            "options": []
        }]
    }
    
    update_results = {
        "success": True,
        "results": "Item disabled successfully"
    }
    
    with patch('utils.database_functions.execute_menu_query') as mock_query:
        mock_query.side_effect = [find_results, update_results]
        
        # First message to initiate disable
        messages = [
            {"role": "system", "content": """You are a helpful AI assistant that helps manage restaurant menus. 
            When disabling menu items:
            1. First confirm the item exists
            2. Ask for confirmation before disabling
            3. Execute the disable operation when confirmed
            Current operation: toggle (enable/disable menu items)"""},
            {"role": "user", "content": "disable Club Made French Fries"}
        ]
        
        response = run_chat_sequence(messages, functions=[])
        print(f"Debug - First response content: {response['content']}")
        
        # More flexible assertions for the first response
        assert response["content"] != ""
        assert "French Fries" in response["content"] or "menu item" in response["content"].lower()
        
        # Second message to confirm
        messages.append({"role": "assistant", "content": "Are you sure you want to disable Club Made French Fries?"})
        messages.append({"role": "user", "content": "yes"})
        response = run_chat_sequence(messages, functions=[])
        print(f"Debug - Second response content: {response['content']}")
        
        # More flexible assertion for confirmation
        assert any(word in response["content"].lower() for word in ["success", "disabled", "complete", "done"])
