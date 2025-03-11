"""
Tests for the Query Processor's feedback functionality.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil
import json
import asyncio
import pytest

from services.query_processor import QueryProcessor
from services.feedback import FeedbackType, IssueCategory, FeedbackModel


class TestQueryProcessorFeedback(unittest.TestCase):
    """Tests for the feedback functionality in the QueryProcessor class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for feedback storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create configuration
        self.config = {
            "feedback_storage_type": "file",
            "feedback_storage_dir": self.temp_dir
        }
        
        # Initialize with mocks to avoid actual service initialization
        with patch('services.query_processor.get_data_access') as mock_get_data_access, \
             patch('services.query_processor.ResponseService') as mock_response_service, \
             patch('services.query_processor.ContextManager') as mock_context_manager:
            
            self.mock_data_access = MagicMock()
            mock_get_data_access.return_value = self.mock_data_access
            
            self.query_processor = QueryProcessor(self.config)
        
        # Setup response history for testing
        self.query_processor.response_history = {
            "response-123": {
                "query_id": "query-abc",
                "query_text": "Show me menu items",
                "session_id": "session-xyz",
                "intent_type": "data_query",
                "query_type": "menu_items",
                "timestamp": "2023-01-01T12:00:00"
            }
        }
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch('services.query_processor.get_feedback_service')
    def test_submit_feedback(self, mock_get_feedback_service):
        """Test submitting feedback through the query processor."""
        # Setup mock feedback service
        mock_feedback_service = MagicMock()
        mock_feedback_service.submit_feedback.return_value = "feedback-456"
        mock_get_feedback_service.return_value = mock_feedback_service
        self.query_processor.feedback_service = mock_feedback_service
        
        # Test with known response ID
        feedback_data = {
            "feedback_type": FeedbackType.HELPFUL,
            "rating": 5,
            "comment": "Great response!"
        }
        
        result = self.query_processor.submit_feedback(
            session_id="session-xyz",
            response_id="response-123",
            feedback_data=feedback_data
        )
        
        # Verify feedback service was called with correct parameters
        mock_feedback_service.submit_feedback.assert_called_once()
        call_args = mock_feedback_service.submit_feedback.call_args[0][0]
        self.assertEqual(call_args.session_id, "session-xyz")
        self.assertEqual(call_args.query_text, "Show me menu items")
        self.assertEqual(call_args.response_id, "response-123")
        self.assertEqual(call_args.feedback_type, FeedbackType.HELPFUL)
        self.assertEqual(call_args.rating, 5)
        
        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["feedback_id"], "feedback-456")
    
    @patch('services.query_processor.get_feedback_service')
    def test_submit_feedback_unknown_response(self, mock_get_feedback_service):
        """Test submitting feedback for an unknown response ID."""
        # Setup mock feedback service
        mock_feedback_service = MagicMock()
        mock_feedback_service.submit_feedback.return_value = "feedback-789"
        mock_get_feedback_service.return_value = mock_feedback_service
        self.query_processor.feedback_service = mock_feedback_service
        
        # Test with unknown response ID
        feedback_data = {
            "feedback_type": FeedbackType.NOT_HELPFUL,
            "rating": 2,
            "query_text": "This is an unknown query",
            "issue_category": IssueCategory.MISUNDERSTOOD_QUERY,
            "comment": "The system didn't understand my question"
        }
        
        result = self.query_processor.submit_feedback(
            session_id="session-unknown",
            response_id="response-unknown",
            feedback_data=feedback_data
        )
        
        # Verify feedback service was called with fallback to provided data
        mock_feedback_service.submit_feedback.assert_called_once()
        call_args = mock_feedback_service.submit_feedback.call_args[0][0]
        self.assertEqual(call_args.session_id, "session-unknown")
        self.assertEqual(call_args.query_text, "This is an unknown query")
        self.assertEqual(call_args.response_id, "response-unknown")
        self.assertEqual(call_args.feedback_type, FeedbackType.NOT_HELPFUL)
        
        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["feedback_id"], "feedback-789")
    
    @patch('services.query_processor.get_feedback_service')
    def test_get_feedback_stats(self, mock_get_feedback_service):
        """Test getting feedback statistics through the query processor."""
        # Setup mock feedback service
        mock_feedback_service = MagicMock()
        mock_stats = MagicMock()
        mock_stats.to_dict.return_value = {
            "total_count": 100,
            "helpful_count": 80,
            "not_helpful_count": 20,
            "helpful_percentage": 80.0,
            "average_rating": 4.2,
            "issue_distribution": {
                IssueCategory.MISUNDERSTOOD_QUERY: 10,
                IssueCategory.INCORRECT_DATA: 5,
                IssueCategory.OTHER: 5
            },
            "top_query_intents": [
                {"intent": "menu_query", "count": 50},
                {"intent": "order_history", "count": 30}
            ]
        }
        mock_feedback_service.get_statistics.return_value = mock_stats
        mock_get_feedback_service.return_value = mock_feedback_service
        self.query_processor.feedback_service = mock_feedback_service
        
        # Get statistics
        result = self.query_processor.get_feedback_stats(time_period="month")
        
        # Verify feedback service was called with correct parameters
        mock_feedback_service.get_statistics.assert_called_once_with(time_period="month")
        
        # Verify result
        self.assertEqual(result["total_count"], 100)
        self.assertEqual(result["helpful_count"], 80)
        self.assertEqual(result["helpful_percentage"], 80.0)
        self.assertEqual(result["average_rating"], 4.2)
        self.assertEqual(len(result["top_query_intents"]), 2)
    
    @pytest.mark.asyncio
    @patch('services.query_processor.get_feedback_service')
    async def test_async_methods(self, mock_get_feedback_service):
        """Test the async versions of the feedback methods."""
        # Setup mock feedback service
        mock_feedback_service = MagicMock()
        mock_feedback_service.submit_feedback.return_value = "feedback-async"
        mock_stats = MagicMock()
        mock_stats.to_dict.return_value = {"total_count": 50}
        mock_feedback_service.get_statistics.return_value = mock_stats
        mock_get_feedback_service.return_value = mock_feedback_service
        self.query_processor.feedback_service = mock_feedback_service
        
        # Test async submit_feedback
        feedback_data = {"feedback_type": FeedbackType.HELPFUL}
        result = await self.query_processor.submit_feedback_async(
            session_id="session-async",
            response_id="response-async",
            feedback_data=feedback_data
        )
        
        # Verify result
        self.assertEqual(result["feedback_id"], "feedback-async")
        
        # Test async get_feedback_stats
        result = await self.query_processor.get_feedback_stats_async(time_period="week")
        self.assertEqual(result["total_count"], 50)
    
    def test_response_id_generation(self):
        """Test that a response ID is generated and tracked."""
        # Initialize a simplified mock setup
        with patch('services.query_processor.get_data_access') as mock_get_data_access, \
             patch('services.query_processor.ResponseService') as mock_response_service, \
             patch('services.query_processor.ContextManager') as mock_context_manager, \
             patch('services.query_processor.get_feedback_service') as mock_get_feedback_service, \
             patch('services.query_processor.QueryProcessor._process_data_query') as mock_process_data_query:
            
            # Setup mocks
            mock_data_access = MagicMock()
            mock_get_data_access.return_value = mock_data_access
            
            mock_context = MagicMock()
            mock_context_manager.return_value.update_context.return_value = mock_context
            
            # Set up the mock to return a simple response
            mock_process_data_query.return_value = {
                "type": "data",
                "content": "Here is the data",
                "data": []
            }
            
            # Create processor with mocks
            processor = QueryProcessor(self.config)
            
            # Process a query
            result = processor.process_query(
                query_text="Test query",
                session_id="test-session",
                classification_result={
                    "query_type": "menu_items",
                    "intent_type": "data_query",
                    "confidence": 0.95
                }
            )
            
            # Verify the response has a response_id
            self.assertIn("response_id", result)
            response_id = result["response_id"]
            
            # Verify the response was tracked
            self.assertIn(response_id, processor.response_history)
            tracked_info = processor.response_history[response_id]
            self.assertEqual(tracked_info["query_text"], "Test query")
            self.assertEqual(tracked_info["session_id"], "test-session")
            self.assertEqual(tracked_info["intent_type"], "data_query")


if __name__ == '__main__':
    unittest.main() 