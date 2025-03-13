"""
Integration tests for the frontend module interacting with the backend services.

Tests the integration between:
- Frontend module
- SessionManager
- OrchestratorService (via ServiceRegistry)
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
import streamlit as st
import pandas as pd
import json
from datetime import datetime

from frontend.session_manager import SessionManager
from frontend.streamlit_app import display_chat_message, process_user_input, initialize_ui
from services.utils.service_registry import ServiceRegistry


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "api": {
            "openai": {
                "api_key": "test_openai_key",
                "model": "gpt-4o-mini"
            }
        },
        "database": {
            "connection_string": "postgresql://test:test@localhost/testdb"
        },
        "services": {
            "classification": {
                "confidence_threshold": 0.7
            }
        }
    }


class TestFrontendIntegration:
    """Integration tests for the frontend module with backend services."""
    
    def setup_method(self):
        """Setup method that runs before each test."""
        # Reset the ServiceRegistry
        ServiceRegistry._services = {}
        ServiceRegistry._config = None
        
        # Reset Streamlit session state
        if hasattr(st, "session_state"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
    
    @patch('frontend.streamlit_app.st')
    @patch('frontend.streamlit_app.OrchestratorService')
    def test_initialize_ui(self, mock_orchestrator_class, mock_st, mock_config):
        """Test that the UI initializes correctly."""
        # Mock the session state
        mock_st.session_state = {}
        
        # Call initialize_ui
        initialize_ui(mock_config)
        
        # Verify SessionManager was initialized
        assert "history" in mock_st.session_state
        assert "context" in mock_st.session_state
        assert "ui_state" in mock_st.session_state
        
        # Verify orchestrator was created
        mock_orchestrator_class.assert_called_once_with(mock_config)
    
    @patch('frontend.streamlit_app.st')
    @patch('frontend.streamlit_app.display_chat_message')
    def test_display_chat_history(self, mock_display_chat, mock_st):
        """Test that chat history is displayed correctly."""
        # Setup mock session state with history
        mock_st.session_state = {
            "history": [
                {
                    "query": "Show me menu items",
                    "response": "Here are the menu items",
                    "category": "data_query",
                    "timestamp": datetime.now().timestamp(),
                    "metadata": {
                        "sql_query": "SELECT * FROM menu",
                        "results": [{"name": "Burger", "price": 9.99}]
                    }
                },
                {
                    "query": "What's popular?",
                    "response": "Our burgers are popular",
                    "category": "general",
                    "timestamp": datetime.now().timestamp(),
                    "metadata": {}
                }
            ]
        }
        
        # Create a mock container for displaying messages
        mock_container = MagicMock()
        mock_st.container.return_value = mock_container
        
        # Import the function directly to ensure we use the patched version
        from frontend.streamlit_app import display_chat_history
        
        # Call function to display chat history
        display_chat_history(mock_st.session_state["history"], mock_container)
        
        # Verify display_chat_message was called with correct arguments
        assert mock_display_chat.call_count == 4
        mock_display_chat.assert_any_call("Show me menu items", "user", mock_container)
        mock_display_chat.assert_any_call("Here are the menu items", "assistant", mock_container)
        mock_display_chat.assert_any_call("What's popular?", "user", mock_container)
        mock_display_chat.assert_any_call("Our burgers are popular", "assistant", mock_container)
    
    @patch('frontend.streamlit_app.st')
    @patch('frontend.streamlit_app.OrchestratorService')
    @patch('frontend.streamlit_app.SessionManager.update_history')
    def test_process_user_input(self, mock_update_history, mock_orchestrator_class, mock_st, mock_config):
        """Test that user input is processed correctly."""
        # Setup mock session state
        mock_st.session_state = {
            "history": [],
            "context": {
                "user_preferences": {},
                "recent_queries": [],
                "active_conversation": True
            },
            "ui_state": {
                "show_sql": False,
                "show_results": False,
                "current_view": "chat"
            },
            "user_input": "Show me menu items under $10"
        }
        
        # Setup mock orchestrator service
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Setup mock response from orchestrator
        mock_response = {
            "category": "data_query",
            "response": "Here are menu items under $10",
            "metadata": {
                "sql_query": "SELECT * FROM menu WHERE price < 10",
                "results": [{"name": "Burger", "price": 8.99}]
            }
        }
        mock_orchestrator.process_query.return_value = mock_response
        
        # Mock update_history to update the session state directly
        def side_effect_update_history(query, result):
            mock_st.session_state["history"].append({
                "query": query,
                "response": result.get("response", ""),
                "category": result.get("category", "general"),
                "timestamp": datetime.now(),
            })
        mock_update_history.side_effect = side_effect_update_history
        
        # Create a mock container
        mock_container = MagicMock()
        mock_st.container.return_value = mock_container
        
        # Mock the DataFrame display
        mock_dataframe = MagicMock()
        mock_st.dataframe = mock_dataframe
        
        # Initialize the orchestrator
        initialize_ui(mock_config)
        
        # Process the user input with direct context
        context = mock_st.session_state["context"]
        process_user_input(mock_container, context)
        
        # Verify orchestrator was called with the user input and context
        mock_orchestrator.process_query.assert_called_once_with(
            "Show me menu items under $10",
            context
        )
        
        # Verify update_history was called
        mock_update_history.assert_called_once_with(
            "Show me menu items under $10",
            mock_response
        )
        
        # Verify chat history was updated
        assert len(mock_st.session_state["history"]) == 1
        assert mock_st.session_state["history"][0]["query"] == "Show me menu items under $10"
        assert mock_st.session_state["history"][0]["response"] == "Here are menu items under $10"
    
    @patch('frontend.streamlit_app.st')
    @patch('frontend.streamlit_app.display_chat_message')
    @patch('frontend.streamlit_app.OrchestratorService')
    def test_data_visualization(self, mock_orchestrator_class, mock_display_chat, mock_st, mock_config):
        """Test that data query results are visualized correctly."""
        # Setup mock session state
        mock_st.session_state = {
            "history": [],
            "context": {
                "user_preferences": {},
                "recent_queries": [],
                "active_conversation": True
            },
            "ui_state": {
                "show_sql": True,
                "show_results": True,
                "current_view": "chat"
            },
            "user_input": "Show me sales data"
        }
        
        # Setup mock orchestrator service
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Sample data for visualization
        sample_data = [
            {"item": "Burger", "sales": 120, "revenue": 1199.88},
            {"item": "Pizza", "sales": 85, "revenue": 1189.15},
            {"item": "Salad", "sales": 45, "revenue": 449.55}
        ]
        
        # Setup mock response from orchestrator
        mock_response = {
            "category": "data_query",
            "response": "Here's the sales data",
            "metadata": {
                "sql_query": "SELECT item, SUM(quantity) as sales, SUM(price*quantity) as revenue FROM orders GROUP BY item",
                "results": sample_data
            }
        }
        mock_orchestrator.process_query.return_value = mock_response
        
        # Mock dataframe and visualization components
        mock_st.dataframe = MagicMock()
        mock_st.bar_chart = MagicMock()
        mock_st.code = MagicMock()
        
        # Create a mock container
        mock_container = MagicMock()
        mock_st.container.return_value = mock_container
        
        # Initialize the UI
        initialize_ui(mock_config)
        
        # Process the user input
        process_user_input(mock_container)
        
        # Verify SQL code was displayed
        mock_st.code.assert_called_with(
            "SELECT item, SUM(quantity) as sales, SUM(price*quantity) as revenue FROM orders GROUP BY item", 
            language="sql"
        )
        
        # Verify dataframe was displayed with correct data
        # Convert the expected dataframe to the same format as would be created in the app
        expected_df = pd.DataFrame(sample_data)
        
        # The assertion below can't directly compare dataframes since we're mocking,
        # but we can verify that dataframe was called
        mock_st.dataframe.assert_called_once()
        
        # Verify bar chart was called (assuming it would be called with the dataframe)
        mock_st.bar_chart.assert_called_once()
    
    @patch('frontend.streamlit_app.st')
    @patch('frontend.streamlit_app.display_chat_message')
    @patch('frontend.streamlit_app.OrchestratorService')
    @patch('frontend.streamlit_app.SessionManager.update_history')
    def test_error_handling_in_ui(self, mock_update_history, mock_orchestrator_class, mock_display_chat, mock_st, mock_config):
        """Test that UI handles errors from the backend gracefully."""
        # Setup mock session state
        mock_st.session_state = {
            "history": [],
            "context": {
                "user_preferences": {},
                "recent_queries": [],
                "active_conversation": True
            },
            "ui_state": {
                "show_sql": True,
                "show_results": True,
                "current_view": "chat"
            },
            "user_input": "Show me bad query"
        }
        
        # Setup mock orchestrator service
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Setup mock error response from orchestrator
        mock_response = {
            "category": "error",
            "response": "Sorry, there was an error processing your query.",
            "error": "SQL generation failed",
            "metadata": {}
        }
        mock_orchestrator.process_query.return_value = mock_response
        
        # Mock update_history to update the session state directly
        def side_effect_update_history(query, result):
            mock_st.session_state["history"].append({
                "query": query,
                "response": result.get("response", ""),
                "category": result.get("category", "general"),
                "timestamp": datetime.now(),
            })
        mock_update_history.side_effect = side_effect_update_history
        
        # Create a mock container
        mock_container = MagicMock()
        mock_st.container.return_value = mock_container
        
        # Mock error display
        mock_st.error = MagicMock()
        
        # Initialize the UI
        initialize_ui(mock_config)
        
        # Process the user input
        process_user_input(mock_container)
        
        # Verify error was displayed
        mock_st.error.assert_called_with("SQL generation failed")
        
        # Verify chat history was updated with the error
        assert len(mock_st.session_state["history"]) == 1
        assert mock_st.session_state["history"][0]["query"] == "Show me bad query"
        assert mock_st.session_state["history"][0]["response"] == "Sorry, there was an error processing your query."
        assert mock_st.session_state["history"][0]["category"] == "error" 