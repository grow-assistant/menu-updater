"""
Unit tests for the enhanced SQLExecutor.
"""
import pytest
import pandas as pd
import time
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from services.execution.sql_executor import SQLExecutor

@pytest.fixture
def mock_config():
    """Fixture for mock configuration."""
    return {
        "database": {
            "connection_string": "sqlite:///:memory:",
            "pool_size": 3,
            "max_overflow": 5,
            "pool_timeout": 10,
            "pool_recycle": 900,
            "max_history_size": 50,
            "slow_query_threshold": 0.5,
            "default_timeout": 15,
            "max_retries": 2,
            "retry_delay": 0.1
        }
    }

@pytest.fixture
def mock_engine():
    """Fixture for mock SQLAlchemy engine."""
    engine = MagicMock()
    
    # Mock connection
    connection = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    
    # Mock pool
    engine.pool.size.return_value = 3
    engine.pool.checkedin.return_value = 2
    engine.pool.checkedout.return_value = 1
    engine.pool.overflow.return_value = 0
    engine.pool.timeout = 10
    engine.pool.recycle = 900
    
    return engine

@pytest.fixture
def sql_executor(mock_config, mock_engine):
    """Fixture for SQLExecutor with mocked dependencies."""
    with patch("services.execution.sql_executor.create_engine") as mock_create_engine:
        mock_create_engine.return_value = mock_engine
        executor = SQLExecutor(mock_config)
        return executor

