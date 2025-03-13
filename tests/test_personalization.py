"""
Tests for the personalization features of the Swoop AI system.
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile
import json
from datetime import datetime
from collections import Counter, defaultdict
import time

from services.context_manager import UserProfile, ConversationContext, ContextManager
from services.query_processor import QueryProcessor
from services.response.response_generator import ResponseGenerator


class TestUserProfile(unittest.TestCase):
    """Tests for the UserProfile class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.profile = UserProfile(self.user_id)
    
    def test_initialization(self):
        """Test that a UserProfile is initialized with default values."""
        # Check basic properties
        self.assertEqual(self.profile.user_id, self.user_id)
        self.assertIsInstance(self.profile.creation_date, datetime)
        self.assertIsInstance(self.profile.last_active, datetime)
        
        # Check default preferences
        self.assertEqual(self.profile.preferences["detail_level"], "standard")
        self.assertEqual(self.profile.preferences["response_tone"], "professional")
        self.assertEqual(self.profile.preferences["chart_preference"], "auto")
        self.assertFalse(self.profile.preferences["voice_enabled"])
        
        # Check counters and statistics
        self.assertEqual(self.profile.stats["total_queries"], 0)
        self.assertEqual(self.profile.stats["total_sessions"], 0)
        self.assertEqual(len(self.profile.frequent_entities), 0)
        self.assertEqual(len(self.profile.frequent_topics), 0)
    
    def test_update_with_query(self):
        """Test that profile is updated correctly with query information."""
        # Test data
        query_text = "Show sales for burger category last month"
        query_type = "data_query"
        entities = {
            "menu_items": [
                {"name": "burger", "id": 123}
            ],
            "time_period": [
                {"name": "month", "qualifier": "last"}
            ]
        }
        topic = "order_history"
        
        # Update profile
        self.profile.update_with_query(query_text, query_type, entities, topic)
        
        # Check stats updates
        self.assertEqual(self.profile.stats["total_queries"], 1)
        self.assertEqual(self.profile.stats["queries_by_category"]["data_query"], 1)
        
        # Check entity tracking
        self.assertEqual(self.profile.frequent_entities["menu_items:burger"], 1)
        
        # Check topic tracking
        self.assertEqual(self.profile.frequent_topics["order_history"], 1)
        
        # Check recent queries
        self.assertEqual(len(self.profile.recent_queries), 1)
        self.assertEqual(self.profile.recent_queries[0]["text"], query_text)
        self.assertEqual(self.profile.recent_queries[0]["type"], query_type)
        self.assertEqual(self.profile.recent_queries[0]["topic"], topic)
    
    def test_multiple_query_updates(self):
        """Test that profile tracks multiple queries correctly."""
        # First query
        self.profile.update_with_query(
            "Show sales for burger category last month", 
            "data_query", 
            {"menu_items": [{"name": "burger", "id": 123}]}, 
            "order_history"
        )
        
        # Second query with same entity
        self.profile.update_with_query(
            "How many burger meals were sold last week?", 
            "data_query", 
            {"menu_items": [{"name": "burger", "id": 123}]}, 
            "order_history"
        )
        
        # Third query with different entity and topic
        self.profile.update_with_query(
            "Update price of pizza to $15", 
            "action_request", 
            {"menu_items": [{"name": "pizza", "id": 456}]}, 
            "menu_update"
        )
        
        # Check entity frequencies
        self.assertEqual(self.profile.frequent_entities["menu_items:burger"], 2)
        self.assertEqual(self.profile.frequent_entities["menu_items:pizza"], 1)
        
        # Check topic frequencies
        self.assertEqual(self.profile.frequent_topics["order_history"], 2)
        self.assertEqual(self.profile.frequent_topics["menu_update"], 1)
        
        # Check topic transitions
        self.assertEqual(self.profile.topic_transitions["order_history"]["menu_update"], 1)
        
        # Check query count
        self.assertEqual(self.profile.stats["total_queries"], 3)
        self.assertEqual(self.profile.stats["queries_by_category"]["data_query"], 2)
        self.assertEqual(self.profile.stats["queries_by_category"]["action_request"], 1)
    
    def test_update_preference(self):
        """Test updating user preferences."""
        # Valid preference update
        result = self.profile.update_preference("detail_level", "concise")
        self.assertTrue(result)
        self.assertEqual(self.profile.preferences["detail_level"], "concise")
        
        # Invalid preference value
        result = self.profile.update_preference("detail_level", "super-detailed")
        self.assertFalse(result)
        self.assertEqual(self.profile.preferences["detail_level"], "concise")  # Unchanged
        
        # Non-existent preference
        result = self.profile.update_preference("nonexistent", "value")
        self.assertFalse(result)
    
    def test_get_personalization_context(self):
        """Test generating personalization context from the profile."""
        # Add some data to the profile
        self.profile.frequent_entities = Counter({
            "menu_items:burger": 5,
            "menu_items:fries": 3,
            "menu_items:pizza": 1,
            "categories:desserts": 2
        })
        
        self.profile.frequent_topics = Counter({
            "order_history": 4,
            "menu_update": 2,
            "menu_query": 1
        })
        
        self.profile.preferences["detail_level"] = "detailed"
        
        # Add some queries to trigger expertise calculation
        for i in range(25):  # Make them "intermediate" level
            self.profile.stats["total_queries"] += 1
        
        # Get context
        context = self.profile.get_personalization_context()
        
        # Check that key data is present
        self.assertEqual(context["preferences"]["detail_level"], "detailed")
        self.assertEqual(context["expertise_level"], "intermediate")
        
        # Check top entities
        self.assertIn("burger", context["frequent_entities"])
        self.assertIn("fries", context["frequent_entities"])
        
        # Check top topics
        self.assertIn("order_history", context["frequent_topics"])
        self.assertIn("menu_update", context["frequent_topics"])
    
    def test_session_tracking(self):
        """Test session start/end functionality."""
        # Start session
        self.profile.start_session()
        self.assertEqual(self.profile.stats["total_sessions"], 1)
        self.assertTrue(hasattr(self.profile, 'session_start_time'))
        
        # Add a small sleep to ensure time difference
        time.sleep(0.01)
        
        # End session
        self.profile.end_session()
        self.assertFalse(hasattr(self.profile, 'session_start_time'))
        self.assertGreater(self.profile.stats["total_time_spent"], 0)
    
    def test_serialization(self):
        """Test to_dict and from_dict methods."""
        # Add some data to the profile
        self.profile.update_with_query(
            "Show sales for burger category last month", 
            "data_query", 
            {"menu_items": [{"name": "burger", "id": 123}]}, 
            "order_history"
        )
        
        self.profile.update_preference("detail_level", "detailed")
        self.profile.start_session()
        
        # Convert to dict
        profile_dict = self.profile.to_dict()
        
        # Check that key data is present in the dict
        self.assertEqual(profile_dict["user_id"], self.user_id)
        self.assertEqual(profile_dict["preferences"]["detail_level"], "detailed")
        self.assertEqual(profile_dict["stats"]["total_queries"], 1)
        self.assertEqual(profile_dict["frequent_entities"]["menu_items:burger"], 1)
        
        # Create a new profile from dict
        new_profile = UserProfile.from_dict(profile_dict)
        
        # Verify the new profile has the same data
        self.assertEqual(new_profile.user_id, self.user_id)
        self.assertEqual(new_profile.preferences["detail_level"], "detailed")
        self.assertEqual(new_profile.stats["total_queries"], 1)
        self.assertEqual(new_profile.frequent_entities["menu_items:burger"], 1)


