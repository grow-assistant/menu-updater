"""
Integration tests for the updated service flow.

Tests the end-to-end functionality of the updated components:
- SessionManager
- ServiceRegistry
- OrchestratorService
- ClassificationService
"""

import pytest
from unittest.mock import patch, MagicMock, call
import streamlit as st
import json
from typing import Dict, Any

from frontend.session_manager import SessionManager
from services.utils.service_registry import ServiceRegistry
from services.orchestrator.orchestrator import OrchestratorService
from services.classification.classifier import ClassificationService


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "api": {
            "openai": {
                "api_key": "test_openai_key",
                "model": "gpt-4"
            },
            "gemini": {
                "api_key": "test_gemini_key"
            }
        },
        "database": {
            "connection_string": "postgresql://test:test@localhost/testdb"
        },
        "services": {
            "classification": {
                "confidence_threshold": 0.7
            },
            "rules": {
                "rules_path": "test_rules_path"
            },
            "sql_generator": {
                "template_path": "test_template_path"
            }
        }
    }


class TestUpdatedServiceFlow:
    """Integration tests for the updated service flow."""
    
    def setup_method(self):
        """Setup method that runs before each test."""
        # Reset the ServiceRegistry
        ServiceRegistry._services = {}
        ServiceRegistry._config = None
        
        # Reset Streamlit session state if it exists
        if hasattr(st, "session_state"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
    
    @patch('frontend.session_manager.st')
    @patch('services.classification.classifier.openai')
    @patch('services.orchestrator.orchestrator.ServiceRegistry')
    def test_end_to_end_query_flow(self, mock_registry, mock_openai, mock_st, mock_config):
        """Test the end-to-end flow from session state through orchestrator to response."""
        # Setup session state
        mock_st.session_state = {}
        
        # Initialize session
        SessionManager.initialize_session()
        
        # Setup mock services
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = "data_query"
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "sql_examples": ["SELECT * FROM menu"],
            "response_rules": {"format": "table"}
        }
        
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate_sql.return_value = "SELECT * FROM menu WHERE price < 10"
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = [{"id": 1, "name": "Burger", "price": 8.99}]
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Here are the menu items under $10"
        
        # Mock ServiceRegistry.get_service to return our mock services
        def mock_get_service(service_name):
            if service_name == "classification":
                return mock_classifier
            elif service_name == "rules":
                return mock_rules
            elif service_name == "sql_generator":
                return mock_sql_generator
            elif service_name == "execution":
                return mock_executor
            elif service_name == "response":
                return mock_response
        
        mock_registry.get_service.side_effect = mock_get_service
        
        # Initialize orchestrator
        orchestrator = OrchestratorService(mock_config)
        
        # Process a query
        query = "Show me menu items under $10"
        context = SessionManager.get_context()
        result = orchestrator.process_query(query, context)
        
        # Update history
        SessionManager.update_history(query, result)
        
        # Verify service calls
        mock_classifier.classify.assert_called_once_with(query, context)
        mock_rules.get_rules_and_examples.assert_called_once_with("data_query")
        mock_sql_generator.generate_sql.assert_called_once_with(
            query, 
            ["SELECT * FROM menu"],
            context
        )
        mock_executor.execute.assert_called_once_with("SELECT * FROM menu WHERE price < 10")
        mock_response.generate.assert_called_once_with(
            query,
            "data_query",
            {"format": "table"},
            [{"id": 1, "name": "Burger", "price": 8.99}],
            context
        )
        
        # Verify session history was updated
        assert len(mock_st.session_state.history) == 1
        entry = mock_st.session_state.history[0]
        assert entry["query"] == query
        assert entry["response"] == "Here are the menu items under $10"
        assert entry["category"] == "data_query"
        assert "metadata" in entry
        assert entry["metadata"]["sql_query"] == "SELECT * FROM menu WHERE price < 10"
        
        # Verify recent queries was updated
        assert mock_st.session_state.context["recent_queries"] == [query]
    
    @patch('frontend.session_manager.st')
    @patch('services.orchestrator.orchestrator.ServiceRegistry')
    def test_conversation_context_preservation(self, mock_registry, mock_st, mock_config):
        """Test that conversation context is preserved across multiple queries."""
        # Setup session state with existing history
        mock_st.session_state = {
            "history": [
                {
                    "query": "What's on the menu?",
                    "response": "We have burgers, salads, and more.",
                    "category": "general",
                    "timestamp": 1000,
                    "metadata": {}
                }
            ],
            "context": {
                "user_preferences": {"favorite": "burger"},
                "recent_queries": ["What's on the menu?"],
                "active_conversation": True
            },
            "ui_state": {
                "show_sql": False,
                "show_results": False,
                "current_view": "chat"
            }
        }
        
        # Setup mock services
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = "data_query"
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "sql_examples": [],
            "response_rules": {}
        }
        
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate_sql.return_value = "SELECT * FROM menu WHERE category = 'burger'"
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = [{"id": 1, "name": "Cheeseburger", "price": 10.99}]
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Here are our burger options"
        
        # Mock ServiceRegistry.get_service
        def mock_get_service(service_name):
            if service_name == "classification":
                return mock_classifier
            elif service_name == "rules":
                return mock_rules
            elif service_name == "sql_generator":
                return mock_sql_generator
            elif service_name == "execution":
                return mock_executor
            elif service_name == "response":
                return mock_response
        
        mock_registry.get_service.side_effect = mock_get_service
        
        # Initialize orchestrator
        orchestrator = OrchestratorService(mock_config)
        
        # Get context and verify it contains previous history
        context = SessionManager.get_context()
        assert len(context["session_history"]) == 1
        assert context["user_preferences"]["favorite"] == "burger"
        assert context["recent_queries"] == ["What's on the menu?"]
        
        # Process a follow-up query
        query = "Show me burger options"
        result = orchestrator.process_query(query, context)
        
        # Update history
        SessionManager.update_history(query, result)
        
        # Verify the classifier received the previous history in the context
        mock_classifier.classify.assert_called_once()
        call_args = mock_classifier.classify.call_args[0]
        assert call_args[0] == query
        assert len(call_args[1]["session_history"]) == 1
        assert call_args[1]["user_preferences"]["favorite"] == "burger"
        
        # Verify history was updated correctly
        assert len(mock_st.session_state.history) == 2
        assert mock_st.session_state.history[1]["query"] == query
        assert mock_st.session_state.history[1]["response"] == "Here are our burger options"
        
        # Verify recent queries was updated
        assert mock_st.session_state.context["recent_queries"] == ["What's on the menu?", query]
    
    @patch('frontend.session_manager.st')
    @patch('services.orchestrator.orchestrator.ServiceRegistry')
    def test_error_handling_and_recovery(self, mock_registry, mock_st, mock_config):
        """Test that errors are handled gracefully and the system can recover."""
        # Setup session state
        mock_st.session_state = {}
        SessionManager.initialize_session()
        
        # Setup mock services - SQL generator will fail
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = "data_query"
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "sql_examples": ["SELECT * FROM menu"],
            "response_rules": {"format": "table"}
        }
        
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate_sql.side_effect = Exception("SQL generation failed")
        
        mock_executor = MagicMock()
        mock_response = MagicMock()
        
        # Mock ServiceRegistry.get_service
        def mock_get_service(service_name):
            if service_name == "classification":
                return mock_classifier
            elif service_name == "rules":
                return mock_rules
            elif service_name == "sql_generator":
                return mock_sql_generator
            elif service_name == "execution":
                return mock_executor
            elif service_name == "response":
                return mock_response
        
        mock_registry.get_service.side_effect = mock_get_service
        
        # Initialize orchestrator
        orchestrator = OrchestratorService(mock_config)
        
        # Process a query that will fail
        query = "Show me menu items"
        context = SessionManager.get_context()
        result = orchestrator.process_query(query, context)
        
        # Verify error response
        assert "error" in result
        assert result["category"] == "error"
        assert "SQL generation failed" in result["response"]
        
        # Update history with the error
        SessionManager.update_history(query, result)
        
        # Verify history contains the error
        assert len(mock_st.session_state.history) == 1
        assert mock_st.session_state.history[0]["category"] == "error"
        
        # Now set up for a successful query
        mock_sql_generator.generate_sql.side_effect = None
        mock_sql_generator.generate_sql.return_value = "SELECT * FROM menu"
        mock_executor.execute.return_value = [{"id": 1, "name": "Burger", "price": 8.99}]
        mock_response.generate.return_value = "Here's the menu"
        
        # Process a new query
        query = "What's on the menu?"
        context = SessionManager.get_context()  # Should include previous error in history
        result = orchestrator.process_query(query, context)
        
        # Verify successful response
        assert result["category"] == "data_query"
        assert result["response"] == "Here's the menu"
        
        # Update history
        SessionManager.update_history(query, result)
        
        # Verify history now has both the error and successful query
        assert len(mock_st.session_state.history) == 2
        assert mock_st.session_state.history[0]["category"] == "error"
        assert mock_st.session_state.history[1]["category"] == "data_query" 