class TestEnhancedSQLExecutor:
    """Tests for the enhanced SQLExecutor."""
    
    def test_initialization(self, sql_executor, mock_config):
        """Test service initialization."""
        assert sql_executor.max_history_size == mock_config["database"]["max_history_size"]
        assert sql_executor.slow_query_threshold == mock_config["database"]["slow_query_threshold"]
        assert sql_executor.default_timeout == mock_config["database"]["default_timeout"]
        assert sql_executor.max_retries == mock_config["database"]["max_retries"]
        assert sql_executor.retry_delay == mock_config["database"]["retry_delay"]
        assert isinstance(sql_executor.query_history, list)
    
    def test_execute_select_query_success(self, sql_executor):
        """Test successful execution of a SELECT query."""
        # Mock data
        test_df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        
        # Mock _execute_with_timeout to return the test DataFrame
        with patch.object(sql_executor, "_execute_with_timeout") as mock_execute:
            mock_execute.return_value = test_df
            
            # Execute query
            result = sql_executor.execute("SELECT * FROM test")
            
            # Check result structure
            assert result["success"] is True
            assert result["error"] is None
            assert result["error_type"] is None
            assert "execution_time" in result
            assert "timestamp" in result
            assert result["row_count"] == 3
            
            # Check results data
            assert len(result["results"]) == 3
            assert result["results"][0]["id"] == 1
            assert result["results"][0]["name"] == "A"
    
    def test_execute_non_select_query_success(self, sql_executor):
        """Test successful execution of a non-SELECT query."""
        # Mock _execute_with_timeout to return affected row count
        with patch.object(sql_executor, "_execute_with_timeout") as mock_execute:
            mock_execute.return_value = 5  # 5 rows affected
            
            # Execute query
            result = sql_executor.execute("UPDATE test SET name = 'X' WHERE id < 6")
            
            # Check result structure
            assert result["success"] is True
            assert result["error"] is None
            assert result["error_type"] is None
            assert result["row_count"] == 5
            
            # Check results data
            assert result["results"]["affected_rows"] == 5
    
    def test_execute_with_error(self, sql_executor):
        """Test query execution with error."""
        # Mock _execute_with_timeout to raise an exception
        with patch.object(sql_executor, "_execute_with_timeout") as mock_execute:
            mock_execute.side_effect = ValueError("Invalid SQL syntax")
            
            # Execute query
            result = sql_executor.execute("INVALID SQL")
            
            # Check result structure
            assert result["success"] is False
            assert result["error"] == "Invalid SQL syntax"
            assert result["error_type"] == "ValueError"
            assert result["results"] is None
    
    def test_execute_with_retry(self, sql_executor):
        """Test query execution with retry after failure."""
        # Mock _execute_with_timeout to fail once, then succeed
        test_df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        side_effects = [
            ValueError("Connection error"),
            test_df
        ]
        
        with patch.object(sql_executor, "_execute_with_timeout", side_effect=side_effects):
            with patch("time.sleep") as mock_sleep:
                # Execute query
                result = sql_executor.execute("SELECT * FROM test")
                
                # Check that sleep was called for retry delay
                mock_sleep.assert_called_once_with(sql_executor.retry_delay)
                
                # Check result structure
                assert result["success"] is True
                assert result["error"] is None
                assert result["row_count"] == 2
                assert len(result["results"]) == 2
    
    def test_execute_with_timeout(self, sql_executor, mock_engine):
        """Test _execute_with_timeout method."""
        # Create a test DataFrame that would be returned by pd.read_sql
        test_df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        
        # Mock pandas.read_sql to return the test DataFrame
        with patch("pandas.read_sql", return_value=test_df):
            # Test SELECT query
            result = sql_executor._execute_with_timeout("SELECT * FROM test", None, 10)
            assert isinstance(result, pd.DataFrame)
            assert result.equals(test_df)
            
            # Test non-SELECT query
            connection = mock_engine.connect.return_value.__enter__.return_value
            execute_result = MagicMock()
            execute_result.rowcount = 3
            connection.execute.return_value = execute_result
            
            result = sql_executor._execute_with_timeout("UPDATE test SET name = 'X'", None, 10)
            assert result == 3
    
    def test_execute_with_timeout_exception(self, sql_executor):
        """Test _execute_with_timeout with an exception in the worker thread."""
        # Mock queue.Queue.get to simulate getting an exception from the worker thread
        with patch("queue.Queue.get") as mock_get:
            mock_get.return_value = ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                sql_executor._execute_with_timeout("SELECT * FROM test", None, 10)
    
    def test_execute_with_timeout_timeout(self, sql_executor):
        """Test _execute_with_timeout with a timeout."""
        # Mock queue.Queue.get to raise Empty exception (timeout)
        with patch("queue.Queue.get") as mock_get:
            mock_get.side_effect = sql_executor._execute_with_timeout.__globals__["queue"].Empty
            
            with pytest.raises(TimeoutError):
                sql_executor._execute_with_timeout("SELECT * FROM test", None, 10)
    
    def test_record_query_performance(self, sql_executor):
        """Test recording query performance metrics."""
        # Record a fast query
        sql_executor._record_query_performance("SELECT * FROM test", 0.1, True, None, 10)
        
        # Record a slow query
        with patch("logging.Logger.warning") as mock_warning:
            sql_executor._record_query_performance("SELECT * FROM test WHERE id > 1000", 1.0, True, None, 5)
            mock_warning.assert_called_once()
        
        # Check that both queries were recorded
        assert len(sql_executor.query_history) == 2
        assert sql_executor.query_history[0]["execution_time"] == 0.1
        assert sql_executor.query_history[1]["execution_time"] == 1.0
        
        # Check history size limit
        sql_executor.max_history_size = 1
        sql_executor._record_query_performance("SELECT 1", 0.05, True, None, 1)
        assert len(sql_executor.query_history) == 1
        assert sql_executor.query_history[0]["query"] == "SELECT 1"
    
    def test_get_performance_metrics(self, sql_executor):
        """Test getting performance metrics."""
        # Test with empty history
        metrics = sql_executor.get_performance_metrics()
        assert metrics["total_queries"] == 0
        assert metrics["avg_execution_time"] == 0
        assert metrics["success_rate"] == 0
        assert metrics["slow_queries"] == 0
        
        # Add some test data
        sql_executor.query_history = [
            {"execution_time": 0.1, "success": True, "error_type": None, "row_count": 10},
            {"execution_time": 0.2, "success": True, "error_type": None, "row_count": 5},
            {"execution_time": 0.8, "success": False, "error_type": "ValueError", "row_count": 0},
            {"execution_time": 0.3, "success": True, "error_type": None, "row_count": 3}
        ]
        
        # Test with data
        metrics = sql_executor.get_performance_metrics()
        assert metrics["total_queries"] == 4
        assert metrics["avg_execution_time"] == 0.35  # (0.1 + 0.2 + 0.8 + 0.3) / 4
        assert metrics["success_rate"] == 0.75  # 3/4
        assert metrics["slow_queries"] == 1  # Only one query > 0.5s
        assert metrics["slow_query_percentage"] == 25.0  # 1/4 * 100
    
    def test_get_connection_pool_status(self, sql_executor, mock_engine):
        """Test getting connection pool status."""
        status = sql_executor.get_connection_pool_status()
        
        assert status["pool_size"] == 3
        assert status["checkedin"] == 2
        assert status["checkedout"] == 1
        assert status["overflow"] == 0
        assert status["timeout"] == 10
        assert status["recycle"] == 900
    
    def test_health_check_success(self, sql_executor, mock_engine):
        """Test health check success."""
        result = sql_executor.health_check()
        assert result is True
        
        connection = mock_engine.connect.return_value.__enter__.return_value
        connection.execute.assert_called_once()
    
    def test_health_check_failure(self, sql_executor, mock_engine):
        """Test health check failure."""
        connection = mock_engine.connect.return_value.__enter__.return_value
        connection.execute.side_effect = Exception("Database error")
        
        result = sql_executor.health_check()
        assert result is False 