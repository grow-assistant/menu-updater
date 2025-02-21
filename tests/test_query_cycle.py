"""Tests for query-execute-respond cycle"""
import pytest
from unittest.mock import patch, MagicMock
from utils.database_functions import execute_menu_query, process_query_results

def test_execute_menu_query_success():
    """Test successful query execution"""
    with patch("utils.database_functions.get_db_connection") as mock_get_conn:
        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.description = [("name",), ("price",)]
        mock_cursor.fetchall.return_value = [("Item 1", 10.99), ("Item 2", 12.99)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Execute test
        result = execute_menu_query("SELECT name, price FROM items")
        
        assert result["success"] is True
        assert result["columns"] == ["name", "price"]
        assert len(result["results"]) == 2
        assert result["results"][0]["name"] == "Item 1"
        assert result["results"][0]["price"] == 10.99

def test_execute_menu_query_error():
    """Test query execution error"""
    with patch("utils.database_functions.get_db_connection") as mock_get_conn:
        # Setup mock to raise exception
        mock_get_conn.side_effect = Exception("Database error")

        # Execute test
        result = execute_menu_query("SELECT * FROM nonexistent")
        
        assert result["success"] is False
        assert "Database error" in result["error"]

def test_process_query_results_success():
    """Test successful results processing"""
    with patch("openai.ChatCompletion.create") as mock_openai:
        # Setup mock
        mock_openai.return_value.choices = [
            MagicMock(message={"content": "Found 2 items: Item 1 ($10.99) and Item 2 ($12.99)"})
        ]

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
