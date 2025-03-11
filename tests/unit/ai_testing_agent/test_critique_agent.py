"""
Unit tests for the CritiqueAgent class.
"""

import pytest
from unittest.mock import MagicMock, patch
from ai_testing_agent.critique_agent import CritiqueAgent

class TestCritiqueAgent:
    """Tests for the CritiqueAgent class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Set up the mock response
        mock_message.content = """
CRITIQUE: The response does not directly answer the user's question about operating hours. It should provide specific hours rather than just saying "we're open daily".

RECOMMENDATION: Implement a database lookup function that retrieves the current operating hours from a centralized source to ensure accuracy across all responses.

CRITIQUE: The tone is too formal for a casual dining establishment. Consider using more conversational language.

RECOMMENDATION: Add error handling in the response generation code to catch cases where database information is missing or incomplete.
"""
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        
        return mock_client
    
    @pytest.fixture
    def mock_db_validator(self):
        """Create a mock DatabaseValidator."""
        mock_validator = MagicMock()
        mock_validator.validate_response.return_value = {
            "valid": True,
            "validation_results": [],
            "accuracy_score": 1.0
        }
        return mock_validator
    
    @pytest.fixture
    def critique_agent(self, mock_openai_client, mock_db_validator):
        """Create a CritiqueAgent with mocked dependencies."""
        return CritiqueAgent(openai_client=mock_openai_client, db_validator=mock_db_validator)
    
    def test_initialization(self, critique_agent, mock_openai_client, mock_db_validator):
        """Test that the agent initializes correctly."""
        assert critique_agent.openai_client == mock_openai_client
        assert critique_agent.db_validator == mock_db_validator
    
    def test_generate_critiques(self, critique_agent, mock_openai_client):
        """Test generating critiques for a response."""
        query = "What are your hours today?"
        response = "We're open daily. Is there anything else I can help you with?"
        conversation_history = [
            {"role": "user", "content": "Hi, I'm interested in dining at your restaurant."},
            {"role": "assistant", "content": "Welcome! We'd be happy to have you dine with us."}
        ]
        
        # Test without terminal logs
        result = critique_agent.generate_critiques(query, response, conversation_history)
        
        # Verify the OpenAI client was called correctly
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify the result structure
        assert "critiques" in result
        assert "recommendations" in result
        assert len(result["critiques"]) == 2
        assert len(result["recommendations"]) == 2
        
        # Verify critique content
        assert "hours" in result["critiques"][0]["message"].lower()
        assert "type" in result["critiques"][0]  # Just verify the type field exists
        
        # Verify recommendation content
        assert "database lookup" in result["recommendations"][0]["message"].lower()
        assert result["recommendations"][0]["category"] == "general"
    
    def test_generate_critiques_with_terminal_logs(self, critique_agent):
        """Test generating critiques with terminal logs."""
        query = "What are your hours today?"
        response = "We're open daily. Is there anything else I can help you with?"
        conversation_history = [
            {"role": "user", "content": "Hi, I'm interested in dining at your restaurant."},
            {"role": "assistant", "content": "Welcome! We'd be happy to have you dine with us."}
        ]
        terminal_logs = """
2023-10-21 14:32:45 INFO - Processing user query: What are your hours today?
2023-10-21 14:32:45 WARNING - Database connection timeout, using cached data
2023-10-21 14:32:46 INFO - Generated response in 0.35s
"""
        
        result = critique_agent.generate_critiques(query, response, conversation_history, terminal_logs)
        
        # The terminal logs should be included in the prompt
        call_args = critique_agent.openai_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        assert "Terminal Logs" in prompt
        assert "Database connection timeout" in prompt
    
    def test_db_validation_failure(self, critique_agent, mock_db_validator):
        """Test handling of database validation failures."""
        # Set up the mock db validator to return a validation failure
        mock_db_validator.validate_response.return_value = {
            "valid": False,
            "validation_results": [
                {
                    "explanation": "Incorrect operating hours provided",
                    "valid": False
                }
            ],
            "accuracy_score": 0.0
        }
        
        query = "What are your hours today?"
        response = "We're open from 9 AM to 10 PM."
        conversation_history = []
        
        # Generate critiques with the validation failure
        result = critique_agent.generate_critiques(query, response, conversation_history)
        
        # Verify that a critique was added for the factual error
        assert any(c["type"] == "factual_error" for c in result["critiques"])
    
    def test_parse_critiques(self, critique_agent):
        """Test parsing critiques from response text."""
        test_text = """
CRITIQUE: The response is missing important information about price.
Suggestion: Include price information in responses about menu items.

CRITIQUE: The system doesn't acknowledge the user's previous question.

RECOMMENDATION: Update the database query to join menu items with pricing information.
"""
        
        critiques = critique_agent._parse_critiques(test_text)
        
        assert len(critiques) == 2
        assert critiques[0]["message"].startswith("CRITIQUE: The response is missing")
        assert critiques[0]["suggestion"] == "Include price information in responses about menu items."
        assert critiques[1]["message"].startswith("CRITIQUE: The system doesn't acknowledge")
    
    def test_parse_recommendations(self, critique_agent):
        """Test parsing recommendations from response text."""
        test_text = """
CRITIQUE: The response doesn't answer the question clearly.

RECOMMENDATION: Implement a more sophisticated context tracking system to maintain conversation state.

RECOMMENDATION: High Priority: Fix the error handling in the database connection code to prevent timeouts.
"""
        
        recommendations = critique_agent._parse_recommendations(test_text)
        
        assert len(recommendations) == 2
        assert "context tracking" in recommendations[0]["message"].lower()
        assert recommendations[0]["priority"] == "medium"
        assert recommendations[1]["priority"] == "high"
        assert recommendations[1]["category"] == "bug_fix"
    
    def test_determine_critique_type(self, critique_agent):
        """Test determining critique type from content."""
        assert critique_agent._determine_critique_type("The information about prices is incorrect") == "factual_error"
        assert critique_agent._determine_critique_type("The response is very confusing and unclear") == "clarity_issue"
        assert critique_agent._determine_critique_type("The button layout doesn't make sense") == "ui_issue"
        assert critique_agent._determine_critique_type("The system is too slow to respond") == "performance_issue"
        assert critique_agent._determine_critique_type("The system ignores the previous context") == "context_issue"
        assert critique_agent._determine_critique_type("There are typos in the response") == "language_issue"
        assert critique_agent._determine_critique_type("The response is not helpful") == "general_issue"
    
    def test_determine_recommendation_category(self, critique_agent):
        """Test determining recommendation category from content."""
        assert critique_agent._determine_recommendation_category("Improve the component architecture") == "architecture"
        assert critique_agent._determine_recommendation_category("Optimize the database queries for better performance") == "performance"
        assert critique_agent._determine_recommendation_category("Fix the null reference bug in the response handler") == "bug_fix"
        assert critique_agent._determine_recommendation_category("Update the API contract to include more metadata") == "api_design"
        assert critique_agent._determine_recommendation_category("Implement a better testing workflow") == "workflow"
        assert critique_agent._determine_recommendation_category("Refactor the code to remove duplication") == "refactoring"
        assert critique_agent._determine_recommendation_category("Make improvements to the system") == "general"
    
    def test_format_conversation_history(self, critique_agent):
        """Test formatting conversation history."""
        conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        formatted = critique_agent._format_conversation_history(conversation)
        
        assert "USER: Hello" in formatted
        assert "ASSISTANT: Hi there!" in formatted
        assert "USER: How are you?" in formatted 