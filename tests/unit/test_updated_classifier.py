"""
Unit tests for the updated ClassificationService using OpenAI GPT-4.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from services.classification.classifier import ClassificationService


class TestUpdatedClassificationService:
    """Test class for the updated ClassificationService."""
    
    def test_init(self):
        """Test initializing the ClassificationService."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key",
                    "model": "gpt-4o"
                }
            }
        }
        
        # Mock the get_available_query_types function in the prompt_builder
        with patch('services.classification.classifier.openai'), \
             patch('services.classification.classifier.classification_prompt_builder') as mock_prompt_builder:
            
            # Setup the mock to return our test categories
            mock_prompt_builder.get_available_query_types.return_value = [
                "order_history",
                "menu_items",
                "sales_analysis",
                "menu_update",
                "scheduling",
                "general_question"
            ]
            
            # Initialize service
            service = ClassificationService(config)
            
            # Check that the API key was set
            assert service.api_key == "test_api_key"
            assert service.model == "gpt-4o"
            
            # Check that we're getting categories from the prompt builder
            assert service.categories == [
                "order_history",
                "menu_items",
                "sales_analysis", 
                "menu_update",
                "scheduling",
                "general_question"
            ]
            
            # Verify that the prompt_builder's method was called
            mock_prompt_builder.get_available_query_types.assert_called_once()

    def test_health_check_success(self):
        """Test health check with successful API connection."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }
        
        # Initialize service
        service = ClassificationService(config)
        
        # Create a mock client and replace the real one
        mock_client = MagicMock()
        mock_client.models.list.return_value = ["gpt-4o", "gpt-3.5-turbo"]
        service.client = mock_client
        
        # Call health check
        result = service.health_check()
        
        # Verify result
        assert result is True
        
        # Verify OpenAI models.list was called
        mock_client.models.list.assert_called_once()

    def test_health_check_failure(self):
        """Test health check with API connection failure."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }
        
        # Initialize service
        service = ClassificationService(config)
        
        # Create a mock client that raises an exception
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("API Error")
        service.client = mock_client
        
        # Call health check
        result = service.health_check()
        
        # Verify result
        assert result is False
        
        # Verify OpenAI models.list was called
        mock_client.models.list.assert_called_once()

    def test_classify_success(self):
        """Test classifying a query successfully."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }

        # Mock the prompt_builder
        with patch('services.classification.classifier.classification_prompt_builder') as mock_prompt_builder:
            
            # Setup the mock to return our test categories
            mock_prompt_builder.get_available_query_types.return_value = [
                "menu_items", 
                "menu_update",
                "general_question"
            ]
            
            # Build a mock prompt
            mock_prompt_builder.build_classification_prompt.return_value = {
                "system": "You are a query classifier",
                "user": "Classify this query: Show me menu items at Idle Hour"
            }
            
            # Initialize service
            service = ClassificationService(config)
            
            # Create a mock client with response
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"query_type": "menu_items", "confidence": 0.95}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response
            service.client = mock_client
            
            # Classify
            result = service.classify_query("Show me menu items at Idle Hour")
            
            # Verify OpenAI was called
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            
            assert call_args['model'] == service.model
            assert isinstance(call_args['messages'], list)
            assert len(call_args['messages']) == 2
            assert call_args['messages'][0]['content'] == "You are a query classifier"
            
            # Check result
            assert result["query_type"] == "menu_items"
            assert "confidence" in result

    def test_classify_invalid_category(self):
        """Test classifying a query that returns an invalid category."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }

        # Mock the prompt_builder
        with patch('services.classification.classifier.classification_prompt_builder') as mock_prompt_builder:
            
            # Setup the mock to return our test categories
            mock_prompt_builder.get_available_query_types.return_value = [
                "menu_items", 
                "menu_update",
                "general_question"
            ]
            
            # Build a mock prompt
            mock_prompt_builder.build_classification_prompt.return_value = {
                "system": "You are a query classifier",
                "user": "Classify this query: What's the weather like?"
            }
            
            # Initialize service
            service = ClassificationService(config)
            
            # Create a mock client with an invalid category response
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"query_type": "invalid_category", "confidence": 0.8}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response
            service.client = mock_client
            
            # Call classify_query
            result = service.classify_query("What's the weather like?")
            
            # Check result - should use fallback category
            assert result["query_type"] == "general_question"
            assert result["classification_method"] == "ai"  # Still classified by AI but with fallback

    def test_classify_api_error(self):
        """Test classifying a query when the API returns an error."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }

        # Mock the openai module and prompt_builder
        with patch('services.classification.classifier.openai') as mock_openai, \
             patch('services.classification.classifier.classification_prompt_builder') as mock_prompt_builder:
            
            # Setup the mock to return our test categories
            mock_prompt_builder.get_available_query_types.return_value = [
                "menu_items", 
                "menu_update",
                "general_question"
            ]
            
            # Build a mock prompt
            mock_prompt_builder.build_classification_prompt.return_value = {
                "system": "You are a query classifier",
                "user": "Classify this query: This will fail"
            }
            
            # Mock OpenAI API error
            mock_openai.chat.completions.create.side_effect = Exception("API Error")
            
            # Initialize service
            service = ClassificationService(config)
            
            # Call classify_query instead of the wrapper method
            result = service.classify_query("This will fail")
            
            # Check result - should use fallback values
            assert result["query_type"] == "general_question"
            assert result["confidence"] == 0.1
            assert result["classification_method"] == "fallback"

    def test_create_classification_prompt(self):
        """Test creating the classification prompt."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }

        # Mock the prompt_builder
        with patch('services.classification.classifier.classification_prompt_builder') as mock_prompt_builder:
            # Mock the build_classification_prompt method
            expected_prompt = {
                "system": "You are a query classifier",
                "user": "Classify this query: Show me all menu items"
            }
            mock_prompt_builder.build_classification_prompt.return_value = expected_prompt
            
            # Initialize service
            service = ClassificationService(config)
            
            # Test with empty context
            context = {}
            
            # Call the method directly through the prompt_builder
            result = service.prompt_builder.build_classification_prompt(
                query="Show me all menu items",
                context=context
            )
            
            # Check the result
            assert result == expected_prompt
            
            # Verify the prompt builder was called correctly
            mock_prompt_builder.build_classification_prompt.assert_called_once_with(
                query="Show me all menu items",
                context=context
            ) 