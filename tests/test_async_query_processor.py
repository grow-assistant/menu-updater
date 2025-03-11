"""
Tests for the asynchronous functionality of the Query Processor.

These tests verify that the Query Processor correctly supports
asynchronous operations while maintaining compatibility with synchronous code.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
import pandas as pd
import asyncio
from datetime import datetime

from services.query_processor import QueryProcessor
from services.context_manager import ConversationContext
from services.utils.error_handler import ErrorTypes


class TestAsyncQueryProcessor(unittest.TestCase):
    """Tests for the asynchronous functionality in QueryProcessor."""
    
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
            },
            "cache": {
                "enabled": True,
                "default_ttl": 300,
                "max_size": 1000,
                "non_cacheable_tables": ["audit_log", "user_sessions"],
                "storage_path": None
            },
            "async_mode": True,
            "response": {
                "templates_dir": "./resources/templates",
                "default_language": "en",
                "enable_voice": False
            }
        }
        
        # Mock services
        self.mock_data_access = MagicMock()
        self.mock_response_service = MagicMock()
        self.mock_context_manager = MagicMock()
        
        # Create a mock context
        self.mock_context = MagicMock(spec=ConversationContext)
        self.mock_context.active_entities = {}
        self.mock_context.filters = {}
        self.mock_context.time_range = {}
        self.mock_context.to_dict.return_value = {}
        
        # Configure mock context manager
        self.mock_context_manager.get_context.return_value = self.mock_context
        self.mock_context_manager.update_context.return_value = self.mock_context
        
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_init(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test initialization with async mode enabled."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Verify async_mode is enabled
        self.assertTrue(query_processor.async_mode)
        
        # Verify services were initialized
        mock_get_data_access.assert_called_once_with(self.test_config)
        
        # We don't need to verify exact parameters for these mocks, just that they were called
        self.assertEqual(mock_rs_class.call_count, 1)
        self.assertEqual(mock_cm_class.call_count, 1)
        
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_get_event_loop(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test that _get_event_loop returns an event loop."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Test getting the event loop
        loop = query_processor._get_event_loop()
        
        # Verify the loop is an event loop
        self.assertIsNotNone(loop)
        self.assertTrue(isinstance(loop, asyncio.AbstractEventLoop))
        
        # Test getting the event loop again (should return an event loop)
        loop2 = query_processor._get_event_loop()
        self.assertTrue(isinstance(loop2, asyncio.AbstractEventLoop))
        
    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_process_query_async_data_query(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing a data query asynchronously."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Configure AsyncMock for query_to_dataframe_async
        self.mock_data_access.query_to_dataframe_async = AsyncMock()
        
        # Setup return value for query_to_dataframe_async
        test_data = pd.DataFrame([
            {"id": 1, "name": "Item 1", "price": 10.99},
            {"id": 2, "name": "Item 2", "price": 15.99}
        ])
        query_metadata = {
            "success": True,
            "cached": False,
            "execution_time": 0.1,
            "total_time": 0.2,
            "rowcount": 2,
            "error": None,
            "query_id": "test-query-id"
        }
        self.mock_data_access.query_to_dataframe_async.return_value = (test_data, query_metadata)
        
        # Configure response service
        self.mock_response_service.format_data_response.return_value = {
            "type": "data",
            "message": "Here are the items you requested",
            "data": test_data.to_dict(orient="records"),
            "success": True
        }
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Patch the async SQL generation method
        with patch.object(query_processor, '_generate_sql_from_query_async', AsyncMock()) as mock_gen_sql:
            # Configure return value for _generate_sql_from_query_async
            mock_gen_sql.return_value = ("SELECT * FROM items", {})
            
            # Process a data query
            query_text = "Show me all items"
            session_id = "test-session-123"
            classification_result = {
                "intent_type": "data_query",
                "query_type": "menu_items",
                "entities": {"entity_type": "items"},
                "confidence": 0.95
            }
            
            # Call the async method
            response = await query_processor.process_query_async(
                query_text, session_id, classification_result
            )
            
            # Verify the response
            self.assertIsNotNone(response)
            self.assertTrue(response.get("success", False))
            self.assertEqual(response.get("type"), "data")
            
            # Verify that the async SQL generation method was called
            mock_gen_sql.assert_awaited_once()
            
            # Verify that the async data access method was called
            self.mock_data_access.query_to_dataframe_async.assert_awaited_once()
            
    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_process_query_async_error_handling(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test error handling in async query processing."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Configure AsyncMock for query_to_dataframe_async to raise an exception
        self.mock_data_access.query_to_dataframe_async = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        # Configure error response
        self.mock_response_service.format_error_response.return_value = {
            "type": "error",
            "message": "An error occurred: Database connection failed",
            "error_type": ErrorTypes.DATABASE_ERROR,
            "success": False
        }
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Patch the async SQL generation method
        with patch.object(query_processor, '_generate_sql_from_query_async', AsyncMock()) as mock_gen_sql:
            # Configure return value for _generate_sql_from_query_async
            mock_gen_sql.return_value = ("SELECT * FROM items", {})
            
            # Process a data query
            query_text = "Show me all items"
            session_id = "test-session-123"
            classification_result = {
                "intent_type": "data_query",
                "query_type": "menu_items",
                "entities": {"entity_type": "items"},
                "confidence": 0.95
            }
            
            # Call the async method
            response = await query_processor.process_query_async(
                query_text, session_id, classification_result
            )
            
            # Verify the response indicates an error
            self.assertIsNotNone(response)
            self.assertEqual(response.get("type"), "error")
            
            # Verify that the async SQL generation method was called
            mock_gen_sql.assert_awaited_once()
            
            # Verify that the async data access method was called
            self.mock_data_access.query_to_dataframe_async.assert_awaited_once()
            
    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_generate_sql_from_query_async(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous SQL generation."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Replace _generate_sql_from_query with a mock
        with patch.object(query_processor, '_generate_sql_from_query') as mock_gen_sql:
            # Configure return value
            expected_sql = "SELECT * FROM menu_items WHERE category = :category"
            expected_params = {"category": "Appetizers"}
            mock_gen_sql.return_value = (expected_sql, expected_params)
            
            # Call the async method
            query_text = "Show me appetizers"
            classification_result = {
                "query_type": "menu_items",
                "entities": {"category": "Appetizers"},
                "filters": {}
            }
            
            sql, params = await query_processor._generate_sql_from_query_async(
                query_text, classification_result, self.mock_context
            )
            
            # Verify the result
            self.assertEqual(sql, expected_sql)
            self.assertEqual(params, expected_params)
            
            # Verify that the synchronous method was called
            mock_gen_sql.assert_called_once_with(
                query_text, classification_result, self.mock_context
            )
            
    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_process_data_query_async(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous data query processing."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Configure AsyncMock for query_to_dataframe_async
        self.mock_data_access.query_to_dataframe_async = AsyncMock()
        
        # Setup return value for query_to_dataframe_async
        test_data = pd.DataFrame([
            {"id": 1, "name": "Item 1", "price": 10.99},
            {"id": 2, "name": "Item 2", "price": 15.99}
        ])
        query_metadata = {
            "success": True,
            "cached": False,
            "execution_time": 0.1,
            "total_time": 0.2,
            "rowcount": 2,
            "error": None,
            "query_id": "test-query-id"
        }
        self.mock_data_access.query_to_dataframe_async.return_value = (test_data, query_metadata)
        
        # Configure response service
        self.mock_response_service.format_data_response.return_value = {
            "type": "data",
            "message": "Here are the items you requested",
            "data": test_data.to_dict(orient="records"),
            "success": True
        }
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Patch the async SQL generation method
        with patch.object(query_processor, '_generate_sql_from_query_async', AsyncMock()) as mock_gen_sql:
            # Configure return value for _generate_sql_from_query_async
            expected_sql = "SELECT * FROM menu_items"
            expected_params = {}
            mock_gen_sql.return_value = (expected_sql, expected_params)
            
            # Call the async method
            query_text = "Show me all menu items"
            classification_result = {
                "query_type": "menu_items",
                "entities": {},
                "filters": {}
            }
            query_info = {
                "query_id": "test-query-123",
                "session_id": "test-session-123",
                "timestamp": datetime.now().isoformat(),
                "intent_type": "data_query",
                "confidence": 0.95,
                "processing_time": 0.0,
            }
            
            response = await query_processor._process_data_query_async(
                query_text, classification_result, self.mock_context, query_info
            )
            
            # Verify the result
            self.assertEqual(response["type"], "data")
            self.assertTrue(response["success"])
            
            # Verify SQL generation was called
            mock_gen_sql.assert_awaited_once_with(
                query_text, classification_result, self.mock_context
            )
            
            # Verify async query execution was called
            self.mock_data_access.query_to_dataframe_async.assert_awaited_once_with(
                sql_query=expected_sql,
                params=expected_params,
                use_cache=True
            )
            
            # Verify response formatting was called
            self.mock_response_service.format_data_response.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_process_action_request_async(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous action request processing."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create a mock response service with format_response_async method
        self.mock_response_service.format_response_async = AsyncMock()
        self.mock_response_service.format_response_async.return_value = {
            "type": "action",
            "message": "Price updated successfully",
            "action_result": {"success": True, "affected_items": 1},
            "success": True
        }
        
        # Mock data access execute_action_async method
        self.mock_data_access.execute_action_async = AsyncMock()
        self.mock_data_access.execute_action_async.return_value = {
            "success": True,
            "affected_rows": 1,
            "execution_time": 0.05,
            "action_id": "test-action-123",
            "details": "Price updated for item Burger"
        }
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Call the async method
        query_text = "Update Burger price to $12.99"
        classification_result = {
            "action": {
                "type": "update_price",
                "parameters": {
                    "item_name": "Burger",
                    "new_price": 12.99
                },
                "required_params": ["item_name", "new_price"]
            }
        }
        query_info = {
            "query_id": "test-query-123",
            "session_id": "test-session-123",
            "timestamp": datetime.now().isoformat(),
            "intent_type": "action_request",
            "confidence": 0.95,
            "processing_time": 0.0,
        }
        
        response = await query_processor._process_action_request_async(
            query_text, classification_result, self.mock_context, query_info
        )
        
        # Verify the result
        self.assertEqual(response["type"], "action")
        self.assertTrue(response["success"])
        
        # Verify execute_action_async was called
        self.mock_data_access.execute_action_async.assert_awaited_once()
        
        # Verify response formatting was called
        self.mock_response_service.format_response_async.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_create_error_response_async(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous error response creation."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Mock response service async method
        self.mock_response_service.format_error_response_async = AsyncMock()
        expected_response = {
            "type": "error",
            "message": "Failed to retrieve data: Database connection error",
            "error_type": ErrorTypes.DATABASE_ERROR,
            "success": False
        }
        self.mock_response_service.format_error_response_async.return_value = expected_response
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Call the async method
        error_type = ErrorTypes.DATABASE_ERROR
        error_message = "Database connection error"
        query_info = {
            "query_id": "test-query-123",
            "session_id": "test-session-123",
            "timestamp": datetime.now().isoformat(),
            "intent_type": "data_query",
            "confidence": 0.95,
            "processing_time": 0.0,
        }
        
        response = await query_processor._create_error_response_async(
            error_type, error_message, query_info, self.mock_context
        )
        
        # Verify the result
        self.assertEqual(response, expected_response)
        
        # Verify format_error_response_async was called
        self.mock_response_service.format_error_response_async.assert_awaited_once_with(
            error_type, error_message, query_info
        )
        
        # Verify error metrics were updated
        self.assertIn(error_type, query_processor.metrics["errors_by_type"])
        self.assertEqual(query_processor.metrics["errors_by_type"][error_type], 1)
        self.assertEqual(query_processor.metrics["failed_queries"], 1)

    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    async def test_create_clarification_response_async(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous clarification response creation."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Mock response service async method
        self.mock_response_service.format_clarification_response_async = AsyncMock()
        expected_response = {
            "type": "clarification",
            "message": "Could you specify which time period you're interested in?",
            "clarification_type": "time_period",
            "success": True,
            "requires_response": True
        }
        self.mock_response_service.format_clarification_response_async.return_value = expected_response
        
        # Create QueryProcessor instance
        query_processor = QueryProcessor(self.test_config)
        
        # Call the async method
        clarification_type = "time_period"
        clarification_subject = "which time period you're interested in"
        query_info = {
            "query_id": "test-query-123",
            "session_id": "test-session-123",
            "timestamp": datetime.now().isoformat(),
            "intent_type": "data_query",
            "confidence": 0.95,
            "processing_time": 0.0,
        }
        
        response = await query_processor._create_clarification_response_async(
            clarification_type, clarification_subject, query_info, self.mock_context
        )
        
        # Verify the result
        self.assertEqual(response, expected_response)
        
        # Verify format_clarification_response_async was called
        self.mock_response_service.format_clarification_response_async.assert_awaited_once_with(
            clarification_type, clarification_subject, query_info
        )
        
        # Verify clarification metrics were updated
        self.assertIn(clarification_type, query_processor.metrics["clarifications_by_type"])
        self.assertEqual(query_processor.metrics["clarifications_by_type"][clarification_type], 1)
        self.assertEqual(query_processor.metrics["clarification_requests"], 1)

    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.FeedbackService')
    async def test_submit_feedback_async(self, mock_fb_class, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous feedback submission."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create a mock feedback service
        mock_feedback_service = MagicMock()
        mock_fb_class.return_value = mock_feedback_service
        
        # Configure mock feedback service
        mock_feedback_service.store_feedback_async = AsyncMock()
        mock_feedback_service.store_feedback_async.return_value = {
            "success": True,
            "feedback_id": "test-feedback-123",
            "message": "Feedback recorded successfully"
        }
        
        # Create QueryProcessor instance
        with patch.dict(self.test_config, {"feedback": {"storage": "memory", "max_entries": 1000}}):
            query_processor = QueryProcessor(self.test_config)
            
            # Replace instance's feedback service with our mock
            query_processor.feedback_service = mock_feedback_service
            
            # Call the async method
            session_id = "test-session-123"
            response_id = "test-response-456"
            feedback_data = {
                "rating": 4,
                "comment": "Very helpful response",
                "was_accurate": True
            }
            
            response = await query_processor.submit_feedback_async(
                session_id, response_id, feedback_data
            )
            
            # Verify the result
            self.assertTrue(response["success"])
            self.assertEqual(response["feedback_id"], "test-feedback-123")
            
            # Verify store_feedback_async was called
            mock_feedback_service.store_feedback_async.assert_awaited_once_with(
                session_id, response_id, feedback_data
            )

    @pytest.mark.asyncio
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.FeedbackService')
    async def test_get_feedback_stats_async(self, mock_fb_class, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test asynchronous retrieval of feedback statistics."""
        # Setup mocks
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create a mock feedback service
        mock_feedback_service = MagicMock()
        mock_fb_class.return_value = mock_feedback_service
        
        # Configure mock feedback service
        mock_feedback_service.get_feedback_stats_async = AsyncMock()
        expected_stats = {
            "total_feedback_count": 25,
            "average_rating": 4.2,
            "accuracy_rate": 0.85,
            "rating_distribution": {"5": 10, "4": 8, "3": 5, "2": 1, "1": 1},
            "recent_comments": ["Very helpful", "Could be more detailed"]
        }
        mock_feedback_service.get_feedback_stats_async.return_value = expected_stats
        
        # Create QueryProcessor instance
        with patch.dict(self.test_config, {"feedback": {"storage": "memory", "max_entries": 1000}}):
            query_processor = QueryProcessor(self.test_config)
            
            # Replace instance's feedback service with our mock
            query_processor.feedback_service = mock_feedback_service
            
            # Call the async method
            time_period = "last_week"
            stats = await query_processor.get_feedback_stats_async(time_period)
            
            # Verify the result
            self.assertEqual(stats, expected_stats)
            
            # Verify get_feedback_stats_async was called
            mock_feedback_service.get_feedback_stats_async.assert_awaited_once_with(time_period)


if __name__ == '__main__':
    unittest.main() 