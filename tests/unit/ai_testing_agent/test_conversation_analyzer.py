"""
Unit tests for the ConversationAnalyzer class.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from ai_testing_agent.conversation_analyzer import ConversationAnalyzer
from ai_testing_agent.database_validator import DatabaseValidator


class TestConversationAnalyzer:
    """Tests for the ConversationAnalyzer class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        # Set up the mock response for chat completions
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "clarity": 8,
            "relevance": 7,
            "helpfulness": 9,
            "politeness": 8,
            "conciseness": 6,
            "context_awareness": 0.8,
            "consistency": 0.9
        })
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        return mock_client
    
    @pytest.fixture
    def mock_db_validator(self):
        """Create a mock database validator."""
        mock_validator = MagicMock(spec=DatabaseValidator)
        
        # Setup the validate_response method to return valid response
        mock_validator.validate_response.return_value = {
            "valid": True,
            "validation_results": [
                {
                    "fact": {"type": "menu_item", "name": "Pizza", "price": 12.99},
                    "valid": True,
                    "explanation": "Menu item price is correct"
                }
            ]
        }
        
        return mock_validator
    
    @pytest.fixture
    def analyzer(self, mock_openai_client, mock_db_validator):
        """Create a ConversationAnalyzer instance with mocks."""
        return ConversationAnalyzer(
            openai_client=mock_openai_client, 
            db_validator=mock_db_validator
        )
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation history."""
        return [
            {"role": "user", "content": "What items do you have on the menu?"},
            {"role": "assistant", "content": "We have pizza, pasta, salads, and desserts on our menu. Would you like specific details about any of these categories?"},
            {"role": "user", "content": "How much is the pepperoni pizza?"},
            {"role": "assistant", "content": "Our pepperoni pizza is $12.99 for a medium and $15.99 for a large."}
        ]
    
    def test_initialization(self, analyzer, mock_openai_client, mock_db_validator):
        """Test that the analyzer initializes correctly."""
        assert analyzer.openai_client == mock_openai_client
        assert analyzer.db_validator == mock_db_validator
        assert len(analyzer.issue_categories) > 0
    
    def test_analyze_conversation(self, analyzer, sample_conversation):
        """Test analyzing a complete conversation."""
        result = analyzer.analyze_conversation(sample_conversation)
        
        # Check that the basic structure is correct
        assert "conversation_length" in result
        assert "metrics" in result
        assert "timestamp" in result
        
        # Check conversation length calculation
        assert result["conversation_length"] == 2  # Two user messages
        
        # Check metrics
        metrics = result["metrics"]
        assert "avg_response_length" in metrics
        assert isinstance(metrics["avg_response_length"], float)
        
        # Check that OpenAI metrics were included
        assert "clarity" in metrics
        
        # Check issue detection
        assert "issues" in metrics
        assert "issue_counts" in metrics
        assert "total_issues" in metrics
    
    def test_detect_issues(self, analyzer):
        """Test detecting issues in a single response."""
        query = "What specific hours are you open tomorrow?"
        response = "We're generally open every day."
        
        issues = analyzer.detect_issues(query, response)
        
        # Should detect the vague response issue due to specificity vs. vagueness
        assert len(issues) > 0
        
        # Check a very short response
        short_response = "Yes."
        short_issues = analyzer.detect_issues(query, short_response)
        assert any(issue["category"] == "too_short" for issue in short_issues)
        
        # Check a lengthy response
        long_response = "Well, let me see. " + "We are open. " * 30
        long_issues = analyzer.detect_issues(query, long_response)
        assert any(issue["category"] == "lengthy_response" for issue in long_issues)
    
    def test_evaluate_response(self, analyzer, mock_openai_client):
        """Test evaluating a single response."""
        query = "What do you recommend for dinner?"
        response = "Our chef's special today is grilled salmon with roasted vegetables."
        
        evaluation = analyzer.evaluate_response(query, response)
        
        # Check all expected metrics are present
        assert "clarity" in evaluation
        assert "relevance" in evaluation
        assert "helpfulness" in evaluation
        assert "politeness" in evaluation
        assert "conciseness" in evaluation
        assert "overall_score" in evaluation
        
        # Verify the OpenAI client was called correctly
        mock_openai_client.chat.completions.create.assert_called()
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert query in messages[1]["content"]
        assert response in messages[1]["content"]
    
    def test_analyze_sentiment(self, analyzer, mock_openai_client):
        """Test sentiment analysis."""
        # Set up a specific mock response for sentiment analysis
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "polarity": 0.8,
            "emotion": "joy",
            "intensity": 7,
            "key_phrases": ["very happy", "wonderful experience"]
        })
        mock_openai_client.chat.completions.create.return_value.choices = [MagicMock(message=mock_message)]
        
        text = "I'm very happy with your service, it was a wonderful experience!"
        result = analyzer.analyze_sentiment(text)
        
        # Check result structure
        assert "polarity" in result
        assert "emotion" in result
        assert "intensity" in result
        assert "key_phrases" in result
        assert "timestamp" in result
        assert "text_analyzed" in result
        
        # Check values
        assert result["polarity"] == 0.8
        assert result["emotion"] == "joy"
        assert result["intensity"] == 7
        assert len(result["key_phrases"]) == 2
    
    def test_identify_ai_issues(self, analyzer, mock_openai_client):
        """Test AI-based issue identification."""
        # Setup a specific mock response for issue identification
        mock_message = MagicMock()
        mock_message.content = json.dumps([
            {
                "category": "missing_information",
                "description": "The response does not provide specific hours",
                "severity": "medium",
                "location": "entire_response",
                "suggestion": "Include specific hours for tomorrow"
            }
        ])
        mock_openai_client.chat.completions.create.return_value.choices = [MagicMock(message=mock_message)]
        
        query = "What are your hours tomorrow?"
        response = "We're open tomorrow."
        issues = analyzer._identify_ai_issues(query, response)
        
        # Check that the issue was identified
        assert len(issues) == 1
        assert issues[0]["category"] == "missing_information"
        assert "specific hours" in issues[0]["description"]
    
    def test_generate_ai_metrics(self, analyzer, mock_openai_client, sample_conversation):
        """Test generating AI-based conversation metrics."""
        metrics = ["clarity", "relevance", "helpfulness"]
        result = analyzer._generate_ai_metrics(sample_conversation, metrics)
        
        # Check that only requested metrics are included
        assert set(result.keys()).issubset(set(metrics))
        
        # Check values
        for metric in result:
            assert isinstance(result[metric], (float, int))
    
    def test_estimate_user_satisfaction(self, analyzer):
        """Test estimating user satisfaction."""
        # Create a conversation with a positive final user message
        positive_conversation = [
            {"role": "user", "content": "Can you help me?"},
            {"role": "assistant", "content": "Of course! What do you need?"},
            {"role": "user", "content": "Thank you, that was very helpful!"}
        ]
        
        # Mock the analyze_sentiment method to return a positive sentiment
        with patch.object(analyzer, 'analyze_sentiment', return_value={"polarity": 0.8}):
            satisfaction = analyzer._estimate_user_satisfaction(positive_conversation)
            assert satisfaction > 0.5  # Should be positive
        
        # Create a conversation with a negative final user message
        negative_conversation = [
            {"role": "user", "content": "Can you help me?"},
            {"role": "assistant", "content": "I'll try."},
            {"role": "user", "content": "That didn't answer my question at all."}
        ]
        
        # Mock the analyze_sentiment method to return a negative sentiment
        with patch.object(analyzer, 'analyze_sentiment', return_value={"polarity": -0.6}):
            satisfaction = analyzer._estimate_user_satisfaction(negative_conversation)
            assert satisfaction < 0.5  # Should be negative
    
    def test_format_conversation_history(self, analyzer, sample_conversation):
        """Test formatting conversation history."""
        formatted = analyzer._format_conversation_history(sample_conversation)
        
        # Check format
        assert "USER: What items do you have on the menu?" in formatted
        assert "ASSISTANT: We have pizza" in formatted
        assert "USER: How much is the pepperoni pizza?" in formatted
        assert "ASSISTANT: Our pepperoni pizza is" in formatted
    
    def test_factual_validation_integration(self, analyzer, mock_db_validator):
        """Test integration with database validator for factual checking."""
        # Set up the mock to return an invalid response
        mock_db_validator.validate_response.return_value = {
            "valid": False,
            "validation_results": [
                {
                    "fact": {"type": "menu_item", "name": "Pizza", "price": 15.99},
                    "valid": False,
                    "actual_data": {"price": 12.99},
                    "explanation": "Price is incorrect. Expected $15.99, found $12.99"
                }
            ]
        }
        
        query = "How much is the Pizza?"
        response = "The Pizza costs $15.99."
        
        issues = analyzer.detect_issues(query, response)
        
        # Should detect a factual error
        factual_errors = [issue for issue in issues if issue["category"] == "factual_error"]
        assert len(factual_errors) > 0
        assert "Price is incorrect" in factual_errors[0]["description"]
    
    def test_handle_empty_conversation(self, analyzer):
        """Test handling an empty conversation."""
        result = analyzer.analyze_conversation([])
        
        # Should return a valid result with zero length
        assert result["conversation_length"] == 0
        assert "metrics" in result
        
        # Metrics should be mostly empty
        assert len(result["metrics"]) == 0
    
    def test_error_handling(self, analyzer, mock_openai_client):
        """Test handling errors during analysis."""
        # Make OpenAI client raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        # Test error handling in evaluate_response
        result = analyzer.evaluate_response("Test query", "Test response")
        assert "error" in result
        assert "API error" in result["error"]
        
        # Test error handling in analyze_sentiment
        sentiment = analyzer.analyze_sentiment("Test text")
        assert "error" in sentiment
        assert "API error" in sentiment["error"] 