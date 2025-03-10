"""
Tests for the enhanced error handling system integration with services.

This file tests:
- Integration of the error handler with the query processor
- Correct error type mapping and recovery suggestions
- Error metrics collection across services
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest
import time
from datetime import datetime

from services.utils.error_handler import ErrorHandler, ErrorTypes, error_handler
from services.query_processor import QueryProcessor

class TestQueryProcessorErrorHandling(unittest.TestCase):
    """Test cases for the integration of error handling in QueryProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test configuration
        self.config = {
            "database": {
                "connection_string": "sqlite:///:memory:",
                "pool_size": 2
            },
            "context_manager": {
                "expiry_minutes": 30
            }
        }
        
        # Create a fresh error handler for testing
        self.original_error_handler = error_handler
        
        # Create mock services
        self.mock_data_access = MagicMock()
        self.mock_response_service = MagicMock()
        self.mock_context_manager = MagicMock()
        
        # Mock context
        self.mock_context = MagicMock()
        self.mock_context.to_dict.return_value = {"session_id": "test_session"}
        self.mock_context.get_reference_summary.return_value = {
            "entity_type": "test_entity",
            "time_period": "last week"
        }
        self.mock_context_manager.get_context.return_value = self.mock_context
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Restore the original error handler
        globals()['error_handler'] = self.original_error_handler
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.error_handler')
    def test_process_query_with_sql_error(self, mock_error_handler, mock_cm_class, 
                                         mock_rs_class, mock_get_data_access):
        """Test handling of SQL execution errors."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Set up mock data access error
        self.mock_data_access.execute_query.return_value = {
            "error": True,
            "error_type": "database_query",
            "message": "SQL syntax error"
        }
        
        # Set up mock response service
        self.mock_response_service.format_response.return_value = {
            "type": "error",
            "text": "There was an error executing your query.",
            "error": "sql_execution_error"
        }
        
        # Create query processor
        processor = QueryProcessor(self.config)
        processor.data_access = self.mock_data_access
        processor.response_service = self.mock_response_service
        processor.context_manager = self.mock_context_manager
        
        # Mock SQL generation
        processor._generate_sql_from_query = MagicMock(return_value=("SELECT * FROM test", {}))
        
        # Act
        classification_result = {
            "query_type": "data_query",
            "entity_type": "test_entity"
        }
        
        response = processor.process_query(
            "How many orders were there last week?",
            "test_session",
            classification_result
        )
        
        # Assert
        self.assertEqual(response["type"], "error")
        self.assertEqual(response["error"], "sql_execution_error")
        self.mock_data_access.execute_query.assert_called_once()
        mock_error_handler.handle_error.assert_not_called()  # shouldn't be called for expected errors
        
        # Check error metrics were updated
        self.assertEqual(processor.metrics["failed_queries"], 1)
        self.assertEqual(processor.metrics["error_counts"]["sql_execution_error"], 1)
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.error_handler')
    def test_process_query_with_unhandled_exception(self, mock_error_handler, mock_cm_class, 
                                                  mock_rs_class, mock_get_data_access):
        """Test handling of unhandled exceptions."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Set up mock data access to raise exception
        test_exception = Exception("Unexpected error")
        self.mock_data_access.execute_query.side_effect = test_exception
        
        # Set up mock error handler to return with SQL error type
        mock_error_handler.handle_error.return_value = {
            "error": ErrorTypes.SQL_EXECUTION_ERROR,
            "message": "Unexpected error",
            "recovery_suggestion": "Please try again later"
        }
        
        # Set up mock response service
        self.mock_response_service.format_response.return_value = {
            "type": "error",
            "text": "An error occurred executing your query.",
            "error": "sql_execution_error"
        }
        
        # Create query processor with decorated methods
        processor = QueryProcessor(self.config)
        processor.data_access = self.mock_data_access
        processor.response_service = self.mock_response_service
        processor.context_manager = self.mock_context_manager
        
        # Mock SQL generation
        processor._generate_sql_from_query = MagicMock(return_value=("SELECT * FROM test", {}))
        
        # Act
        classification_result = {
            "query_type": "data_query",
            "entity_type": "test_entity"
        }
        
        response = processor.process_query(
            "How many orders were there last week?",
            "test_session",
            classification_result
        )
        
        # Assert
        self.assertEqual(response["type"], "error")
        self.assertEqual(response["error"], "sql_execution_error")
        mock_error_handler.handle_error.assert_called_once()
        
        # Check that the error handler was called with the right arguments
        # The handle_error method is called with (error, error_type, context, recovery_suggestion)
        args, kwargs = mock_error_handler.handle_error.call_args
        if args:  # If called with positional arguments
            self.assertTrue(isinstance(args[0], Exception), "First arg should be an exception")
            if len(args) > 1:
                self.assertEqual(args[1], ErrorTypes.SQL_EXECUTION_ERROR)
        elif kwargs:  # If called with keyword arguments
            self.assertTrue(isinstance(kwargs.get('error'), Exception), "error kwarg should be an exception")
            self.assertEqual(kwargs.get('error_type'), ErrorTypes.SQL_EXECUTION_ERROR)
            self.assertIsNotNone(kwargs.get('context'), "context should be provided")
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.error_handler')
    def test_process_query_with_missing_parameters(self, mock_error_handler, mock_cm_class, 
                                                 mock_rs_class, mock_get_data_access):
        """Test handling of missing parameters for action requests."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Set up mock response service
        self.mock_response_service.format_response.return_value = {
            "type": "clarification",
            "text": "Could you specify which item you want to update?"
        }
        
        # Create query processor
        processor = QueryProcessor(self.config)
        processor.data_access = self.mock_data_access
        processor.response_service = self.mock_response_service
        processor.context_manager = self.mock_context_manager
        
        # Act
        classification_result = {
            "query_type": "action_request",
            "action": {
                "type": "update_price",
                "parameters": {"price": 10.99},
                "required_params": ["item_id", "price"]
            }
        }
        
        response = processor.process_query(
            "Update the price to $10.99",
            "test_session",
            classification_result
        )
        
        # Assert
        self.assertEqual(response["type"], "clarification")
        self.assertIn("specify", response["text"].lower())
        
        # Check metrics
        self.assertEqual(processor.metrics["total_queries"], 1)
        self.assertEqual(processor.metrics["successful_queries"], 1)
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    @patch('services.query_processor.error_handler')
    def test_health_check_includes_error_metrics(self, mock_error_handler, mock_cm_class, 
                                               mock_rs_class, mock_get_data_access):
        """Test that health check includes error handler health metrics."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Set up mock health checks
        self.mock_data_access.health_check.return_value = {"status": "healthy"}
        mock_error_handler.health_check.return_value = {
            "status": "healthy",
            "error_rate_1min": 0.0,
            "total_errors": 0
        }
        
        # Create query processor
        processor = QueryProcessor(self.config)
        processor.data_access = self.mock_data_access
        processor.response_service = self.mock_response_service
        processor.context_manager = self.mock_context_manager
        
        # Act
        health_status = processor.health_check()
        
        # Assert
        self.assertEqual(health_status["status"], "healthy")
        self.assertIn("error_handler", health_status["components"])
        self.assertEqual(
            health_status["components"]["error_handler"],
            mock_error_handler.health_check.return_value
        )

if __name__ == '__main__':
    unittest.main() 