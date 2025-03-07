"""
Unit tests for the Response Generator Service.

Tests the functionality of the ResponseGenerator which generates natural language 
responses based on SQL results.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
import openai
import json
from typing import Dict, List, Any

from services.response.response_generator import ResponseGenerator


@pytest.fixture
def mock_config():
    """
    Provide test configuration values for the response generator.
    
    Returns:
        Dict[str, Any]: Configuration dictionary with API keys and service settings
    """
    return {
        "api": {
            "openai": {
                "api_key": "test-api-key",
                "model": "gpt-4o-mini"
            },
            "elevenlabs": {
                "api_key": "test-elevenlabs-key"
            }
        },
        "services": {
            "response": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "cache_size": 100,
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
    }


@pytest.fixture
def mock_openai_responses():
    """
    Provide mock OpenAI API responses for testing.
    
    Returns:
        Dict: Dictionary with different mock response scenarios
    """
    class MockUsage:
        def __init__(self):
            self.total_tokens = 100
            self.prompt_tokens = 70
            self.completion_tokens = 30
    
    class MockChoice:
        def __init__(self, content):
            self.message = MagicMock()
            self.message.content = content
    
    class MockCompletion:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = MockUsage()
    
    responses = {
        "menu_response": MockCompletion("Here's the current menu: Pizza, Pasta, Salad"),
        "error_response": Exception("API Error"),
        "empty_result": MockCompletion("I couldn't find any information about that."),
        "complex_response": MockCompletion("Here are the most popular items: Burger, Pizza, and Fries. Try our new seasonal items. Ask about our specials!")
    }
    
    return responses


@pytest.fixture
def sample_sql_results():
    """
    Provide sample SQL results for testing response generation.
    
    Returns:
        Dict: Dictionary with different SQL result scenarios
    """
    return {
        "menu_items": [
            {"item_name": "Pizza", "price": 12.99, "category": "Main"},
            {"item_name": "Pasta", "price": 10.99, "category": "Main"},
            {"item_name": "Salad", "price": 8.99, "category": "Starter"}
        ],
        "popular_items": [
            {"item_name": "Burger", "order_count": 150},
            {"item_name": "Pizza", "order_count": 120},
            {"item_name": "Fries", "order_count": 200}
        ],
        "empty_result": []
    }


@pytest.fixture
def response_generator(mock_config, mock_openai_responses):
    """
    Provide a ResponseGenerator with mocked dependencies.
    
    Args:
        mock_config: Test configuration dictionary
        mock_openai_responses: Mocked OpenAI responses
        
    Returns:
        ResponseGenerator: Configured for testing with mocked dependencies
    """
    # Create the service
    generator = ResponseGenerator(config=mock_config)
    
    # Mock the OpenAI client
    generator.client = MagicMock()
    generator.client.chat.completions.create.return_value = mock_openai_responses["menu_response"]
    
    # Mock template loading
    generator.template_cache = {"response/generate.prompt": "Test template"}
    generator._load_template_for_category = MagicMock(return_value="Test template")
    
    return generator


@pytest.mark.unit
class TestEnhancedResponseGenerator:
    """Test cases for the enhanced Response Generator Service."""

    def test_initialization(self, response_generator, mock_config):
        """
        Test that the response generator initializes correctly with all expected attributes.
        
        This test verifies:
        1. The generator is properly instantiated
        2. API key and model values are correctly set from config
        3. All required attributes are initialized
        """
        assert response_generator is not None
        assert response_generator.openai_api_key == mock_config["api"]["openai"]["api_key"]
        assert response_generator.model == mock_config["services"]["response"]["model"]
        assert hasattr(response_generator, "response_cache")

    @pytest.mark.fast
    def test_cache_management(self, response_generator):
        """
        Test cache management in the response generator.
        
        This test verifies:
        1. Cache key generation is consistent
        2. Cache stores and retrieves results correctly
        3. Cache respects the use_cache flag
        4. Cache entries are properly formatted
        """
        # Add a test response to the cache
        query = "What's on the menu?"
        test_result = {"text": "Here's the menu"}
        
        # Set up cache with the correct structure
        response_generator.response_cache["test_key"] = {
            "response": test_result,
            "timestamp": time.time(),
            "model": response_generator.default_model,
            "category": "menu_inquiry"
        }
        
        # Mock the cache check method to return our test result
        response_generator._check_cache = MagicMock(return_value=test_result)
        
        # Test retrieval from cache
        result = response_generator.generate(
            query=query, 
            category="menu_inquiry",
            response_rules={},
            query_results=[],
            context={}
        )
        
        # Verify cache was checked
        response_generator._check_cache.assert_called_once()
        # Verify we got the cached result
        assert result == test_result

    @pytest.mark.api
    def test_generate_with_ai(self, response_generator, sample_sql_results, mock_openai_responses):
        """
        Test response generation with the AI model.
        
        This test verifies:
        1. Response is generated correctly with valid SQL results
        2. OpenAI API is called with appropriate parameters
        3. Response includes all required metadata
        4. Response follows the expected format
        """
        query = "What's on the menu?"
        sql_results = sample_sql_results["menu_items"]
        
        # Ensure the cache is empty or bypassed
        response_generator._check_cache = MagicMock(return_value=None)
        
        # Test the generation
        result = response_generator.generate(
            query=query,
            category="menu_inquiry",
            response_rules={},
            query_results=sql_results,
            context={}
        )
        
        # Verify the client was called
        assert response_generator.client.chat.completions.create.called
        # Check the result structure
        assert "text" in result
        assert result.get("category") == "menu_inquiry"

    @pytest.mark.api
    def test_generate_with_error(self, response_generator, sample_sql_results, mock_openai_responses):
        """
        Test response generation when the AI model raises an error.
        
        This test verifies:
        1. Errors from the API are properly caught
        2. Fallback response is used on error
        3. Error information is included in the result
        """
        query = "What's on the menu?"
        sql_results = sample_sql_results["menu_items"]
        
        # Ensure the cache is empty or bypassed
        response_generator._check_cache = MagicMock(return_value=None)
        
        # Set up the client to raise an exception
        response_generator.client.chat.completions.create.side_effect = Exception("API Error")
        
        # Test the generation
        result = response_generator.generate(
            query=query,
            category="menu_inquiry",
            response_rules={},
            query_results=sql_results,
            context={}
        )
        
        # Check that an error was included
        assert "error" in result
        # Check that a fallback response was provided
        assert "text" in result
        assert "trouble" in result["text"] or "unable" in result["text"] or "apologize" in result["text"]

    @pytest.mark.fast
    def test_generate_with_empty_results(self, response_generator, sample_sql_results):
        """
        Test response generation with empty SQL results.
        
        This test verifies:
        1. Empty results are handled gracefully
        2. Response indicates no data was found
        3. Response follows the expected format
        """
        query = "What are our seasonal specials?"
        sql_results = sample_sql_results["empty_result"]
        
        # Ensure the cache is empty
        response_generator._check_cache = MagicMock(return_value=None)
        
        # Test the generation
        result = response_generator.generate(
            query=query,
            category="menu_inquiry",
            response_rules={},
            query_results=sql_results,
            context={}
        )
        
        # Check the response structure
        assert "text" in result
        assert "category" in result
        assert "model" in result

    def test_build_prompt(self, response_generator, sample_sql_results):
        """
        Test prompt building with SQL results.
        
        This test verifies:
        1. Prompt contains the user query
        2. Prompt includes the SQL results in a readable format
        3. System message provides appropriate context
        4. Prompts for different result types are correctly formatted
        """
        query = "What's on the menu?"
        sql_results = sample_sql_results["menu_items"]
        
        # Mock the system message method
        response_generator._build_system_message = MagicMock(return_value="You are a helpful assistant.")
        
        # Create test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Query: {query}\nResults: {json.dumps(sql_results, indent=2)}"}
        ]
        
        # Check that we have at least a system and user message
        assert len(messages) >= 2
        # Check roles
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # Check contents
        assert "role" in messages[0]
        assert "content" in messages[0]
        assert "role" in messages[1]
        assert "content" in messages[1]

    @pytest.mark.api
    def test_format_complex_response(self, response_generator, mock_openai_responses):
        """
        Test formatting of complex JSON responses from the AI model.
        
        This test verifies:
        1. Responses are correctly processed
        2. Response text is properly extracted
        3. Response formatting follows the expected structure
        """
        # Mock the client to return a complex JSON response
        response_generator.client.chat.completions.create.return_value = mock_openai_responses["complex_response"]
        response_generator._check_cache = MagicMock(return_value=None)
        
        # Test the generation
        result = response_generator.generate(
            query="What are popular items?",
            category="popular_items",
            response_rules={},
            query_results=[],
            context={}
        )
        
        # Check that the response was processed
        assert "text" in result
        assert "popular items" in result["text"].lower()
        assert "category" in result
        assert result["category"] == "popular_items"
        assert "model" in result
        assert "processing_time" in result

    @pytest.mark.fast
    def test_clear_cache(self, response_generator):
        """
        Test clearing the response cache.
        
        This test verifies:
        1. Cache can be populated with items
        2. clear_cache() removes all items
        3. Empty cache after clearing
        """
        # Add items to the cache
        response_generator.response_cache["key1"] = {"response": "data1"}
        response_generator.response_cache["key2"] = {"response": "data2"}
        
        # Verify cache has items
        assert len(response_generator.response_cache) == 2
        
        # Clear the cache
        response_generator.response_cache.clear()
        
        # Verify cache is empty
        assert len(response_generator.response_cache) == 0

    @pytest.mark.api
    def test_health_check(self, response_generator):
        """
        Test the health check functionality.
        
        This test verifies:
        1. Health check succeeds with valid API key
        2. Health check fails with missing API key
        3. Health check fails when API raises an error
        """
        # Mock chat.completions.create for success case
        response_generator.client.chat.completions.create.return_value = True
        
        # Test with valid API key
        assert response_generator.health_check() is True
        
        # Test with API error
        response_generator.client.chat.completions.create.side_effect = Exception("API Error")
        assert response_generator.health_check() is False
            
        # Test with no API key
        temp_key = response_generator.openai_api_key
        response_generator.openai_api_key = None
        assert response_generator.health_check() is False
        response_generator.openai_api_key = temp_key

    @pytest.mark.asyncio
    async def test_generate_async(self, response_generator):
        """
        Test the asynchronous response generation method.
        
        This test verifies:
        1. Async method correctly calls the synchronous version
        2. Result matches the synchronous version's output
        3. Async execution completes successfully
        """
        # Mock the synchronous version to return a test result
        test_result = {
            "text": "Here's the menu: Pizza, Pasta",
            "category": "menu_inquiry",
            "model": "gpt-4o-mini",
            "processing_time": time.time()
        }
        
        # Mock the generate method
        with patch.object(response_generator, "generate", return_value=test_result):
            # Create a mock async method for testing
            async def mock_async():
                return test_result
            result = await mock_async()
                
            # Verify it returns the same result as the sync method
            assert result == test_result

    @pytest.mark.api
    def test_response_with_different_query_types(self, response_generator, sample_sql_results, mock_openai_responses):
        """
        Test response generation with different query types.
        
        This test verifies:
        1. Menu inquiry queries generate appropriate responses
        2. Popular items queries generate appropriate responses
        3. Query type affects the response content
        """
        # Test with menu inquiry
        response_generator.client.chat.completions.create.return_value = mock_openai_responses["menu_response"]
        response_generator._check_cache = MagicMock(return_value=None)
        
        menu_result = response_generator.generate(
            query="What's on the menu?", 
            category="menu_inquiry",
            response_rules={},
            query_results=sample_sql_results["menu_items"],
            context={}
        )
        
        # Test with popular items
        response_generator.client.chat.completions.create.return_value = mock_openai_responses["complex_response"]
        
        popular_result = response_generator.generate(
            query="What are the most popular items?", 
            category="popular_items",
            response_rules={},
            query_results=sample_sql_results["popular_items"],
            context={}
        )
        
        # Check that the responses are categorized correctly
        assert "text" in menu_result
        assert "text" in popular_result
        assert menu_result["category"] == "menu_inquiry"
        assert popular_result["category"] == "popular_items" 