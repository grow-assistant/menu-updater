"""
Tests for the Enhanced Data Access Layer.

These tests validate the functionality of the database connection manager,
query cache manager, and enhanced data access components.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
import time
import threading
from datetime import datetime, timedelta
import json
import tempfile
import os

from services.data.db_connection_manager import DatabaseConnectionManager
from services.data.query_cache_manager import QueryCacheManager
from services.data.enhanced_data_access import EnhancedDataAccess, get_data_access


class TestDatabaseConnectionManager(unittest.TestCase):
    """Tests for the DatabaseConnectionManager class."""
    
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
            }
        }
        
        # Create a mock engine for certain tests
        self.mock_engine = Mock()
        self.mock_connection = Mock()
        self.mock_engine.connect.return_value = self.mock_connection
        
    @patch('services.data.db_connection_manager.create_engine')
    def test_init(self, mock_create_engine):
        """Test initialization with valid configuration."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        
        # Act
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Assert
        mock_create_engine.assert_called_once()
        assert db_manager.connection_string == "sqlite:///:memory:"
        assert db_manager.max_retries == 2
        assert db_manager.default_timeout == 5
    
    def test_init_missing_connection_string(self):
        """Test initialization with missing connection string."""
        # Arrange
        bad_config = {"database": {}}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Database connection string not provided"):
            DatabaseConnectionManager(bad_config)
    
    @patch('services.data.db_connection_manager.create_engine')
    def test_get_connection(self, mock_create_engine):
        """Test get_connection context manager."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Act
        with db_manager.get_connection() as conn:
            pass
        
        # Assert
        self.mock_engine.connect.assert_called_once()
        self.mock_connection.close.assert_called_once()
    
    @patch('services.data.db_connection_manager.create_engine')
    def test_get_connection_exception(self, mock_create_engine):
        """Test get_connection context manager with exception."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Mock connection raising an exception
        self.mock_connection.execute.side_effect = Exception("Test exception")
        
        # Act & Assert
        with pytest.raises(Exception):
            with db_manager.get_connection() as conn:
                conn.execute("SELECT 1")
        
        # Verify connection was closed
        self.mock_connection.close.assert_called_once()
    
    @patch('services.data.db_connection_manager.create_engine')
    @patch('services.data.db_connection_manager.pd.read_sql')
    def test_execute_with_timeout_select(self, mock_read_sql, mock_create_engine):
        """Test _execute_with_timeout with SELECT query."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Setup mock for read_sql
        mock_df = pd.DataFrame({"test": [1, 2, 3]})
        mock_read_sql.return_value = mock_df
        
        # Act
        result = db_manager._execute_with_timeout("SELECT * FROM test", {}, 5)
        
        # Assert
        assert isinstance(result, pd.DataFrame)
        assert result.equals(mock_df)
        mock_read_sql.assert_called_once()
    
    @patch('services.data.db_connection_manager.create_engine')
    @patch('services.data.db_connection_manager.text')
    def test_execute_with_timeout_non_select(self, mock_text, mock_create_engine):
        """Test _execute_with_timeout with non-SELECT query."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Setup mock for text
        mock_text.return_value = "INSERT INTO test VALUES (:value)"
        
        # Setup mock result
        mock_result = Mock()
        mock_result.rowcount = 5
        self.mock_connection.execute.return_value = mock_result
        
        # Act
        result = db_manager._execute_with_timeout(
            "INSERT INTO test VALUES (:value)", 
            {"value": "test"}, 
            5
        )
        
        # Assert
        assert result == 5
        self.mock_connection.execute.assert_called_once()
    
    @patch('services.data.db_connection_manager.create_engine')
    def test_execute_query_success(self, mock_create_engine):
        """Test execute_query with successful execution."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Create a partial mock to replace _execute_with_timeout
        db_manager._execute_with_timeout = Mock()
        mock_df = pd.DataFrame({"test": [1, 2, 3]})
        db_manager._execute_with_timeout.return_value = mock_df
        
        # Act
        result = db_manager.execute_query("SELECT * FROM test")
        
        # Assert
        assert result["success"] is True
        assert len(result["data"]) == 3
        assert result["rowcount"] == 3
        assert result["execution_time"] > 0
    
    @patch('services.data.db_connection_manager.create_engine')
    def test_execute_query_failure(self, mock_create_engine):
        """Test execute_query with failure."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Create a partial mock to replace _execute_with_timeout
        db_manager._execute_with_timeout = Mock()
        db_manager._execute_with_timeout.side_effect = Exception("Test exception")
        
        # Act
        result = db_manager.execute_query("SELECT * FROM test")
        
        # Assert
        assert result["success"] is False
        assert "Test exception" in result["error"]
        assert result["execution_time"] > 0
    
    @patch('services.data.db_connection_manager.create_engine')
    def test_is_select_query(self, mock_create_engine):
        """Test _is_select_query method."""
        # Arrange
        mock_create_engine.return_value = self.mock_engine
        db_manager = DatabaseConnectionManager(self.test_config)
        
        # Test cases
        test_cases = [
            ("SELECT * FROM test", True),
            ("select id from users", True),
            ("SELECT * FROM test -- with comment", True),
            ("/*comment*/ SELECT * FROM test", True),
            ("INSERT INTO test VALUES (1)", False),
            ("UPDATE test SET value = 1", False),
            ("DELETE FROM test", False),
        ]
        
        # Act & Assert
        for query, expected in test_cases:
            assert db_manager._is_select_query(query) == expected


