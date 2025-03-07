"""
Unit tests for the SessionManager class.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from frontend.session_manager import SessionManager


class TestSessionManager:
    """Test class for the SessionManager."""

    @patch('frontend.session_manager.st')
    def test_initialize_session(self, mock_st):
        """Test that initialize_session correctly sets up session state variables."""
        # Setup mock state
        mock_st.session_state = {}

        # Call the method
        SessionManager.initialize_session()

        # Verify session state was properly initialized
        assert "history" in mock_st.session_state
        assert isinstance(mock_st.session_state["history"], list)
        assert "context" in mock_st.session_state
        assert isinstance(mock_st.session_state["context"], dict)
        assert "ui_state" in mock_st.session_state
        assert isinstance(mock_st.session_state["ui_state"], dict)

        # Verify default values
        assert mock_st.session_state["context"]["user_preferences"] == {}
        assert mock_st.session_state["context"]["recent_queries"] == []
        assert mock_st.session_state["context"]["active_conversation"] is True
        assert mock_st.session_state["ui_state"]["show_sql"] is False
        assert mock_st.session_state["ui_state"]["show_results"] is False
        assert mock_st.session_state["ui_state"]["current_view"] == "chat"

    @patch('frontend.session_manager.st')
    def test_get_context(self, mock_st):
        """Test that get_context returns the expected context dictionary."""
        # Setup mock state
        mock_st.session_state = {
            "history": [{"query": "test", "response": "test response"}],
            "context": {
                "user_preferences": {"theme": "dark"},
                "recent_queries": ["test query"],
                "active_conversation": True
            }
        }

        # Call the method
        context = SessionManager.get_context()

        # Verify context was correctly built
        assert context["session_history"] == mock_st.session_state["history"]
        assert context["user_preferences"] == {"theme": "dark"}
        assert context["recent_queries"] == ["test query"]

    @patch('frontend.session_manager.st')
    def test_update_history(self, mock_st):
        """Test that update_history correctly updates the session history."""
        # Setup mock state
        mock_st.session_state = {
            "history": [],
            "context": {
                "recent_queries": []
            }
        }

        # Mock response data
        response = {
            "response": "Test response",
            "category": "test_category",
            "sql_query": "SELECT * FROM test",
            "query_results": [{"id": 1, "name": "test"}],
            "timestamp": 1234567890
        }

        # Call the method
        SessionManager.update_history("Test query", response)

        # Verify history was updated
        assert len(mock_st.session_state["history"]) == 1
        entry = mock_st.session_state["history"][0]
        assert entry["query"] == "Test query"
        assert entry["response"] == "Test response"
        assert entry["category"] == "test_category"
        assert entry["timestamp"] == 1234567890
        assert "metadata" in entry
        assert entry["metadata"]["sql_query"] == "SELECT * FROM test"
        assert entry["metadata"]["query_results"] == [{"id": 1, "name": "test"}]

        # Verify recent queries was updated
        assert mock_st.session_state["context"]["recent_queries"] == ["Test query"]

    @patch('frontend.session_manager.st')
    def test_update_history_limit_recent_queries(self, mock_st):
        """Test that update_history limits the recent queries list to 10 items."""
        # Setup mock state with 10 existing queries
        existing_queries = [f"query_{i}" for i in range(10)]
        mock_st.session_state = {
            "history": [],
            "context": {
                "recent_queries": existing_queries
            }
        }

        # Mock response data
        response = {
            "response": "New response",
            "category": "test_category"
        }

        # Call the method
        SessionManager.update_history("new query", response)

        # Verify recent queries is limited to 10 items
        recent_queries = mock_st.session_state["context"]["recent_queries"]
        assert len(recent_queries) == 10
        assert recent_queries[9] == "new query"  # Most recent is at the end
        assert recent_queries[0] == "query_1"    # Oldest query was removed 