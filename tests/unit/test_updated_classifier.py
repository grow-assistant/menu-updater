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
                    "model": "gpt-4"
                }
            }
        }
        
        # Mock the openai module
        with patch('services.classification.classifier.openai') as mock_openai:
            # Initialize service
            service = ClassificationService(config)
            
            # Check that the API key was set
            assert service.api_key == "test_api_key"
            assert service.model == "gpt-4"
            assert service.categories == [
                "data_query",
                "analysis",
                "menu_update",
                "scheduling",
                "general",
                "unsupported"
            ]
            mock_openai.api_key = "test_api_key"

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
        
        # Mock the openai module
        with patch('services.classification.classifier.openai') as mock_openai:
            # Initialize service
            service = ClassificationService(config)
            
            # Setup mock for models.list
            mock_openai.models.list.return_value = ["gpt-4", "gpt-3.5-turbo"]
            
            # Call health check
            result = service.health_check()
            
            # Verify result
            assert result is True
            mock_openai.models.list.assert_called_once()

    def test_health_check_failure(self):
        """Test health check with failed API connection."""
        # Create mock config
        config = {
            "api": {
                "openai": {
                    "api_key": "test_api_key"
                }
            }
        }
        
        # Mock the openai module
        with patch('services.classification.classifier.openai') as mock_openai:
            # Initialize service
            service = ClassificationService(config)
            
            # Setup mock for models.list to raise exception
            mock_openai.models.list.side_effect = Exception("API Error")
            
            # Call health check
            result = service.health_check()
            
            # Verify result
            assert result is False
            mock_openai.models.list.assert_called_once()

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
        
        # Mock the openai module and create_classification_prompt
        with patch('services.classification.classifier.openai') as mock_openai, \
             patch.object(ClassificationService, '_create_classification_prompt') as mock_create_prompt:
            
            # Setup mocks
            mock_completion = MagicMock()
            mock_completion.choices[0].message.content = "data_query"
            mock_openai.chat.completions.create.return_value = mock_completion
            
            mock_create_prompt.return_value = {
                "system": "System prompt",
                "user": "User prompt"
            }
            
            # Initialize service
            service = ClassificationService(config)
            
            # Call classify
            context = {"session_history": []}
            result = service.classify("Show me all menu items", context)
            
            # Verify result
            assert result == "data_query"
            mock_create_prompt.assert_called_once_with("Show me all menu items", context)
            mock_openai.chat.completions.create.assert_called_once_with(
                model=service.model,
                messages=[
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": "User prompt"}
                ],
                temperature=0.3,
                max_tokens=50
            )

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
        
        # Mock the openai module and create_classification_prompt
        with patch('services.classification.classifier.openai') as mock_openai, \
             patch.object(ClassificationService, '_create_classification_prompt') as mock_create_prompt:
            
            # Setup mocks
            mock_completion = MagicMock()
            mock_completion.choices[0].message.content = "invalid_category"
            mock_openai.chat.completions.create.return_value = mock_completion
            
            mock_create_prompt.return_value = {
                "system": "System prompt",
                "user": "User prompt"
            }
            
            # Initialize service
            service = ClassificationService(config)
            
            # Call classify
            context = {"session_history": []}
            result = service.classify("What is the meaning of life?", context)
            
            # Verify result - should default to "general" for invalid categories
            assert result == "general"

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
        
        # Mock the openai module and create_classification_prompt
        with patch('services.classification.classifier.openai') as mock_openai, \
             patch.object(ClassificationService, '_create_classification_prompt') as mock_create_prompt:
            
            # Setup mocks
            mock_openai.chat.completions.create.side_effect = Exception("API Error")
            
            mock_create_prompt.return_value = {
                "system": "System prompt",
                "user": "User prompt"
            }
            
            # Initialize service
            service = ClassificationService(config)
            
            # Call classify
            context = {"session_history": []}
            result = service.classify("Show me all menu items", context)
            
            # Verify result - should default to "general" on error
            assert result == "general"

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
        
        # Initialize service
        service = ClassificationService(config)
        
        # Test with empty context
        context = {}
        prompt = service._create_classification_prompt("Show me all menu items", context)
        
        # Verify prompt structure
        assert "system" in prompt
        assert "user" in prompt
        assert "You are a query classifier" in prompt["system"]
        assert "Classify this query: Show me all menu items" in prompt["user"]
        
        # Test with session history
        context = {
            "session_history": [
                {
                    "query": "What's on the menu?",
                    "response": "We have several items on our menu..."
                }
            ]
        }
        
        prompt = service._create_classification_prompt("Show me the prices", context)
        
        # Verify prompt includes history
        assert "Recent conversation history" in prompt["user"]
        assert "What's on the menu?" in prompt["user"]
        assert "We have several items on our menu..." in prompt["user"] 