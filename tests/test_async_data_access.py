"""
Tests for the asynchronous data access functionality.

These tests verify that the Enhanced Data Access Layer correctly supports
asynchronous operations while maintaining compatibility with synchronous code.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
import pandas as pd
import time
import threading
import asyncio
from datetime import datetime, timedelta
import json
import tempfile
import os

from services.data.db_connection_manager import DatabaseConnectionManager
from services.data.query_cache_manager import QueryCacheManager
from services.data.enhanced_data_access import EnhancedDataAccess, get_data_access


class TestAsyncDataAccess(unittest.TestCase):
    """Tests for the asynchronous functionality in EnhancedDataAccess."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test configuration
        self.test_config = {
            "database": {
                "connection_string": "sqlite:///:memory:",
                "pool_size": 2,
                "max_overflow": 2,
                "pool_timeout": 5,
                "pool_recycle": 300,
                "max_retries": 2,
                "retry_delay": 0.1,
                "default_timeout": 5,
                "application_name": "test_app"
            },
            "cache": {
                "enabled": True,
                "default_ttl": 300,
                "max_size": 1000,
                "non_cacheable_tables": ["audit_log", "user_sessions"],
                "storage_path": None
            },
            "async_mode": True
        }
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_get_event_loop(self, mock_qcm_class, mock_dcm_class):
        """Test that _get_event_loop returns an event loop."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Test getting the event loop
        loop = data_access._get_event_loop()
        
        # Verify the loop is an event loop
        self.assertIsNotNone(loop)
        self.assertTrue(isinstance(loop, asyncio.AbstractEventLoop))
        
        # Test getting the event loop again (should reuse)
        loop2 = data_access._get_event_loop()
        self.assertEqual(loop, loop2)
        
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_extract_tables_from_query(self, mock_qcm_class, mock_dcm_class):
        """Test the extraction of table names from SQL queries."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Test simple query
        query1 = "SELECT * FROM orders WHERE date > '2023-01-01'"
        tables = data_access._extract_tables_from_query(query1)
        self.assertEqual(tables, ["orders"])
        
        # Test join query
        query2 = "SELECT o.id, i.name FROM orders o JOIN items i ON o.item_id = i.id"
        tables = data_access._extract_tables_from_query(query2)
        self.assertEqual(set(tables), {"orders", "o", "items", "i"})
        
        # Test multi-line query
        query3 = """
        SELECT 
            o.id, 
            c.name 
        FROM 
            orders o 
        JOIN 
            customers c ON o.customer_id = c.id
        """
        tables = data_access._extract_tables_from_query(query3)
        self.assertEqual(set(tables), {"orders", "o", "customers", "c"})
    
    @pytest.mark.asyncio
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    async def test_execute_query_async(self, mock_qcm_class, mock_dcm_class):
        """Test the _execute_query_async internal method."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Mock the synchronous execute_query method
        mock_dcm.execute_query.return_value = {
            "success": True,
            "cached": False,
            "data": [{"id": 1, "name": "Test"}],
            "rowcount": 1,
            "execution_time": 0.1,
            "error": None,
            "query_id": "test-id"
        }
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Call the async method
        result = await data_access._execute_query_async(
            sql_query="SELECT * FROM test",
            params={"param": "value"},
            timeout=10
        )
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["rowcount"], 1)
        self.assertEqual(len(result["data"]), 1)
        self.assertTrue("total_time" in result)
        
        # Verify database manager was called correctly
        mock_dcm.execute_query.assert_called_once_with(
            sql_query="SELECT * FROM test",
            params={"param": "value"},
            timeout=10
        )
        
    @pytest.mark.asyncio
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    async def test_query_to_dataframe_async(self, mock_qcm_class, mock_dcm_class):
        """Test the async query_to_dataframe method."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Create test data
        test_data = [{"id": 1, "name": "Test1"}, {"id": 2, "name": "Test2"}]
        
        # Mock cache miss
        mock_qcm.get.return_value = None
        mock_qcm.should_cache_query.return_value = True
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Patch the async execute method
        with patch.object(data_access, '_execute_query_async', new_callable=AsyncMock) as mock_execute:
            # Configure mock to return test data
            mock_execute.return_value = {
                "success": True,
                "cached": False,
                "data": test_data,
                "rowcount": len(test_data),
                "execution_time": 0.1,
                "total_time": 0.2,
                "error": None,
                "query_id": "test-query-id"
            }
            
            # Test async query execution
            sql_query = "SELECT * FROM test_table"
            params = {"param1": "value1"}
            
            df, metadata = await data_access.query_to_dataframe_async(
                sql_query=sql_query,
                params=params,
                use_cache=True
            )
            
            # Verify the result
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[0]["name"], "Test1")
            self.assertEqual(df.iloc[1]["name"], "Test2")
            
            # Verify metadata
            self.assertTrue(metadata["success"])
            self.assertFalse(metadata["cached"])
            self.assertEqual(metadata["rowcount"], 2)
            self.assertIsNone(metadata["error"])
            
            # Verify the cache was set
            mock_qcm.generate_cache_key.assert_called_with(sql_query, params)
            mock_qcm.set.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    async def test_query_to_dataframe_async_cache_hit(self, mock_qcm_class, mock_dcm_class):
        """Test async query_to_dataframe with cache hit."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Create test data
        test_data = [{"id": 1, "name": "Test1"}, {"id": 2, "name": "Test2"}]
        
        # Mock cache hit
        cached_result = {
            "success": True,
            "cached": True,
            "data": test_data,
            "rowcount": len(test_data),
            "execution_time": 0.1,
            "total_time": 0.2,
            "error": None,
            "query_id": "test-query-id"
        }
        mock_qcm.get.return_value = cached_result
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Mock execute_query_async to verify it's not called
        execute_async_mock = AsyncMock()
        data_access._execute_query_async = execute_async_mock
        
        # Test async query execution with cache hit
        sql_query = "SELECT * FROM test_table"
        params = {"param1": "value1"}
        
        df, metadata = await data_access.query_to_dataframe_async(
            sql_query=sql_query,
            params=params,
            use_cache=True
        )
        
        # Verify the result
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["name"], "Test1")
        self.assertEqual(df.iloc[1]["name"], "Test2")
        
        # Verify metadata shows cached
        self.assertTrue(metadata["success"])
        self.assertTrue(metadata["cached"])
        
        # Verify the database was not queried
        execute_async_mock.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    async def test_query_to_dataframe_async_error(self, mock_qcm_class, mock_dcm_class):
        """Test handling of errors in async query_to_dataframe."""
        # Setup mocks
        mock_dcm = mock_dcm_class.return_value
        mock_qcm = mock_qcm_class.return_value
        
        # Mock cache miss
        mock_qcm.get.return_value = None
        
        # Create EnhancedDataAccess instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Patch the async execute method to raise an exception
        with patch.object(data_access, '_execute_query_async', new_callable=AsyncMock) as mock_execute:
            error_message = "Database connection error"
            mock_execute.side_effect = Exception(error_message)
            
            # Test async query execution with error
            sql_query = "SELECT * FROM test_table"
            
            df, metadata = await data_access.query_to_dataframe_async(
                sql_query=sql_query,
                use_cache=True
            )
            
            # Verify the result is an empty DataFrame
            self.assertEqual(len(df), 0)
            
            # Verify metadata
            self.assertFalse(metadata["success"])
            self.assertFalse(metadata["cached"])
            self.assertEqual(metadata["rowcount"], 0)
            self.assertIn(error_message, metadata["error"])


if __name__ == '__main__':
    unittest.main() 