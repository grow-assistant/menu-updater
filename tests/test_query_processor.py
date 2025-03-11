"""
Tests for the Query Processor.

These tests validate the integration between data access layer and response service.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
from datetime import datetime

from services.query_processor import QueryProcessor
from services.context_manager import ConversationContext


class TestQueryProcessor(unittest.TestCase):
    """Test cases for the QueryProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock configuration
        self.config = {
            "database": {
                "connection_string": "sqlite:///:memory:",
                "pool_size": 2
            },
            "context_manager": {
                "expiry_minutes": 30
            }
        }
        
        # Create mocks for dependencies
        self.mock_data_access = MagicMock()
        self.mock_response_service = MagicMock()
        self.mock_context_manager = MagicMock()
        
        # Create test data
        self.test_data = [
            {"id": 1, "name": "Test Item 1", "value": 100},
            {"id": 2, "name": "Test Item 2", "value": 200}
        ]
        
        # Test query information
        self.query_text = "How many orders were there last week?"
        self.session_id = "test_session"
        self.classification_result = {
            "query_type": "data_query",
            "confidence": 0.95,
            "parameters": {
                "entity_type": "orders",
                "time_period": "last week"
            }
        }
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_initialization(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test that the processor initializes properly."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Act
        processor = QueryProcessor(self.config)
        
        # Assert
        mock_get_data_access.assert_called_once_with(self.config)
        mock_rs_class.assert_called_once()
        mock_cm_class.assert_called_once()
        self.assertEqual(processor.data_access, self.mock_data_access)
        self.assertEqual(processor.response_service, self.mock_response_service)
        self.assertEqual(processor.context_manager, self.mock_context_manager)
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_process_data_query_success(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing a data query with successful execution."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup mock context
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.get_reference_summary.return_value = {
            "entity_type": "orders",
            "time_period": "last week",
            "time_references": {
                "start_date": "2023-08-01",
                "end_date": "2023-08-07"
            }
        }
        # Add attributes needed by the updated implementation
        mock_context.active_entities = {"entity_type": "orders"}
        mock_context.filters = {}
        mock_context.time_range = {
            "start_date": "2023-08-01",
            "end_date": "2023-08-07"
        }
        self.mock_context_manager.get_context.return_value = mock_context
        
        # Setup mock data access
        mock_df = pd.DataFrame(self.test_data)
        self.mock_data_access.query_to_dataframe.return_value = (
            mock_df, {"success": True, "rowcount": 2}
        )
        
        # Setup mock response service
        expected_response = {
            "type": "data",
            "text": "Found 2 orders for last week.",
            "data": self.test_data,
            "metadata": {
                "query_id": "test-1234",
                "processing_time": 0.12
            }
        }
        self.mock_response_service.format_response.return_value = expected_response
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        response = processor.process_query(
            self.query_text, 
            self.session_id, 
            self.classification_result
        )
        
        # Assert
        self.mock_context_manager.get_context.assert_called_with(self.session_id, None)
        self.mock_data_access.query_to_dataframe.assert_called_once()
        mock_context.update_with_query.assert_called_once()
        self.mock_response_service.format_response.assert_called_once()
        
        # Metrics should be updated
        self.assertEqual(processor.metrics['total_queries'], 1)
        self.assertEqual(processor.metrics['successful_queries'], 1)
        self.assertEqual(processor.metrics['failed_queries'], 0)
        
        # Response should have metadata added
        self.assertIn('metadata', response)
        self.assertIn('query_id', response['metadata'])
        self.assertIn('processing_time', response['metadata'])
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_process_data_query_database_error(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing a data query with a database error."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup mock context
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.get_reference_summary.return_value = {
            "entity_type": "orders",
            "time_period": "last week",
            "time_references": {
                "start_date": "2023-08-01",
                "end_date": "2023-08-07"
            }
        }
        # Add attributes needed by the updated implementation
        mock_context.active_entities = {"entity_type": "orders"}
        mock_context.filters = {}
        mock_context.time_range = {
            "start_date": "2023-08-01",
            "end_date": "2023-08-07"
        }
        self.mock_context_manager.get_context.return_value = mock_context
        
        # Setup mock data access to return an error
        self.mock_data_access.query_to_dataframe.return_value = (
            pd.DataFrame(), {"success": False, "error": "Database connection error"}
        )
        
        # Setup mock response service for error
        error_response = {
            "type": "error",
            "text": "Sorry, I encountered an error: Unable to connect to the database. Please try again later.",
            "error": "query_error"
        }
        self.mock_response_service.format_response.return_value = error_response
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        response = processor.process_query(
            self.query_text,
            self.session_id,
            self.classification_result
        )
        
        # Assert
        self.mock_data_access.query_to_dataframe.assert_called_once()
        
        # Response service should be called with error_response type
        self.mock_response_service.format_response.assert_called_once()
        call_args = self.mock_response_service.format_response.call_args[1]
        self.assertEqual(call_args['response_type'], 'error')
        
        # Metrics should be updated
        self.assertEqual(processor.metrics['total_queries'], 1)
        self.assertEqual(processor.metrics['successful_queries'], 0)  # Changed from 1 to 0 because we don't count errors as successful
        self.assertEqual(processor.metrics['failed_queries'], 1)  # Changed from 0 to 1 because errors increment failed_queries
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_process_action_request(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing an action request."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup action classification
        action_classification = {
            "query_type": "action_request",
            "confidence": 0.92,
            "parameters": {
                "action_type": "update",
                "entity_type": "menu_item",
                "entity_name": "Hamburger",
                "price": 9.99
            }
        }
        
        # Setup mock context
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.get_reference_summary.return_value = {
            "entity_type": "menu_item"
        }
        self.mock_context_manager.get_context.return_value = mock_context
        
        # Setup mock response service
        action_response = {
            "type": "action",
            "text": "I've updated the menu item Hamburger.",
            "action": "update"
        }
        self.mock_response_service.format_response.return_value = action_response
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        response = processor.process_query(
            "Update the price of Hamburger to $9.99", 
            self.session_id, 
            action_classification
        )
        
        # Assert
        self.mock_context_manager.get_context.assert_called_with(self.session_id, None)
        
        # Response service should be called with action type
        self.mock_response_service.format_response.assert_called_once()
        call_args = self.mock_response_service.format_response.call_args[1]
        self.assertEqual(call_args['response_type'], 'action')
        
        # Action data should contain the right information
        action_data = call_args['data']
        self.assertEqual(action_data['action'], 'update')
        self.assertEqual(action_data['entity_type'], 'menu_item')
        self.assertEqual(action_data['entity_name'], 'Hamburger')
        self.assertTrue(action_data['success'])
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_process_action_request_missing_params(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing an action request with missing parameters."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup action classification with missing entity name
        action_classification = {
            "query_type": "action_request",
            "confidence": 0.92,
            "parameters": {
                "action_type": "update",
                "entity_type": "menu_item",
                # Missing entity_name
                "price": 9.99
            }
        }
        
        # Setup mock context
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.get_reference_summary.return_value = {
            "entity_type": "menu_item"
        }
        self.mock_context_manager.get_context.return_value = mock_context
        
        # Setup mock response service
        clarification_response = {
            "type": "clarification",
            "text": "Which menu item do you want to modify?",
            "requires_response": True
        }
        self.mock_response_service.format_response.return_value = clarification_response
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        response = processor.process_query(
            "Update the price to $9.99", 
            self.session_id, 
            action_classification
        )
        
        # Assert
        # Response service should be called with clarification type
        self.mock_response_service.format_response.assert_called_once()
        call_args = self.mock_response_service.format_response.call_args[1]
        self.assertEqual(call_args['response_type'], 'clarification')
        
        # Clarification data should be about the entity_name
        clarification_data = call_args['data']
        self.assertEqual(clarification_data['clarification_type'], 'entity_name')
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_process_query_with_error(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test processing a query that raises an exception."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup mock context to raise an exception
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.update_with_query.side_effect = ValueError("Test exception")
        self.mock_context_manager.get_context.return_value = mock_context
        
        # Setup mock response service for error
        error_response = {
            "type": "error",
            "text": "Sorry, an internal error occurred. Please try again.",
            "error": "internal_error"
        }
        self.mock_response_service.format_response.return_value = error_response
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        response = processor.process_query(
            self.query_text, 
            self.session_id, 
            self.classification_result
        )
        
        # Assert
        # Error handling should create an error response
        self.mock_response_service.format_response.assert_called_once()
        call_args = self.mock_response_service.format_response.call_args[1]
        self.assertEqual(call_args['response_type'], 'error')
        
        # Metrics should show a failed query
        self.assertEqual(processor.metrics['total_queries'], 1)
        self.assertEqual(processor.metrics['successful_queries'], 0)
        self.assertEqual(processor.metrics['failed_queries'], 1)
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_generate_sql_from_query(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test SQL generation from query and context."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Setup mock context
        mock_context = MagicMock(spec=ConversationContext)
        mock_context.get_reference_summary.return_value = {
            "entity_type": "orders",
            "time_references": {
                "start_date": "2023-08-01",
                "end_date": "2023-08-07"
            }
        }
        # Add attributes needed by the updated implementation
        mock_context.active_entities = {"entity_type": "orders"}
        mock_context.filters = {}
        mock_context.time_range = {
            "start_date": "2023-08-01",
            "end_date": "2023-08-07"
        }
        
        # Act
        sql, params = processor._generate_sql_from_query(
            self.query_text,
            self.classification_result,
            mock_context
        )
        
        # Assert
        self.assertIn("SELECT * FROM orders", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("updated_at >= :start_date", sql)
        self.assertIn("updated_at <= :end_date", sql)
        self.assertEqual(params["start_date"], "2023-08-01")
        self.assertEqual(params["end_date"], "2023-08-07")
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_health_check(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test the health check method."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup health check mocks
        self.mock_data_access.health_check.return_value = {
            "service": "data_access",
            "status": "ok"
        }
        self.mock_response_service.health_check.return_value = {
            "service": "response_service",
            "status": "ok"
        }
        
        # Create processor
        processor = QueryProcessor(self.config)
        
        # Act
        health_info = processor.health_check()
        
        # Assert
        self.mock_data_access.health_check.assert_called_once()
        self.mock_response_service.health_check.assert_called_once()
        
        self.assertEqual(health_info["service"], "query_processor")
        self.assertEqual(health_info["status"], "ok")
        self.assertIn("components", health_info)
        self.assertIn("data_access", health_info["components"])
        self.assertIn("response_service", health_info["components"])
        self.assertIn("metrics", health_info)
    
    @patch('services.query_processor.get_data_access')
    @patch('services.query_processor.ResponseService')
    @patch('services.query_processor.ContextManager')
    def test_get_metrics(self, mock_cm_class, mock_rs_class, mock_get_data_access):
        """Test getting performance metrics."""
        # Arrange
        mock_get_data_access.return_value = self.mock_data_access
        mock_rs_class.return_value = self.mock_response_service
        mock_cm_class.return_value = self.mock_context_manager
        
        # Setup metrics mock
        self.mock_data_access.get_performance_metrics.return_value = {
            "total_queries": 100,
            "cache_hit_rate": 75.5
        }
        
        # Create processor with some metrics
        processor = QueryProcessor(self.config)
        processor.metrics = {
            'total_queries': 50,
            'successful_queries': 45,
            'failed_queries': 5,
            'avg_processing_time': 0.1,
            'total_processing_time': 5.0
        }
        
        # Act
        metrics = processor.get_metrics()
        
        # Assert
        self.mock_data_access.get_performance_metrics.assert_called_once()
        
        self.assertEqual(metrics["total_queries"], 50)
        self.assertEqual(metrics["successful_queries"], 45)
        self.assertEqual(metrics["failed_queries"], 5)
        self.assertIn("data_access_metrics", metrics)
        self.assertEqual(metrics["data_access_metrics"]["total_queries"], 100)
        self.assertEqual(metrics["data_access_metrics"]["cache_hit_rate"], 75.5)


if __name__ == "__main__":
    unittest.main() 