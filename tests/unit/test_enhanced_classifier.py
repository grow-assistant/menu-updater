"""
Unit tests for the Classification Service.

Tests the functionality of the ClassificationService class which classifies user queries.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
import openai
import asyncio
from typing import Dict, Any

from services.classification.classifier import ClassificationService
from services.classification.prompt_builder import ClassificationPromptBuilder


@pytest.fixture
def mock_config():
    """
    Provide test configuration values for the classifier.
    
    Returns:
        Dict[str, Any]: Configuration dictionary with API keys and service settings
    """
    return {
        "api": {
            "openai": {
                "api_key": "test-api-key",
                "model": "gpt-4o-mini"
            }
        },
        "services": {
            "classification": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "cache_size": 100,
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 50
            }
        }
    }


@pytest.fixture
def mock_prompt_builder():
    """
    Provide a mocked ClassificationPromptBuilder.
    
    Returns:
        MagicMock: Mock object that simulates the ClassificationPromptBuilder
    """
    mock_builder = MagicMock(spec=ClassificationPromptBuilder)
    
    # Set up mock methods
    mock_builder.get_available_query_types.return_value = [
        "order_history", "trend_analysis", "popular_items", 
        "order_ratings", "menu_inquiry", "general_question"
    ]
    
    mock_builder.build_classification_prompt.return_value = {
        "system": "Test system prompt",
        "user": "Test user prompt"
    }
    
    mock_builder.is_valid_query_type.return_value = True
    
    return mock_builder


@pytest.fixture
def mock_openai_responses():
    """
    Provide mock OpenAI API responses for testing.
    
    Returns:
        Dict: Dictionary with different mock response scenarios
    """
    class MockChoice:
        def __init__(self, content):
            self.message = MagicMock()
            self.message.content = content
    
    class MockCompletion:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
    
    # Different response types
    responses = {
        "menu_inquiry": MockCompletion("menu_inquiry"),
        "order_history": MockCompletion("order_history"),
        "general_question": MockCompletion("general_question"),
        "invalid_response": MockCompletion("not_a_valid_category"),
        "error_response": Exception("API Error")
    }
    
    return responses


@pytest.fixture
def classifier(mock_config, mock_prompt_builder, mock_openai_responses):
    """
    Provide a ClassificationService with mocked dependencies.
    
    Args:
        mock_config: Test configuration dictionary
        mock_prompt_builder: Mocked prompt builder
        mock_openai_responses: Mocked OpenAI responses
        
    Returns:
        ClassificationService: Configured for testing with mocked dependencies
    """
    # Patch the prompt_builder import in the classifier module
    with patch("services.classification.classifier.classification_prompt_builder", mock_prompt_builder):
        # Create the service
        classifier = ClassificationService(config=mock_config)
        
        # Configure service with test values
        classifier.prompt_builder = mock_prompt_builder
        classifier.categories = mock_prompt_builder.get_available_query_types.return_value
        
        return classifier


@pytest.mark.unit
class TestEnhancedClassifier:
    """Test cases for the enhanced Classification Service."""

    def test_initialization(self, classifier, mock_config):
        """
        Test that the classifier initializes correctly with all expected attributes.
        
        This test verifies:
        1. The classifier is properly instantiated
        2. API key and model values are correctly set from config
        3. All required attributes are initialized
        """
        assert classifier is not None
        assert classifier.api_key == mock_config["api"]["openai"]["api_key"]
        assert classifier.model == mock_config["api"]["openai"]["model"]
        assert isinstance(classifier.prompt_builder, MagicMock)
        assert len(classifier.categories) > 0
        assert isinstance(classifier._classification_cache, dict)

    def test_normalize_query(self, classifier):
        """
        Test query normalization for caching purposes.
        
        This test verifies that the normalization:
        1. Removes leading and trailing whitespace
        2. Converts text to lowercase
        3. Handles mixed-case input correctly
        """
        # Test with spaces and uppercase
        assert classifier._normalize_query("  HELLO world  ") == "hello world"
        
        # Test with leading/trailing whitespace
        assert classifier._normalize_query("  test query  ") == "test query"
        
        # Test with mixed case
        assert classifier._normalize_query("Show Me The Menu") == "show me the menu"

    def test_classification_caching(self, classifier):
        """
        Test the classification caching mechanism.
        
        This test verifies:
        1. Cache is empty initially
        2. Cache correctly stores and retrieves results
        3. Cache respects the use_cache flag
        4. Results retrieved from cache have from_cache=True
        """
        # Clear the cache to start fresh
        classifier._classification_cache = {}
        
        # Create a test query and result
        test_query = "What's on the menu?"
        normalized_query = classifier._normalize_query(test_query)
        test_result = {
            "query": test_query,
            "query_type": "menu_inquiry", 
            "confidence": 0.9,
            "time_elapsed": 0.5,
            "from_cache": False
        }
        
        # Directly test cache retrieval when cache is empty
        cached_result = classifier._check_query_cache(test_query, True)
        assert cached_result is None
        
        # Add the result to the cache
        classifier._classification_cache[normalized_query] = test_result
        
        # Verify we can retrieve from cache
        cached_result = classifier._check_query_cache(test_query, True)
        assert cached_result is not None
        assert cached_result["query_type"] == "menu_inquiry"
        assert cached_result["from_cache"] is False
        
        # Test with use_cache=False (should ignore cache)
        cached_result = classifier._check_query_cache(test_query, False)
        assert cached_result is None
        
        # Test the full classify_query method with caching
        with patch.object(classifier, '_check_query_cache', wraps=classifier._check_query_cache) as mock_check_cache:
            # Mock the API call to avoid actual calls
            with patch('openai.chat.completions.create'):
                # First call should check cache and find our entry
                result = classifier.classify_query(test_query)
                mock_check_cache.assert_called_once()
                assert result["from_cache"] is True  # classify_query sets this
                assert result["query_type"] == "menu_inquiry"

    @pytest.mark.fast
    def test_keyword_classification(self, classifier):
        """
        Test classification using keyword matching.
        
        This test verifies:
        1. Correct classification based on keywords in query
        2. Appropriate confidence levels for matches
        3. Default categorization for non-matching queries
        
        Edge cases:
        - Query with multiple category keywords
        - Query with no recognized keywords
        """
        # Test with menu-related keywords
        menu_result = classifier._classify_by_keywords("Show me the current menu items")
        assert menu_result["query_type"] == "menu_inquiry"
        assert menu_result["confidence"] > 0.7
        
        # Test with trend-related keywords
        trend_result = classifier._classify_by_keywords("Show me sales trends over time")
        assert trend_result["query_type"] == "trend_analysis"
        assert trend_result["confidence"] > 0.7
        
        # Test with order history keywords
        history_result = classifier._classify_by_keywords("Let me see my past orders")
        assert history_result["query_type"] == "order_history"
        assert history_result["confidence"] > 0.7
        
        # Test with no matching keywords (should default to general)
        general_result = classifier._classify_by_keywords("Tell me about your business hours")
        assert general_result["query_type"] == "general_question"
        assert general_result["confidence"] < 0.7

    @pytest.mark.fast
    def test_fallback_classification(self, classifier):
        """
        Test the fallback classification used when errors occur.
        
        This test verifies:
        1. Fallback returns a valid classification result
        2. Result has appropriate confidence level (low)
        3. Result includes error information
        4. Result uses general_question as the default type
        """
        result = classifier._fallback_classification("Any query text")
        assert result["query_type"] == "general_question"
        assert result["confidence"] == 0.3
        assert result["classification_method"] == "fallback"
        assert "error" in result

    @pytest.mark.api
    def test_classify_query_with_ai(self, classifier, mock_openai_responses):
        """
        Test classification using the AI model.
        
        This test verifies:
        1. OpenAI API is called with correct parameters
        2. Response is properly parsed and returned
        3. Metadata is correctly added to the result
        4. Result follows the expected format
        """
        test_query = "What items are on the menu?"
        
        # Mock OpenAI API call to return a specific classification
        with patch("openai.chat.completions.create", return_value=mock_openai_responses["menu_inquiry"]):
            result = classifier.classify_query(test_query)
            
            assert result["query_type"] == "menu_inquiry"
            assert result["confidence"] >= 0.7
            assert result["classification_method"] == "ai"
            assert result["query"] == test_query
            assert "time_elapsed" in result
            assert result["from_cache"] is False

    @pytest.mark.api
    def test_classify_query_with_ai_error(self, classifier, mock_openai_responses):
        """
        Test classification when AI model raises an error.
        
        This test verifies:
        1. Errors from the API are properly caught
        2. Fallback classification is used on error
        3. Error information is included in the result
        """
        test_query = "What items are on the menu?"
        
        # Mock OpenAI API call to raise an exception
        with patch("openai.chat.completions.create", side_effect=mock_openai_responses["error_response"]):
            # Should use fallback classification
            result = classifier.classify_query(test_query)
            
            assert result["query_type"] == "general_question"  # Fallback type
            assert result["confidence"] == 0.3  # Low confidence
            assert result["classification_method"] == "fallback"
            assert "error" in result

    def test_parse_classification_response(self, classifier):
        """
        Test parsing of classification response from API.
        
        This test verifies:
        1. Valid categories are recognized and returned with high confidence
        2. Partial matches are recognized with lower confidence
        3. Invalid responses default to general_question
        
        Edge cases:
        - Response contains category name embedded in text
        - Response contains completely invalid category
        """
        # Test with valid category
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "menu_inquiry"
        
        result = classifier.parse_classification_response(mock_response, "test query")
        assert result["query_type"] == "menu_inquiry"
        assert result["confidence"] == 0.9
        
        # Test with partial match
        mock_response.choices[0].message.content = "This looks like an order_history request"
        result = classifier.parse_classification_response(mock_response, "test query")
        assert result["query_type"] == "order_history"
        assert result["confidence"] == 0.7
        
        # Test with invalid category (should default to general)
        mock_response.choices[0].message.content = "something_completely_invalid"
        result = classifier.parse_classification_response(mock_response, "test query")
        assert result["query_type"] == "general_question"
        assert result["confidence"] == 0.5

    def test_classify_method_compatibility(self, classifier):
        """
        Test the classify method which provides compatibility with the orchestrator.
        
        This test verifies:
        1. classify() method correctly calls classify_query()
        2. Result is transformed into the format expected by orchestrator
        3. All required fields are present in the result
        """
        # Mock the classify_query method
        with patch.object(classifier, "classify_query", return_value={
            "query_type": "menu_inquiry",
            "confidence": 0.9,
            "skip_database": False
        }):
            result = classifier.classify("Show me the menu")
            
            assert "category" in result
            assert result["category"] == "menu_inquiry"
            assert "confidence" in result
            assert "skip_database" in result

    @pytest.mark.api
    def test_health_check(self, classifier):
        """
        Test the health check functionality.
        
        This test verifies:
        1. Health check succeeds with valid API key
        2. Health check fails with missing API key
        3. Health check fails when API raises an error
        """
        # Test with valid API key
        with patch("openai.models.list") as mock_list:
            mock_list.return_value = ["gpt-4", "gpt-3.5-turbo"]
            assert classifier.health_check() is True
        
        # Test with no API key
        classifier.api_key = None
        assert classifier.health_check() is False
        
        # Test with API error
        classifier.api_key = "test-api-key"
        with patch("openai.models.list", side_effect=Exception("API Error")):
            assert classifier.health_check() is False

    @pytest.mark.fast
    def test_clear_cache(self, classifier):
        """
        Test clearing the classification cache.
        
        This test verifies:
        1. Cache can be populated with items
        2. clear_cache() removes all items
        3. Empty cache after clearing
        """
        # Add items to the cache
        classifier._classification_cache = {
            "query1": {"result": "data1"},
            "query2": {"result": "data2"}
        }
        
        # Verify cache has items
        assert len(classifier._classification_cache) == 2
        
        # Clear the cache
        classifier.clear_cache()
        
        # Verify cache is empty
        assert len(classifier._classification_cache) == 0

    @pytest.mark.asyncio
    async def test_classify_query_async(self, classifier):
        """
        Test the asynchronous classification method.
        
        This test verifies:
        1. Async method correctly calls the synchronous version
        2. Result matches the synchronous version's output
        3. Async execution completes successfully
        """
        # Mock the synchronous version to return a test result
        test_result = {
            "query_type": "menu_inquiry",
            "confidence": 0.9,
            "classification_method": "async_test"
        }
        
        with patch.object(classifier, "classify_query", return_value=test_result):
            # Call the async method
            result = await classifier.classify_query_async("What's on the menu?")
            
            # Verify it returns the same result as the sync method
            assert result == test_result 