class TestQueryCacheManager(unittest.TestCase):
    """Tests for the QueryCacheManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test configuration
        self.test_config = {
            "cache": {
                "enabled": True,
                "default_ttl": 60,
                "max_size": 100,
                "max_memory_mb": 10,
                "min_query_time": 0.01,
                "cacheable_tables": ["users", "orders"],
                "uncacheable_tables": ["logs", "sessions"]
            }
        }
        
        self.cache_manager = QueryCacheManager(self.test_config)
    
    def test_init(self):
        """Test initialization with valid configuration."""
        # Assert
        assert self.cache_manager.enabled is True
        assert self.cache_manager.default_ttl == 60
        assert self.cache_manager.max_size == 100
        assert "users" in self.cache_manager.cacheable_tables
        assert "logs" in self.cache_manager.uncacheable_tables
    
    def test_should_cache_query(self):
        """Test _should_cache_query method."""
        # Test cases
        test_cases = [
            ("SELECT * FROM users WHERE id = 1", True),
            ("SELECT * FROM orders LIMIT 10", True),
            ("SELECT * FROM logs WHERE date > '2023-01-01'", False),
            ("SELECT * FROM sessions", False),
            ("SELECT * FROM customers", True),  # Not in lists, so cacheable
        ]
        
        # Act & Assert
        for query, expected in test_cases:
            assert self.cache_manager._should_cache_query(query) == expected
    
    def test_generate_cache_key(self):
        """Test _generate_cache_key method."""
        # Test cases
        query1 = "SELECT * FROM users WHERE id = :id"
        params1 = {"id": 1}
        query2 = "SELECT * FROM users WHERE id = :id"
        params2 = {"id": 2}
        
        # Act
        key1 = self.cache_manager._generate_cache_key(query1, params1)
        key2 = self.cache_manager._generate_cache_key(query1, params2)
        key3 = self.cache_manager._generate_cache_key(query1, params1)
        
        # Assert
        assert isinstance(key1, str)
        assert len(key1) > 0
        assert key1 != key2  # Different params should yield different keys
        assert key1 == key3  # Same query and params should yield same key
    
    def test_set_and_get(self):
        """Test setting and getting cache entries."""
        # Arrange
        query = "SELECT * FROM users WHERE active = :active"
        params = {"active": True}
        data = [{"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]
        
        # Act - Set
        self.cache_manager.set(
            query=query,
            params=params,
            result=data,
            is_select=True,
            execution_time=0.1
        )
        
        # Act - Get
        hit, result = self.cache_manager.get(query, params)
        
        # Assert
        assert hit is True
        assert result == data
        assert self.cache_manager.stats["hits"] == 1
        assert self.cache_manager.stats["misses"] == 0
    
    def test_cache_miss(self):
        """Test cache miss behavior."""
        # Arrange
        query = "SELECT * FROM users WHERE id = :id"
        params = {"id": 999}
        
        # Act
        hit, result = self.cache_manager.get(query, params)
        
        # Assert
        assert hit is False
        assert result is None
        assert self.cache_manager.stats["hits"] == 0
        assert self.cache_manager.stats["misses"] == 1
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        # Arrange
        query = "SELECT * FROM users LIMIT 10"
        data = [{"id": i, "name": f"User {i}"} for i in range(10)]
        
        # Act - Set with short TTL
        self.cache_manager.set(
            query=query,
            params=None,
            result=data,
            is_select=True,
            execution_time=0.1,
            ttl=1  # 1 second TTL
        )
        
        # Act - Get immediately (should hit)
        hit1, result1 = self.cache_manager.get(query, None)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Act - Get after expiration (should miss)
        hit2, result2 = self.cache_manager.get(query, None)
        
        # Assert
        assert hit1 is True
        assert result1 == data
        assert hit2 is False
        assert result2 is None
        assert self.cache_manager.stats["hits"] == 1
        assert self.cache_manager.stats["misses"] == 1
    
    def test_invalidate_by_table(self):
        """Test invalidating cache entries by table name."""
        # Arrange
        queries = [
            ("SELECT * FROM users WHERE id = 1", None),
            ("SELECT * FROM orders WHERE user_id = 1", None),
            ("SELECT * FROM products WHERE active = TRUE", None)
        ]
        
        # Add to cache
        for query, params in queries:
            self.cache_manager.set(
                query=query,
                params=params,
                result=[{"value": "test"}],
                is_select=True,
                execution_time=0.1
            )
        
        # Act - Invalidate users table
        invalidated = self.cache_manager.invalidate(table_name="users")
        
        # Assert
        assert invalidated == 1
        
        # Check which entries remain
        hit1, _ = self.cache_manager.get(queries[0][0], None)
        hit2, _ = self.cache_manager.get(queries[1][0], None)
        hit3, _ = self.cache_manager.get(queries[2][0], None)
        
        assert hit1 is False  # users query should be gone
        assert hit2 is True   # orders query should remain
        assert hit3 is True   # products query should remain
    
    def test_invalidate_complete(self):
        """Test complete cache invalidation."""
        # Arrange
        queries = [
            ("SELECT * FROM users WHERE id = 1", None),
            ("SELECT * FROM orders WHERE user_id = 1", None),
        ]
        
        # Add to cache
        for query, params in queries:
            self.cache_manager.set(
                query=query,
                params=params,
                result=[{"value": "test"}],
                is_select=True,
                execution_time=0.1
            )
        
        # Act - Invalidate everything
        invalidated = self.cache_manager.invalidate(complete=True)
        
        # Assert
        assert invalidated == 2
        
        # Check that nothing remains
        hit1, _ = self.cache_manager.get(queries[0][0], None)
        hit2, _ = self.cache_manager.get(queries[1][0], None)
        
        assert hit1 is False
        assert hit2 is False


class TestEnhancedDataAccess(unittest.TestCase):
    """Tests for the EnhancedDataAccess class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test configuration
        self.test_config = {
            "database": {
                "connection_string": "sqlite:///:memory:",
                "pool_size": 2,
                "max_retries": 2
            },
            "cache": {
                "enabled": True,
                "default_ttl": 60,
                "max_size": 100
            }
        }
        
        # Create mocks for components
        self.mock_db_manager = MagicMock()
        self.mock_cache_manager = MagicMock()
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_init(self, mock_qcm_class, mock_dcm_class):
        """Test initialization."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Act
        data_access = EnhancedDataAccess(self.test_config)
        
        # Assert
        mock_dcm_class.assert_called_once_with(self.test_config)
        mock_qcm_class.assert_called_once_with(self.test_config)
        assert data_access.db_manager == self.mock_db_manager
        assert data_access.cache_manager == self.mock_cache_manager
        assert data_access._transaction_depth == 0
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_execute_query_cache_hit(self, mock_qcm_class, mock_dcm_class):
        """Test execute_query with cache hit."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Set up cache hit
        self.mock_cache_manager.get.return_value = (True, [{"id": 1, "name": "Test"}])
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Act
        result = data_access.execute_query(
            sql_query="SELECT * FROM test WHERE id = :id",
            params={"id": 1},
            use_cache=True
        )
        
        # Assert
        self.mock_cache_manager.get.assert_called_once()
        self.mock_db_manager.execute_query.assert_not_called()  # DB should not be called
        assert result["success"] is True
        assert result["cached"] is True
        assert result["data"] == [{"id": 1, "name": "Test"}]
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_execute_query_cache_miss(self, mock_qcm_class, mock_dcm_class):
        """Test execute_query with cache miss and DB success."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Set up cache miss and DB success
        self.mock_cache_manager.get.return_value = (False, None)
        self.mock_db_manager.execute_query.return_value = {
            "success": True,
            "is_select": True,
            "data": [{"id": 1, "name": "Test"}],
            "rowcount": 1,
            "execution_time": 0.1,
            "error": None
        }
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Act
        result = data_access.execute_query(
            sql_query="SELECT * FROM test WHERE id = :id",
            params={"id": 1},
            use_cache=True
        )
        
        # Assert
        self.mock_cache_manager.get.assert_called_once()
        self.mock_db_manager.execute_query.assert_called_once()
        self.mock_cache_manager.set.assert_called_once()  # Should store in cache
        assert result["success"] is True
        assert result["cached"] is False
        assert result["data"] == [{"id": 1, "name": "Test"}]
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_execute_query_no_cache(self, mock_qcm_class, mock_dcm_class):
        """Test execute_query with cache disabled."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Set up DB success
        self.mock_db_manager.execute_query.return_value = {
            "success": True,
            "is_select": True,
            "data": [{"id": 1, "name": "Test"}],
            "rowcount": 1,
            "execution_time": 0.1,
            "error": None
        }
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Act
        result = data_access.execute_query(
            sql_query="SELECT * FROM test WHERE id = :id",
            params={"id": 1},
            use_cache=False  # Disable cache
        )
        
        # Assert
        self.mock_cache_manager.get.assert_not_called()  # Cache should not be checked
        self.mock_db_manager.execute_query.assert_called_once()
        self.mock_cache_manager.set.assert_not_called()  # Should not store in cache
        assert result["success"] is True
        assert result["cached"] is False
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_query_to_dataframe(self, mock_qcm_class, mock_dcm_class):
        """Test query_to_dataframe method."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Create a partial mock to replace execute_query
        data_access = EnhancedDataAccess(self.test_config)
        data_access.execute_query = Mock()
        data_access.execute_query.return_value = {
            "success": True,
            "data": [{"id": 1, "name": "Test"}, {"id": 2, "name": "Test2"}],
            "cached": False,
            "execution_time": 0.1,
            "total_time": 0.2,
            "rowcount": 2,
            "error": None,
            "query_id": "q-12345"
        }
        
        # Act
        df, metadata = data_access.query_to_dataframe(
            sql_query="SELECT * FROM test",
            use_cache=True
        )
        
        # Assert
        data_access.execute_query.assert_called_once()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert metadata["success"] is True
        assert metadata["query_id"] == "q-12345"
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_transactions(self, mock_qcm_class, mock_dcm_class):
        """Test transaction management."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Act - Begin transaction twice (nested transaction)
        data_access.begin_transaction()
        data_access.begin_transaction()
        
        # Assert
        assert data_access._transaction_depth == 2
        
        # Act - Commit first level
        data_access.commit_transaction()
        
        # Assert - Still in transaction
        assert data_access._transaction_depth == 1
        
        # Act - Rollback (should reset to 0)
        data_access.rollback_transaction()
        
        # Assert
        assert data_access._transaction_depth == 0
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_execute_batch_success(self, mock_qcm_class, mock_dcm_class):
        """Test execute_batch with successful statements."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Create a partial mock to replace execute_query
        data_access.execute_query = Mock()
        data_access.execute_query.side_effect = [
            {"success": True, "rowcount": 1, "data": None, "error": None},
            {"success": True, "rowcount": 2, "data": None, "error": None}
        ]
        
        # Create a batch of statements
        statements = [
            {"sql": "INSERT INTO test (id, name) VALUES (:id, :name)", 
             "params": {"id": 1, "name": "Test"}, 
             "name": "insert_1"},
            {"sql": "UPDATE test SET updated = TRUE WHERE id = :id", 
             "params": {"id": 1}, 
             "name": "update_1"}
        ]
        
        # Act
        results = data_access.execute_batch(statements, transaction=True)
        
        # Assert
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[0]["statement_name"] == "insert_1"
        assert results[1]["success"] is True
        assert results[1]["statement_name"] == "update_1"
        assert data_access._transaction_depth == 0  # Transaction should be committed
    
    @patch('services.data.enhanced_data_access.DatabaseConnectionManager')
    @patch('services.data.enhanced_data_access.QueryCacheManager')
    def test_execute_batch_failure(self, mock_qcm_class, mock_dcm_class):
        """Test execute_batch with a failing statement."""
        # Arrange
        mock_dcm_class.return_value = self.mock_db_manager
        mock_qcm_class.return_value = self.mock_cache_manager
        
        # Create instance
        data_access = EnhancedDataAccess(self.test_config)
        
        # Create a partial mock to replace execute_query
        data_access.execute_query = Mock()
        data_access.execute_query.side_effect = [
            {"success": True, "rowcount": 1, "data": None, "error": None},
            {"success": False, "rowcount": 0, "data": None, "error": "Constraint violation"}
        ]
        
        # Also mock begin, commit, rollback
        data_access.begin_transaction = Mock()
        data_access.commit_transaction = Mock()
        data_access.rollback_transaction = Mock()
        
        # Create a batch of statements
        statements = [
            {"sql": "INSERT INTO test (id, name) VALUES (:id, :name)", 
             "params": {"id": 1, "name": "Test"}},
            {"sql": "INSERT INTO test (id, name) VALUES (:id, :name)", 
             "params": {"id": 1, "name": "Duplicate"}}  # Will fail due to duplicate
        ]
        
        # Act
        results = data_access.execute_batch(statements, transaction=True)
        
        # Assert
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        data_access.begin_transaction.assert_called_once()
        data_access.rollback_transaction.assert_called_once()
        data_access.commit_transaction.assert_not_called()


@patch('services.data.enhanced_data_access.EnhancedDataAccess')
def test_get_data_access_singleton(mock_eda_class):
    """Test get_data_access singleton behavior."""
    # Arrange
    mock_instance = MagicMock()
    mock_eda_class.return_value = mock_instance
    test_config = {"test": "config"}
    
    # Act
    instance1 = get_data_access(test_config)
    instance2 = get_data_access()  # No config needed second time
    
    # Assert
    assert instance1 == instance2
    mock_eda_class.assert_called_once_with(test_config)


if __name__ == "__main__":
    unittest.main() 