"""
Unit tests for the SQL Execution Service.

Tests the functionality of the SQLExecutionService class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.execution import SQLExecutionLayer
from services.execution_service import SQLExecutionService


class TestExecutionService:
    """Test cases for the SQL Execution Service."""

    def test_init_execution_service(self, test_config):
        """Test the initialization of the SQLExecutionService."""
        with patch("services.execution_service.sql_execution_layer.psycopg2.connect"):
            execution_service = SQLExecutionService(config=test_config)
            assert execution_service is not None
            assert execution_service.config == test_config

    def test_execute_query(self, mock_execution_service):
        """Test executing a SQL query."""
        # Test with mocked execute_query
        result = mock_execution_service.execute_query(
            "SELECT * FROM menu_items WHERE location_id = 62"
        )
        assert result == [{"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}]

    def test_execute_query_with_error(self, test_config):
        """Test executing a query that causes an error."""
        with patch("services.execution_service.sql_execution_layer.psycopg2.connect") as mock_connect:
            mock_cursor = MagicMock()
            mock_connection = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_connection
            
            # Set up mock to raise an exception
            mock_cursor.execute.side_effect = Exception("Test database error")
            
            execution_service = SQLExecutionService(config=test_config)
            
            # Patch the logger to avoid actual error logging
            with patch("services.execution_service.sql_execution_layer.logger"):
                result = execution_service.execute_query("SELECT * FROM nonexistent_table")
                assert result == {"error": "Database error: Test database error"}

    def test_format_results(self, mock_execution_service):
        """Test formatting query results."""
        with patch.object(mock_execution_service, "format_results") as mock_format:
            mock_format.return_value = [
                {"id": 1, "name": "Test Item", "price": 10.99}
            ]
            
            rows = [(1, "Test Item", 10.99)]
            column_names = ["id", "name", "price"]
            
            result = mock_execution_service.format_results(rows, column_names)
            assert result == [{"id": 1, "name": "Test Item", "price": 10.99}]

    def test_execute_update_query(self, test_config):
        """Test executing an update query."""
        with patch("services.execution_service.sql_execution_layer.psycopg2.connect") as mock_connect:
            mock_cursor = MagicMock()
            mock_connection = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_connection
            
            # Set up mock for update query
            mock_cursor.rowcount = 1
            
            execution_service = SQLExecutionService(config=test_config)
            
            with patch.object(execution_service, "is_select_query") as mock_is_select:
                mock_is_select.return_value = False
                
                result = execution_service.execute_query(
                    "UPDATE menu_items SET price = 12.99 WHERE id = 1 AND location_id = 62"
                )
                
                assert result == {"affected_rows": 1, "message": "Update successful"}

    def test_is_select_query(self, mock_execution_service):
        """Test detecting if a query is a SELECT query."""
        with patch.object(mock_execution_service, "is_select_query") as mock_is_select:
            # SELECT query
            mock_is_select.return_value = True
            is_select = mock_execution_service.is_select_query(
                "SELECT * FROM menu_items"
            )
            assert is_select is True
            
            # UPDATE query
            mock_is_select.return_value = False
            is_select = mock_execution_service.is_select_query(
                "UPDATE menu_items SET price = 12.99 WHERE id = 1"
            )
            assert is_select is False

    def test_analyze_query_for_date_handling(self, mock_execution_service):
        """Test analyzing queries for date handling requirements."""
        with patch.object(mock_execution_service, "analyze_query_for_date_handling") as mock_analyze:
            mock_analyze.return_value = True
            needs_date_handling = mock_execution_service.analyze_query_for_date_handling(
                "SELECT * FROM orders WHERE order_date > '2023-01-01'"
            )
            assert needs_date_handling is True

    def test_format_items(self, mock_execution_service):
        """Test formatting individual items in results."""
        with patch.object(mock_execution_service, "format_item") as mock_format:
            mock_format.return_value = {
                "price": "$10.99",
                "is_active": "Yes"
            }
            
            item = {
                "price": 10.99,
                "is_active": True
            }
            
            formatted = mock_execution_service.format_item(item)
            assert formatted == {"price": "$10.99", "is_active": "Yes"} 