"""
Unit tests for the SQL Execution Service.

Tests the functionality of the SQLExecutionLayer class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from services.execution.sql_execution_layer import SQLExecutionLayer


class TestExecutionService:
    """Test cases for the SQL Execution Service."""

    def test_init_execution_service(self, test_config):
        """Test the initialization of the SQLExecutionLayer."""
        execution_service = SQLExecutionLayer()
        assert execution_service is not None
        assert execution_service.max_rows == 1000
        assert execution_service.timeout == 10

    @pytest.mark.asyncio
    async def test_execute_query(self):
        """Test executing a SQL query."""
        # Mock the get_db_connection context manager directly
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        
        with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
            # Mock the execute_query_with_connection function
            with patch("services.execution.db_utils._execute_query_with_connection") as mock_execute:
                # Configure the mock to return test data
                test_data = [
                    {"id": 1, "name": "Test Item 1", "price": 9.99},
                    {"id": 2, "name": "Test Item 2", "price": 14.99}
                ]
                
                mock_execute.return_value = test_data
                
                # Create the execution service
                execution_service = SQLExecutionLayer()
                
                # Call the method under test
                result = await execution_service.execute_sql(
                    "SELECT * FROM menu_items WHERE location_id = 62"
                )
                
                # Verify the results
                assert result["success"] is True
                assert result["data"] is not None
                assert result["row_count"] == 2

    @pytest.mark.asyncio
    async def test_execute_query_with_error(self):
        """Test executing a query that causes an error."""
        # Mock the get_db_connection context manager directly
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        
        with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
            # Mock the execute_query_with_connection function to raise an exception
            with patch("services.execution.db_utils._execute_query_with_connection") as mock_execute:
                # Set up mock to raise an exception
                mock_execute.side_effect = Exception("Test database error")
                
                # Create the execution service
                execution_service = SQLExecutionLayer()
                
                # Call the method under test
                result = await execution_service.execute_sql("SELECT * FROM nonexistent_table")
                
                # Verify error handling
                assert result["success"] is False
                assert "Test database error" in result["error"]
                assert result["data"] is None

    @pytest.mark.asyncio
    async def test_format_results(self):
        """Test formatting query results."""
        # Mock the get_db_connection context manager directly
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        
        with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
            # Mock the execute_query_with_connection function
            with patch("services.execution.db_utils._execute_query_with_connection") as mock_execute:
                # Configure the mocks
                test_data = [
                    {"id": 1, "name": "Test Item", "price": 10.99}
                ]
                mock_execute.return_value = test_data
                
                # Create the execution service
                execution_service = SQLExecutionLayer()
                
                # Call the method under test
                result = await execution_service.execute_sql(
                    "SELECT * FROM menu_items",
                    format_type="json"  # Use json format which is supported
                )
                
                # Verify the results
                assert result["success"] is True
                assert "execution_time" in result
                assert result["row_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_update_query(self):
        """Test executing an update query."""
        # Mock the get_db_connection context manager directly
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        
        with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
            # Mock the execute_query_with_connection function
            with patch("services.execution.db_utils._execute_query_with_connection") as mock_execute:
                # Configure the mock to return empty list for UPDATE
                mock_execute.return_value = []
                
                # Create the execution service
                execution_service = SQLExecutionLayer()
                
                # Call the method under test
                result = await execution_service.execute_sql(
                    "UPDATE menu_items SET price = 12.99 WHERE id = 1 AND location_id = 62"
                )
                
                # Verify the results for an update query
                assert result["success"] is True
                assert result["row_count"] == 0
                assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_transaction_queries(self):
        """Test executing transaction queries."""
        # Mock the get_db_connection context manager
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        
        # Direct patching of the internal transaction function
        with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
            with patch("services.execution.db_utils._execute_transaction_with_connection", new_callable=AsyncMock) as mock_exec_trans:
                # Configure the mock to succeed
                mock_exec_trans.return_value = None
                
                # Create the execution service
                execution_service = SQLExecutionLayer()
                
                # Create test queries
                queries = [
                    ("UPDATE menu_items SET price = 12.99 WHERE id = 1", []),
                    ("UPDATE menu_items SET price = 14.99 WHERE id = 2", [])
                ]
                
                # Call the method under test
                result = await execution_service.execute_transaction_queries(queries)
                
                # Verify the results
                assert result["success"] is True
                assert result["query_count"] == 2
                assert "execution_time" in result
                # Verify the mock was called
                mock_exec_trans.assert_called_once()

    def test_add_limit_clause(self):
        """Test adding a LIMIT clause to queries."""
        execution_service = SQLExecutionLayer()
        
        # Test adding LIMIT to a query without one
        query_without_limit = "SELECT * FROM menu_items"
        query_with_added_limit = execution_service._add_limit_if_needed(query_without_limit, 100)
        assert "LIMIT 100" in query_with_added_limit
        
        # Test not modifying a query that already has a LIMIT
        query_with_limit = "SELECT * FROM menu_items LIMIT 50"
        query_unchanged = execution_service._add_limit_if_needed(query_with_limit, 100)
        assert query_unchanged == query_with_limit 