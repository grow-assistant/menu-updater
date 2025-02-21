"""Tests for query-execute-respond cycle"""
import pytest
from unittest.mock import patch, MagicMock
from tests.mocks import mock_database, mock_openai
from utils.database_functions import execute_menu_query, process_query_results

# Mock dependencies
mock_openai()

@patch("utils.database_functions.get_db_connection")
def test_execute_menu_query_success(mock_get_conn):
    """Test successful query execution"""
    # Setup mock
    mock_connection, mock_cursor = mock_database()
    mock_cursor.description = [("name",), ("price",)]
    mock_cursor.fetchall.return_value = [("Item 1", 10.99), ("Item 2", 12.99)]
    mock_get_conn.return_value = mock_connection

    # Execute test
    result = execute_menu_query("SELECT name, price FROM items")
    
    assert result["success"] is True
    assert result["columns"] == ["name", "price"]
    assert len(result["results"]) == 2
    assert result["results"][0]["name"] == "Item 1"
    assert result["results"][0]["price"] == 10.99

@patch("utils.database_functions.get_db_connection")
def test_execute_menu_query_error(mock_get_conn):
    """Test query execution error"""
    # Setup mock to raise exception
    mock_get_conn.side_effect = Exception("Database error")

    # Execute test
    result = execute_menu_query("SELECT * FROM nonexistent")
    
    assert result["success"] is False
    assert "Database error" in result["error"]

@patch("openai.ChatCompletion.create")
def test_process_query_results_success(mock_openai):
    """Test successful results processing"""
    # Setup mock
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message={"content": "Found 2 items: Item 1 ($10.99) and Item 2 ($12.99)"})
    ]
    mock_openai.return_value = mock_response

    # Test data
    results = {
        "success": True,
        "query": "SELECT name, price FROM items",
        "columns": ["name", "price"],
        "results": [
            {"name": "Item 1", "price": 10.99},
            {"name": "Item 2", "price": 12.99}
        ]
    }

    response = process_query_results(results)
    assert "Found 2 items" in response

def test_process_query_results_error():
    """Test error results processing"""
    results = {
        "success": False,
        "error": "Table not found",
        "query": "SELECT * FROM nonexistent"
    }

    response = process_query_results(results)
    assert "Error executing query" in response
