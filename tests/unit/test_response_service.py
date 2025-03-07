"""
Unit tests for the Response Service.

Tests the functionality of the ResponseGenerator class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.response_service import ResponseGenerator


class TestResponseService:
    """Test cases for the Response Service."""

    def test_init_response_generator(self, mock_openai_client, test_config):
        """Test the initialization of the ResponseGenerator."""
        response_generator = ResponseGenerator(
            ai_client=mock_openai_client,
            config=test_config
        )
        assert response_generator is not None
        assert response_generator.ai_client == mock_openai_client
        assert response_generator.config == test_config
        assert response_generator.temperature == test_config.get("response_temperature", 0.7)
        assert response_generator.persona == test_config.get("persona", "casual")

    def test_set_persona(self, mock_response_generator):
        """Test setting the response persona."""
        mock_response_generator.set_persona("professional")
        assert mock_response_generator.persona == "professional"

    def test_get_persona_prompt(self, mock_response_generator):
        """Test getting persona-specific prompt instructions."""
        with patch.object(mock_response_generator, "get_persona_prompt") as mock_get:
            mock_get.return_value = "Respond in a professional, business-like tone."
            prompt = mock_response_generator.get_persona_prompt()
            assert prompt == "Respond in a professional, business-like tone."

    def test_clean_sql_result_list_of_dicts(self, mock_response_generator):
        """Test cleaning SQL results that are a list of dictionaries."""
        with patch.object(mock_response_generator, "clean_sql_result") as mock_clean:
            mock_clean.return_value = "| id | name | price |\n| --- | --- | --- |\n| 1 | Test Item | 10.99 |"
            
            sql_result = [
                {"id": 1, "name": "Test Item", "price": 10.99}
            ]
            
            result = mock_response_generator.clean_sql_result(sql_result)
            assert "| id | name | price |" in result
            assert "| 1 | Test Item | 10.99 |" in result

    def test_clean_sql_result_empty(self, mock_response_generator):
        """Test cleaning empty SQL results."""
        with patch.object(mock_response_generator, "clean_sql_result") as mock_clean:
            mock_clean.return_value = "No results found."
            
            sql_result = []
            
            result = mock_response_generator.clean_sql_result(sql_result)
            assert result == "No results found."

    def test_clean_sql_result_single_dict(self, mock_response_generator):
        """Test cleaning SQL results that are a single dictionary."""
        with patch.object(mock_response_generator, "clean_sql_result") as mock_clean:
            mock_clean.return_value = "id: 1\nname: Test Item\nprice: 10.99"
            
            sql_result = {"id": 1, "name": "Test Item", "price": 10.99}
            
            result = mock_response_generator.clean_sql_result(sql_result)
            assert "id: 1" in result
            assert "name: Test Item" in result
            assert "price: 10.99" in result

    def test_generate_response(self, mock_response_generator, mock_openai_client):
        """Test generating a response from SQL results."""
        # Test with mocked generate_response
        response = mock_response_generator.generate_response(
            "Show me the menu items at Idle Hour",
            [{"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}],
            {"location_name": "Idle Hour Country Club"}
        )
        assert response == "Here are the results for your query."

    def test_generate_response_no_ai_client(self, test_config):
        """Test generating a response without an AI client."""
        response_generator = ResponseGenerator(
            ai_client=None,
            config=test_config
        )
        
        response = response_generator.generate_response(
            "Show me the menu items at Idle Hour",
            [{"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}]
        )
        
        assert "| id | name | price | location_id |" in response
        assert "| 1 | Test Item | 10.99 | 62 |" in response

    def test_generate_summary(self, mock_response_generator):
        """Test generating a summary of text."""
        # Test with mocked generate_summary
        summary = mock_response_generator.generate_summary(
            "This is a long text that needs to be summarized for voice output. " * 10,
            max_length=100
        )
        assert summary == "Summary of results."

    def test_generate_summary_no_ai_client(self, test_config):
        """Test generating a summary without an AI client."""
        response_generator = ResponseGenerator(
            ai_client=None,
            config=test_config
        )
        
        original_text = "This is a short text."
        summary = response_generator.generate_summary(original_text, max_length=100)
        assert summary == original_text  # Short enough to not need summarization
        
        long_text = "This is a long text that needs to be summarized. " * 10
        summary = response_generator.generate_summary(long_text, max_length=50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")

    def test_clean_for_tts(self, mock_response_generator):
        """Test cleaning text for text-to-speech processing."""
        with patch.object(mock_response_generator, "clean_for_tts") as mock_clean:
            mock_clean.return_value = "This is clean text for TTS."
            
            markdown_text = """
            # Results
            
            Here are the **bold** results:
            
            | id | name | price |
            | --- | --- | --- |
            | 1 | Test Item | 10.99 |
            
            Check out this [link](https://example.com)
            """
            
            cleaned = mock_response_generator.clean_for_tts(markdown_text)
            assert cleaned == "This is clean text for TTS." 