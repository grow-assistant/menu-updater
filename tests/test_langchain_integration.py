import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import streamlit as st
import re
import pytest
import json

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.langchain_integration import (
    create_langchain_agent,
    create_sql_database_tool,
    create_menu_update_tool,
    StreamlitCallbackHandler,
)
from main_integration import (
    integrate_with_existing_flow,
    categorize_query,
)
from langchain.agents import Tool

# Check if the new services are available
try:
    from app.services.prompt_service import prompt_service, PromptService
    from app.services.query_service import query_service, QueryService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False


class TestLangchainIntegration(unittest.TestCase):

    @patch("utils.langchain_integration.os.getenv")
    @patch("utils.langchain_integration.ChatOpenAI")
    @patch("utils.langchain_integration.initialize_agent")
    def test_create_langchain_agent(
        self, mock_init_agent, mock_chat_openai, mock_getenv
    ):
        """
        Test that create_langchain_agent creates and configures an agent properly
        """
        # Set up mocks
        mock_getenv.return_value = "fake-api-key"
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_agent = MagicMock()
        mock_init_agent.return_value = mock_agent

        # Create test tools
        test_tools = [MagicMock()]

        # Call the function
        agent = create_langchain_agent(
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            streaming=True,
            tools=test_tools,
            verbose=True,
        )

        # Check that the agent was created properly
        mock_chat_openai.assert_called_once()
        mock_init_agent.assert_called_once()
        self.assertEqual(agent, mock_agent)

    def test_create_sql_database_tool(self):
        """
        Test that create_sql_database_tool creates a tool with the correct name and function
        """
        # Create a mock execute query function
        mock_execute_query = MagicMock()
        mock_execute_query.return_value = {
            "success": True,
            "results": [{"item": "Burger", "price": 9.99}],
        }

        # Create the tool
        tool = create_sql_database_tool(mock_execute_query)

        # Check that the tool has the correct properties
        self.assertEqual(tool.name, "sql_database")
        self.assertTrue(callable(tool.func))

        # Test the tool function
        result = tool.func("SELECT * FROM menu_items")

        # Check that it called our mock function and formatted the results
        mock_execute_query.assert_called_once_with("SELECT * FROM menu_items")
        self.assertIn("Burger", result)
        self.assertIn("9.99", result)

    def test_menu_update_tool(self):
        """
        Test that create_menu_update_tool creates a tool with the correct name and function
        """
        # Create a mock execute update function
        mock_execute_update = MagicMock()
        mock_execute_update.return_value = {"success": True, "affected_rows": 2}

        # Create the tool
        tool = create_menu_update_tool(mock_execute_update)

        # Check that the tool has the correct properties
        self.assertEqual(tool.name, "update_menu")
        self.assertTrue(callable(tool.func))

        # Test the tool function with a valid JSON update spec
        update_spec = '{"item_id": 1, "price": 12.99}'
        result = tool.func(update_spec)

        # Check that it called our mock function and formatted the results
        mock_execute_update.assert_called_once()
        self.assertIn("Update successful", result)
        self.assertIn("2", result)

    @patch("main_integration.categorize_query")
    @patch("main_integration.SERVICES_AVAILABLE", True)
    @patch("main_integration.query_service")
    @patch("main_integration.get_query_path")
    def test_integrate_with_existing_flow(self, mock_get_query_path, mock_query_service, mock_categorize_query):
        """Test that integrate_with_existing_flow correctly processes a menu update query"""
        # Set up the mock categorization function to return our test data when called
        mock_categorize_query.return_value = {
            "request_type": "update_price", 
            "time_period": "today", 
            "item_name": "burger", 
            "new_price": 10.99
        }
        
        # Set up mock for query_service.process_query_with_path
        mock_query_service.process_query_with_path.return_value = {
            "success": True,
            "verbal_answer": "Price updated successfully",
            "text_answer": "The price of burger has been updated to $10.99",
            "sql_query": "UPDATE items SET price = 10.99 WHERE name ILIKE '%burger%'"
        }
        
        # Use a mock callback handler to capture function progress
        mock_callback = MagicMock()

        # Execute the function
        result = integrate_with_existing_flow(
            "Update the price of the burger to $10.99",
            callback_handler=mock_callback,
        )

        # Verify the flow was initiated
        self.assertIsNotNone(result)

        # Verify that our mocks were called appropriately
        mock_categorize_query.assert_called_once()
        mock_query_service.process_query_with_path.assert_called_once()
        
        # Assert the function returned a success result
        self.assertTrue(result.get("success", False))
        
        # Assert the callback was called with our verbal answer
        mock_callback.on_text.assert_called_once_with("Price updated successfully")


# Only run these tests if the services are available
@pytest.mark.skipif(not SERVICES_AVAILABLE, reason="New services not available")
class TestServiceModules(unittest.TestCase):
    """Tests for the new service modules"""
    
    def test_prompt_service_initialization(self):
        """Test that the prompt service initializes correctly"""
        # Create a new instance for testing
        test_prompt_service = PromptService()
        
        # Verify it has the expected methods
        self.assertTrue(hasattr(test_prompt_service, "create_gemini_prompt"))
        self.assertTrue(hasattr(test_prompt_service, "create_categorization_prompt"))
        self.assertTrue(hasattr(test_prompt_service, "create_query_categorization_prompt"))
    
    @patch("prompts.google_gemini_prompt.create_gemini_prompt")
    def test_create_gemini_prompt(self, mock_create_gemini_prompt):
        """Test that the prompt service creates Gemini prompts correctly"""
        # Setup the mock
        mock_create_gemini_prompt.return_value = "Test prompt content"
        
        # Create a test instance and manually set the mock
        test_prompt_service = PromptService()
        test_prompt_service._create_gemini_prompt = mock_create_gemini_prompt
            
        # Call the method
        result = test_prompt_service.create_gemini_prompt(
            user_query="How many orders yesterday?",
            context_files={"test": "data"},
            location_id=42
        )
            
        # Verify the mock was called with correct parameters
        mock_create_gemini_prompt.assert_called_once()
            
        # Verify the result
        self.assertEqual(result, "Test prompt content")
    
    def test_query_categorization(self):
        """Test that the query service categorizes queries correctly"""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Set up the mock response structure
        mock_message.content = '{"request_type": "order_history", "time_period": "yesterday"}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call the method with our mock
        result = query_service.categorize_query(
            "How many orders did we have yesterday?",
            openai_client=mock_client
        )
        
        # Verify the result - we don't need to check the exact call parameters here
        self.assertEqual(result["request_type"], "order_history")
        self.assertEqual(result["time_period"], "yesterday")


if __name__ == "__main__":
    unittest.main()
