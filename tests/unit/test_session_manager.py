"""
Unit tests for the SessionManager class.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from frontend.session_manager import SessionManager


class SessionStateMock:
    """A mock for Streamlit's session_state that supports both dict and dot notation access."""
    def __init__(self, initial_data=None):
        self.__dict__.update(initial_data or {})
    
    def __getitem__(self, key):
        return self.__dict__[key]
    
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    
    def __contains__(self, key):
        return key in self.__dict__

class TestSessionManager:
    """Test class for the SessionManager."""

    @patch('frontend.session_manager.st')
    def test_initialize_session(self, mock_st):
        """Test that initialize_session correctly sets up session state variables."""
        # Setup mock state as an object with dot notation access
        mock_st.session_state = SessionStateMock()

        # Call the method
        SessionManager.initialize_session()

        # Verify session state was properly initialized
        assert hasattr(mock_st.session_state, "history")
        assert isinstance(mock_st.session_state.history, list)
        assert hasattr(mock_st.session_state, "context")
        assert isinstance(mock_st.session_state.context, dict)
        assert hasattr(mock_st.session_state, "ui_state")
        assert isinstance(mock_st.session_state.ui_state, dict)

        # Verify default values
        assert mock_st.session_state.context["user_preferences"] == {}
        assert mock_st.session_state.context["recent_queries"] == []
        assert mock_st.session_state.context["active_conversation"] is True
        assert mock_st.session_state.ui_state["show_sql"] is False
        assert mock_st.session_state.ui_state["show_results"] is False
        assert mock_st.session_state.ui_state["current_view"] == "chat"

    @patch('frontend.session_manager.st')
    def test_get_context(self, mock_st):
        """Test that get_context returns the expected context dictionary."""
        # Setup mock state with dot notation access
        mock_st.session_state = SessionStateMock({
            "history": [{"query": "test", "response": "test response"}],
            "context": {
                "user_preferences": {"theme": "dark"},
                "recent_queries": ["test query"],
                "active_conversation": True
            },
            "voice_enabled": True,
            "persona": "casual"
        })

        # Call the method
        context = SessionManager.get_context()

        # Verify returned context
        assert context["session_history"] == mock_st.session_state.history
        assert context["user_preferences"] == {"theme": "dark"}
        assert context["recent_queries"] == ["test query"]
        assert context["enable_verbal"] is True
        assert context["persona"] == "casual"

    @patch('frontend.session_manager.st')
    def test_update_history(self, mock_st):
        """Test that update_history correctly adds items to history."""
        # Setup mock state with dot notation access
        mock_st.session_state = SessionStateMock({
            "history": [],
            "context": {
                "recent_queries": []
            }
        })

        # Test query and response
        query = "Test query"
        result = {
            "category": "test_category",
            "response": "Test response",
            "sql_query": "SELECT * FROM test",
            "query_results": [{"id": 1, "name": "test"}]
        }

        # Call the method
        SessionManager.update_history(query, result)

        # Verify history was updated
        assert len(mock_st.session_state.history) == 1
        assert mock_st.session_state.history[0]["query"] == "Test query"
        assert mock_st.session_state.history[0]["response"] == "Test response"
        assert mock_st.session_state.history[0]["category"] == "test_category"
        assert mock_st.session_state.history[0]["sql_query"] == "SELECT * FROM test"
        assert mock_st.session_state.history[0]["results"] == [{"id": 1, "name": "test"}]

        # Verify recent_queries was updated
        assert len(mock_st.session_state.context["recent_queries"]) == 1
        assert mock_st.session_state.context["recent_queries"][0] == "Test query"

    @patch('frontend.session_manager.st')
    def test_update_history_limit_recent_queries(self, mock_st):
        """Test that update_history limits the recent queries list to 10 items."""
        # Setup mock state with 10 existing queries
        existing_queries = [f"query_{i}" for i in range(10)]
        mock_st.session_state = SessionStateMock({
            "history": [],
            "context": {
                "recent_queries": existing_queries
            }
        })

        # Mock response data
        response = {
            "response": "New response",
            "category": "test_category"
        }

        # Call the method
        SessionManager.update_history("new query", response)

        # Verify the oldest query was removed
        recent_queries = mock_st.session_state.context["recent_queries"]
        assert len(recent_queries) == 10
        assert "query_0" not in recent_queries
        assert "new query" in recent_queries 