class TestPersonalizationIntegration(unittest.TestCase):
    """Tests for the integration of personalization features."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for user profiles
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a context manager with profile storage
        self.context_manager = ContextManager(
            expiry_minutes=30,
            profile_storage_path=self.temp_dir
        )
        
        # Test session and user IDs
        self.session_id = "test-session-123"
        self.user_id = "test-user-456"
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_context_with_user_profile(self):
        """Test that ConversationContext integrates with UserProfile."""
        # Get context with user ID
        context = self.context_manager.get_context(self.session_id, self.user_id)
        
        # Verify user profile was created
        self.assertTrue(hasattr(context, 'user_profile'))
        self.assertEqual(context.user_profile.user_id, self.user_id)
        
        # Update with a query
        classification_result = {
            "query_type": "data_query",
            "confidence": 0.9,
            "parameters": {
                "entities": {
                    "menu_items": [{"name": "burger", "id": 123}]
                }
            }
        }
        
        context.update_with_query("Show burger sales", classification_result)
        
        # Check that user profile was updated
        self.assertEqual(context.user_profile.stats["total_queries"], 1)
        self.assertEqual(context.user_profile.frequent_entities["menu_items:burger"], 1)
    
    def test_get_personalization_hints(self):
        """Test that ConversationContext provides personalization hints."""
        # Get context with user ID
        context = self.context_manager.get_context(self.session_id, self.user_id)
        
        # Add some history and preferences
        context.user_profile.update_preference("detail_level", "concise")
        context.user_profile.update_preference("response_tone", "friendly")
        
        # Update with some queries
        for i in range(3):
            classification_result = {
                "query_type": "data_query",
                "confidence": 0.9,
                "parameters": {
                    "entities": {
                        "menu_items": [{"name": f"item{i}", "id": i}]
                    }
                }
            }
            query = f"Tell me about item{i}"
            context.update_with_query(query, classification_result)
        
        # Get personalization hints
        hints = context.get_personalization_hints()
        
        # Verify key elements are present
        self.assertEqual(hints["preferences"]["detail_level"], "concise")
        self.assertEqual(hints["preferences"]["response_tone"], "friendly")
        self.assertEqual(hints["expertise_level"], "beginner")  # Only 3 queries
        
        # Check session context
        self.assertTrue("session_context" in hints)
        self.assertEqual(len(hints["session_context"]["recent_queries"]), 3)
    
    def test_profile_persistence(self):
        """Test that user profiles are persisted and loaded."""
        # Get context with user ID
        context = self.context_manager.get_context(self.session_id, self.user_id)
        
        # Update preferences and add some queries
        context.user_profile.update_preference("detail_level", "detailed")
        context.update_with_query("Test query", {"query_type": "data_query", "confidence": 0.9, "parameters": {}})
        
        # Persist the profile
        self.context_manager.persist_user_profile(self.user_id)
        
        # Verify file was created
        profile_path = os.path.join(self.temp_dir, f"{self.user_id}.json")
        self.assertTrue(os.path.exists(profile_path))
        
        # Create a new context manager and load the profile
        new_context_manager = ContextManager(
            expiry_minutes=30,
            profile_storage_path=self.temp_dir
        )
        
        # Get context with same user ID
        new_context = new_context_manager.get_context("new-session-id", self.user_id)
        
        # Verify profile was loaded
        self.assertEqual(new_context.user_profile.preferences["detail_level"], "detailed")
        self.assertEqual(new_context.user_profile.stats["total_queries"], 1)
    
    @patch('services.response.response_generator.ResponseGenerator._build_system_message')
    def test_response_generator_personalization(self, mock_build_message):
        """Test that ResponseGenerator uses personalization information."""
        # Mock config
        config = {
            "templates_dir": "templates",
            "default_model": "gpt-3.5-turbo",
            "api": {"openai": {"api_key": "fake-key"}}
        }
        
        # Create response generator
        response_generator = ResponseGenerator(config)
        
        # Create a context with personalization hints
        context_hints = {
            "preferences": {
                "detail_level": "concise",
                "response_tone": "friendly"
            },
            "expertise_level": "intermediate",
            "frequent_entities": ["burger", "fries"],
            "session_context": {
                "recent_queries": ["How many burgers sold?", "What are the sales trends?"],
                "entity_focus": ["burger"]
            }
        }
        
        # Mock the response for testing
        mock_build_message.return_value = "Personalized system message"
        
        # Call generate method with context containing personalization
        response_generator.generate(
            query="How are sales?",
            category="data_query",
            response_rules={},
            query_results=[{"data": "example"}],
            context={"personalization_hints": context_hints}
        )
        
        # Verify that personalization was passed to _build_system_message
        mock_build_message.assert_called_once()
        _, _, personalization = mock_build_message.call_args[0]
        
        # Check that personalization contains key elements
        self.assertEqual(personalization["preferences"]["detail_level"], "concise")
        self.assertEqual(personalization["preferences"]["response_tone"], "friendly")


if __name__ == '__main__':
    unittest.main() 