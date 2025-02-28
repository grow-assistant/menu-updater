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
    integrate_with_existing_flow,
)
from langchain.agents import Tool


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

    @patch("integrate_app.get_clients")
    @patch("integrate_app.create_categorization_prompt")
    def test_integrate_with_existing_flow(
        self, mock_create_categorization_prompt, mock_get_clients
    ):
        """Test that integrate_with_existing_flow correctly processes a menu update query"""
        # Create mock clients
        mock_openai_client = MagicMock()
        mock_other_client = MagicMock()
        mock_get_clients.return_value = (mock_openai_client, mock_other_client)

        # Setup categorization prompt mock
        mock_create_categorization_prompt.return_value = {"prompt": "test prompt"}

        # Setup mock response from OpenAI
        mock_response = MagicMock()
        mock_choices = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"request_type": "menu_update", "time_period": "today", "item_name": "burger", "new_price": 10.99}'
        mock_choices.choices = [MagicMock(message=mock_message)]

        # For new OpenAI client structure (>= 1.0.0)
        mock_openai_client.chat.completions.create.return_value = mock_choices

        # Create a valid Tool for testing
        test_tool = Tool(
            name="test_tool", func=lambda x: "test result", description="A test tool"
        )

        # Use a mock callback handler to capture function progress
        mock_callback = MagicMock()

        # Execute the function - we'll just verify it runs without exceptions
        try:
            result = integrate_with_existing_flow(
                "Update the price of the burger to $10.99",
                [test_tool],
                callback_handler=mock_callback,
                context={
                    "date_filter": {
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31",
                    }
                },
            )

            # Verify the flow was initiated
            self.assertIsNotNone(result)

            # Verify that our mocks were called appropriately
            mock_get_clients.assert_called_once()
            mock_create_categorization_prompt.assert_called_once()

            # We expect the mock_callback to be called with status updates
            mock_callback.on_text.assert_called()

        except Exception as e:
            self.fail(f"integrate_with_existing_flow raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
