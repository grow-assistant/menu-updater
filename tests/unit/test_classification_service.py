"""
Unit tests for the Classification Service.

Tests the functionality of the ClassificationService class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from services.classification.classifier import ClassificationService


class TestClassificationService:
    """Test cases for the Classification Service."""

    def test_init_classification_service(self, test_config):
        """Test the initialization of the ClassificationService."""
        # Add OpenAI API key to test config
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        classification_service = ClassificationService(config=config)
        assert classification_service is not None
        assert classification_service.config == config
        assert classification_service.api_key == "test_api_key"
        assert classification_service.model == "gpt-4o-mini"

    def test_classify(self, test_config):
        """Test the classify method."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create a mock for openai.chat.completions.create
        with patch('services.classification.classifier.openai.chat.completions.create') as mock_create, \
             patch('services.classification.classifier.ClassificationService.classify_query') as mock_classify_query:
            
            # Set up the mock response
            mock_classify_query.return_value = {
                "query_type": "menu_items",
                "confidence": 0.9,
                "time_period_clause": "last_week",
                "is_followup": False,
                "from_cache": False
            }
            
            # Create the classifier and call the classify method
            classifier = ClassificationService(config=config)
            result = classifier.classify("Show me menu items at Idle Hour")
            
            # Verify the result
            assert result["category"] == "menu_items"
            assert result["confidence"] == 0.9
            assert result["time_period_clause"] == "last_week"
            assert result["is_followup"] is False

    def test_classify_with_cache(self, test_config):
        """Test the classify method with caching."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create a mock for classify_query
        with patch('services.classification.classifier.ClassificationService.classify_query') as mock_classify_query:
            # Set up responses
            first_response = {
                "query_type": "menu_items",
                "confidence": 0.9,
                "time_period_clause": "last_week",
                "is_followup": False,
                "from_cache": False,
                "classification_method": "ai"
            }
            second_response = {
                "query_type": "menu_items",
                "confidence": 0.9,
                "time_period_clause": "last_week",
                "is_followup": False,
                "from_cache": True,
                "classification_method": "cached"
            }
            
            # Need to use side_effect to return different values on subsequent calls
            mock_classify_query.side_effect = [first_response, second_response]
            
            # Create the classifier
            classifier = ClassificationService(config=config)
            
            # Call classify twice with the same query
            result1 = classifier.classify("Show me menu items at Idle Hour")
            result2 = classifier.classify("Show me menu items at Idle Hour")
            
            # The classify method returns a transformed dictionary with different keys
            # Verify correct transformation of keys and values
            assert result1["category"] == "menu_items"  # query_type becomes category
            assert result2["category"] == "menu_items"
            
            # Verify that both classify_query calls were made
            assert mock_classify_query.call_count == 2
            
            # Check that the second call to classify_query was made with the cache parameter
            # Note: from_cache isn't passed through to the final result since classify
            # transforms the result to match what the orchestrator expects
            mock_classify_query.assert_any_call("Show me menu items at Idle Hour", None, True)

    def test_classify_fallback(self, test_config):
        """Test the classify method's fallback mechanism."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create a mock client
        mock_client = MagicMock()
        
        # Make the API call raise an exception to trigger the fallback
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Create the classifier with our mock client
        classifier = ClassificationService(config=config)
        # Replace its client with our mock
        classifier.client = mock_client
        
        # Call the classify method
        result = classifier.classify("Show me menu items at Idle Hour")
        
        # Verify the fallback result based on the transformation done by classify method
        assert result["category"] == "general_question"  # query_type becomes category
        assert "confidence" in result
        assert "time_period_clause" in result
        assert "is_followup" in result
        
        # Verify that the OpenAI API was called once (and failed)
        assert mock_client.chat.completions.create.call_count == 1

    def test_health_check_success(self, test_config):
        """Test the health_check method with a successful API response."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create the classifier
        classifier = ClassificationService(config=config)
        
        # Create a mock client and replace the actual one
        mock_client = MagicMock()
        mock_client.models.list.return_value = ["model1", "model2"]
        classifier.client = mock_client
        
        # Call the health_check method
        result = classifier.health_check()
        
        # Verify the result
        assert result is True
        # Verify that the models.list method was called
        mock_client.models.list.assert_called_once()

    def test_health_check_failure(self, test_config):
        """Test the health_check method with a failed API call."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create the classifier
        classifier = ClassificationService(config=config)
        
        # Create a mock client and replace the actual one
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("API Error")
        classifier.client = mock_client
        
        # Call the health_check method
        result = classifier.health_check()
        
        # Verify the result
        assert result is False
        # Verify that the models.list method was called
        mock_client.models.list.assert_called_once()

    def test_clear_cache(self, test_config):
        """Test the clear_cache method."""
        # Create a config with API key
        config = test_config.copy()
        config["api"] = {"openai": {"api_key": "test_api_key", "model": "gpt-4o-mini"}}
        
        # Create the classifier
        classifier = ClassificationService(config=config)
        
        # Add an item to the cache
        normalized_query = classifier._normalize_query("test query")
        classifier._classification_cache[normalized_query] = {"test": "data"}
        
        # Verify the cache has an item
        assert len(classifier._classification_cache) == 1
        
        # Call the clear_cache method
        classifier.clear_cache()
        
        # Verify the cache is empty
        assert len(classifier._classification_cache) == 0 