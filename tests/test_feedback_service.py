"""
Tests for the Feedback Service implementation.
"""
import unittest
import tempfile
import shutil
import os
import json
from datetime import datetime, timedelta

from services.feedback.feedback_service import FeedbackService, get_feedback_service
from services.data.models.feedback import FeedbackModel, FeedbackStats, FeedbackType, IssueCategory


class TestFeedbackService(unittest.TestCase):
    """Tests for the FeedbackService class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for feedback storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create configuration with file storage pointing to temporary directory
        self.config = {
            "feedback_storage_type": "file",
            "feedback_storage_dir": self.temp_dir,
            "feedback_stats_cache_ttl": 10  # Short TTL for testing
        }
        
        # Create the service
        self.feedback_service = FeedbackService(self.config)
        
        # Sample feedback data
        self.sample_feedback = FeedbackModel(
            session_id="test-session-123",
            query_text="Show me the menu items",
            response_id="response-456",
            feedback_type=FeedbackType.HELPFUL,
            rating=5,
            original_intent="menu_query"
        )
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_get_feedback_service_factory(self):
        """Test the factory function to get a FeedbackService instance."""
        # Test with empty config
        service = get_feedback_service()
        self.assertIsInstance(service, FeedbackService)
        
        # Test with specific config
        service = get_feedback_service(self.config)
        self.assertIsInstance(service, FeedbackService)
        self.assertEqual(service.storage_type, "file")
        self.assertEqual(service.storage_dir, self.temp_dir)
    
    def test_submit_feedback_file_storage(self):
        """Test submitting feedback with file storage."""
        # Set up a temporary directory for file storage
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create feedback service with file storage
            service = FeedbackService({
                "feedback_storage_type": "file",
                "feedback_storage_dir": temp_dir
            })
            
            # Submit feedback
            feedback = FeedbackModel(
                session_id="test-session-12345",
                query_text="How many orders did we have last month?",
                response_id="resp-12345",
                feedback_type=FeedbackType.HELPFUL,
                rating=5
            )
            
            feedback_id = service.submit_feedback(feedback)
            
            # Verify feedback file was created
            filename = os.path.join(temp_dir, f"{feedback_id}.json")
            self.assertTrue(os.path.exists(filename))
            
            # Verify file content
            with open(filename, 'r') as f:
                data = json.load(f)
                self.assertEqual(data["feedback_id"], feedback_id)
                self.assertEqual(data["session_id"], "test-session-12345")
                self.assertEqual(data["feedback_type"], FeedbackType.HELPFUL)
                self.assertEqual(data["rating"], 5)
    
    def test_submit_feedback_memory_storage(self):
        """Test submitting feedback with memory storage."""
        # Create service with memory storage
        memory_config = {"feedback_storage_type": "memory"}
        memory_service = FeedbackService(memory_config)
        
        # Submit feedback
        feedback_id = memory_service.submit_feedback(self.sample_feedback)
        
        # Verify it was stored in memory
        self.assertEqual(len(memory_service.memory_storage), 1)
        stored_feedback = memory_service.memory_storage[0]
        self.assertEqual(stored_feedback.feedback_id, feedback_id)
        self.assertEqual(stored_feedback.session_id, "test-session-123")
    
    def test_get_feedback(self):
        """Test retrieving feedback."""
        # Submit multiple feedback items
        feedback1 = FeedbackModel(
            session_id="session-1",
            query_text="Query 1",
            feedback_type=FeedbackType.HELPFUL
        )
        feedback2 = FeedbackModel(
            session_id="session-2",
            query_text="Query 2",
            feedback_type=FeedbackType.NOT_HELPFUL
        )
        feedback3 = FeedbackModel(
            session_id="session-1",  # Same session as feedback1
            query_text="Query 3",
            feedback_type=FeedbackType.SPECIFIC_ISSUE,
            issue_category=IssueCategory.INCORRECT_DATA
        )
        
        id1 = self.feedback_service.submit_feedback(feedback1)
        id2 = self.feedback_service.submit_feedback(feedback2)
        id3 = self.feedback_service.submit_feedback(feedback3)
        
        # Test retrieval by ID
        result = self.feedback_service.get_feedback(feedback_id=id1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].feedback_id, id1)
        
        # Test retrieval by session ID
        result = self.feedback_service.get_feedback(session_id="session-1")
        self.assertEqual(len(result), 2)
        self.assertIn(result[0].query_text, ["Query 1", "Query 3"])
        self.assertIn(result[1].query_text, ["Query 1", "Query 3"])
        
        # Test pagination
        result = self.feedback_service.get_feedback(limit=1)
        self.assertEqual(len(result), 1)
    
    def test_get_statistics(self):
        """Test generating statistics from feedback."""
        # Submit various types of feedback
        for i in range(5):
            feedback = FeedbackModel(
                session_id=f"session-{i}",
                query_text=f"Query {i}",
                feedback_type=FeedbackType.HELPFUL,
                rating=5,
                original_intent="menu_query"
            )
            self.feedback_service.submit_feedback(feedback)
        
        for i in range(3):
            feedback = FeedbackModel(
                session_id=f"session-{i+10}",
                query_text=f"Query {i+10}",
                feedback_type=FeedbackType.NOT_HELPFUL,
                rating=2,
                issue_category=IssueCategory.MISUNDERSTOOD_QUERY,
                original_intent="order_history"
            )
            self.feedback_service.submit_feedback(feedback)
        
        # Get statistics
        stats = self.feedback_service.get_statistics()
        
        # Verify counts
        self.assertEqual(stats.total_count, 8)
        self.assertEqual(stats.helpful_count, 5)
        self.assertEqual(stats.not_helpful_count, 3)
        
        # Verify average rating (should be around 3.875 - (5*5 + 3*2)/8)
        self.assertAlmostEqual(stats.average_rating, 3.875, places=1)
        
        # Verify issue distribution
        self.assertIn(IssueCategory.MISUNDERSTOOD_QUERY, stats.issue_distribution)
        self.assertEqual(stats.issue_distribution[IssueCategory.MISUNDERSTOOD_QUERY], 3)
        
        # Verify intents
        self.assertEqual(len(stats.top_query_intents), 2)
        
        # Test statistics caching
        # Add another feedback, but stats should remain the same due to caching
        feedback = FeedbackModel(
            session_id="session-new",
            query_text="New query",
            feedback_type=FeedbackType.HELPFUL
        )
        self.feedback_service.submit_feedback(feedback)
        
        cached_stats = self.feedback_service.get_statistics()
        self.assertEqual(cached_stats.total_count, 8)  # Still 8, not 9
        
        # Force refresh
        fresh_stats = self.feedback_service.get_statistics(force_refresh=True)
        self.assertEqual(fresh_stats.total_count, 9)  # Now 9
    
    def test_export_feedback(self):
        """Test exporting feedback for analysis."""
        # Add some feedback
        for i in range(5):
            feedback = FeedbackModel(
                session_id=f"session-{i}",
                query_text=f"Query {i}",
                feedback_type=FeedbackType.HELPFUL
            )
            self.feedback_service.submit_feedback(feedback)
        
        # Export as CSV
        csv_path = self.feedback_service.export_feedback_for_analysis(format='csv')
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(csv_path.endswith('.csv'))
        
        # Export as JSON
        json_path = self.feedback_service.export_feedback_for_analysis(format='json')
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(json_path.endswith('.json'))
        
        # Verify JSON contents
        with open(json_path, 'r') as f:
            exported_data = json.load(f)
        
        self.assertEqual(len(exported_data), 5)
        self.assertEqual(exported_data[0]["feedback_type"], FeedbackType.HELPFUL)
    
    def test_store_query_response(self):
        """Test storing query and response for later feedback reference."""
        # Create feedback service
        service = FeedbackService({
            "feedback_storage_type": "memory"
        })
        
        # Sample response data
        response_id = "response-12345"
        session_id = "session-6789"
        query_text = "What were our best selling items last week?"
        query_type = "order_history"
        response = {
            "type": "data_response",
            "message": "Here are your best selling items",
            "data": [{"item": "Pizza", "count": 120}, {"item": "Burger", "count": 95}],
            "response_id": response_id
        }
        metadata = {
            "classification_confidence": 0.98,
            "processing_time": 0.45
        }
        
        # Store the query-response pair
        service.store_query_response(
            session_id=session_id,
            response_id=response_id,
            query_text=query_text,
            query_type=query_type,
            response=response,
            metadata=metadata
        )
        
        # Retrieve the stored response
        retrieved = service.get_response(response_id)
        
        # Verify retrieved data
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["session_id"], session_id)
        self.assertEqual(retrieved["response_id"], response_id)
        self.assertEqual(retrieved["query_text"], query_text)
        self.assertEqual(retrieved["query_type"], query_type)
        self.assertEqual(retrieved["response"]["type"], "data_response")
        self.assertEqual(retrieved["metadata"]["classification_confidence"], 0.98)
        
        # Test retrieval of non-existent response
        none_response = service.get_response("non-existent-id")
        self.assertIsNone(none_response)
        
    def test_store_and_get_response_file_storage(self):
        """Test storing and retrieving responses with file storage."""
        # Set up a temporary directory for file storage
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create feedback service with file storage
            service = FeedbackService({
                "feedback_storage_type": "file",
                "feedback_storage_dir": temp_dir
            })
            
            # Sample response data
            response_id = "file-response-12345"
            session_id = "session-file-test"
            query_text = "Update the price of Caesar Salad to $12.99"
            query_type = "action_request"
            response = {
                "type": "action_response",
                "message": "Price updated successfully",
                "response_id": response_id
            }
            
            # Store the query-response pair
            service.store_query_response(
                session_id=session_id,
                response_id=response_id,
                query_text=query_text,
                query_type=query_type,
                response=response
            )
            
            # Verify response file was created
            response_dir = os.path.join(temp_dir, 'responses')
            response_file = os.path.join(response_dir, f"{response_id}.json")
            self.assertTrue(os.path.exists(response_file))
            
            # Retrieve and verify
            retrieved = service.get_response(response_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["response_id"], response_id)
            self.assertEqual(retrieved["query_type"], "action_request")


if __name__ == '__main__':
    unittest.main() 