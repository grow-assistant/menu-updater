"""
Unit tests for the AIUserSimulator class.
"""

import pytest
from unittest.mock import MagicMock, patch
import random
from ai_testing_agent.ai_user_simulator import AIUserSimulator, DEFAULT_PERSONAS

class TestAIUserSimulator:
    """Tests for the AIUserSimulator class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        return mock_client
        
    @pytest.fixture
    def simulator(self, mock_openai_client):
        """Create an AIUserSimulator with a mock OpenAI client."""
        return AIUserSimulator(openai_client=mock_openai_client, persona="casual_diner")
        
    def test_initialization(self, simulator, mock_openai_client):
        """Test that the simulator initializes correctly."""
        assert simulator.openai_client == mock_openai_client
        assert simulator.persona == "casual_diner"
        assert simulator.persona_data == DEFAULT_PERSONAS["casual_diner"]
        assert simulator.conversation_history == []
        assert simulator.error_rate == 0.0
        
    def test_set_persona(self, simulator):
        """Test setting the persona."""
        simulator.set_persona("frequent_customer")
        
        assert simulator.persona == "frequent_customer"
        assert simulator.persona_data == DEFAULT_PERSONAS["frequent_customer"]
        
    def test_set_persona_unknown(self, simulator):
        """Test setting an unknown persona."""
        original_persona = simulator.persona
        original_persona_data = simulator.persona_data
        
        simulator.set_persona("nonexistent_persona")
        
        # Should keep the original persona
        assert simulator.persona == original_persona
        assert simulator.persona_data == original_persona_data
        
    def test_set_context(self, simulator):
        """Test setting context for the simulator."""
        context = {"order_history": [{"date": "2023-01-15", "items": ["Pizza"]}]}
        simulator.set_context(context)
        
        assert hasattr(simulator, 'context')
        assert simulator.context == context
        
    def test_generate_initial_query(self, simulator, mock_openai_client):
        """Test generating an initial query."""
        # Set up the mock to return a specific response
        mock_message = MagicMock()
        mock_message.content = "What are your specials today?"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        query = simulator.generate_initial_query()
        
        # Verify the query is what we expected
        assert query == "What are your specials today?"
        
        # Verify the prompt structure
        call_args = mock_openai_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4o"
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert "persona" in call_args["messages"][0]["content"]
        assert call_args["messages"][1]["role"] == "user"
        
        # Verify the conversation history is updated
        assert len(simulator.conversation_history) == 1
        assert simulator.conversation_history[0]["role"] == "user"
        assert simulator.conversation_history[0]["content"] == "What are your specials today?"
        
    def test_generate_followup(self, simulator, mock_openai_client):
        """Test generating a follow-up query."""
        # Add some conversation history
        simulator.conversation_history = [
            {"role": "user", "content": "What are your specials today?"},
            {"role": "assistant", "content": "Today we have a seafood pasta special for $18.99."}
        ]
        
        # Set up the mock to return a specific response
        mock_message = MagicMock()
        mock_message.content = "Does that come with any sides?"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        query = simulator.generate_followup("Today we have a seafood pasta special for $18.99.")
        
        # Verify the query is what we expected
        assert query == "Does that come with any sides?"
        
        # Verify the prompt structure
        call_args = mock_openai_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4o"
        
        # Check that messages include system, history, and user prompts
        messages = call_args["messages"]
        assert messages[0]["role"] == "system"
        assert len(messages) > 3  # System + history + user prompt
        
        # Verify the conversation history is updated
        assert len(simulator.conversation_history) == 3
        assert simulator.conversation_history[2]["role"] == "user"
        assert simulator.conversation_history[2]["content"] == "Does that come with any sides?"
        
    def test_error_handling_initial_query(self, simulator, mock_openai_client):
        """Test error handling when generating an initial query."""
        # Make the API call raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        # Make random.choice deterministic
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "What are your most popular dishes?"
            
            query = simulator.generate_initial_query()
            
            # Should fall back to an example
            assert query == "What are your most popular dishes?"
            
            # Verify the conversation history contains the fallback
            assert len(simulator.conversation_history) == 1
            assert simulator.conversation_history[0]["content"] == "What are your most popular dishes?"
        
    def test_error_handling_followup(self, simulator, mock_openai_client):
        """Test error handling when generating a follow-up query."""
        # Add some conversation history
        simulator.conversation_history = [
            {"role": "user", "content": "What are your specials today?"}
        ]
        
        # Make the API call raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        query = simulator.generate_followup("Today we have a seafood pasta special for $18.99.")
        
        # Should fall back to a generic follow-up
        assert query == "Can you tell me more about that?"
        
        # Verify the conversation history contains both the system response and fallback
        assert len(simulator.conversation_history) == 3
        assert simulator.conversation_history[1]["role"] == "assistant"
        assert simulator.conversation_history[1]["content"] == "Today we have a seafood pasta special for $18.99."
        assert simulator.conversation_history[2]["role"] == "user"
        assert simulator.conversation_history[2]["content"] == "Can you tell me more about that?"
        
    def test_introduce_error_typo(self):
        """Test introducing a typo error."""
        simulator = AIUserSimulator(error_rate=1.0)
        
        # Create a completely deterministic version of the _introduce_error method for testing
        def mock_introduce_error(original_text):
            # Always return a specific modified text
            return "What are yaur specials today?"
            
        # Replace the method with our mock
        simulator._introduce_error = mock_introduce_error
        
        original_text = "What are your specials today?"
        modified_text = simulator._introduce_error(original_text)
        
        # Text should be modified but length should stay the same
        assert modified_text != original_text
        assert len(modified_text) == len(original_text)
        assert modified_text == "What are yaur specials today?"
        
    def test_introduce_error_omission(self):
        """Test introducing an omission error."""
        simulator = AIUserSimulator(error_rate=1.0)
        
        # Mock the random choice to always return "omission"
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "omission"
            
            # Mock randint to always return position 2
            with patch('random.randint') as mock_randint:
                mock_randint.return_value = 2
                
                original_text = "What are your specials today?"
                modified_text = simulator._introduce_error(original_text)
                
                # Text should be modified and have one fewer word
                assert modified_text != original_text
                assert len(modified_text.split()) == len(original_text.split()) - 1
        
    def test_introduce_error_extra_words(self):
        """Test introducing extra words."""
        simulator = AIUserSimulator(error_rate=1.0)
        
        # Mock the random choice to always return "extra_words"
        with patch('random.choice') as mock_choice:
            mock_choice.side_effect = ["extra_words", "um"]  # First for error type, then for filler word
            
            # Mock randint to always return position 2
            with patch('random.randint') as mock_randint:
                mock_randint.return_value = 2
                
                original_text = "What are your specials today?"
                modified_text = simulator._introduce_error(original_text)
                
                # Text should be modified and have one more word
                assert modified_text != original_text
                assert len(modified_text.split()) == len(original_text.split()) + 1
                assert "um" in modified_text
        
    def test_introduce_error_grammar(self):
        """Test introducing grammar errors."""
        simulator = AIUserSimulator(error_rate=1.0)
        
        # Mock the random choice to always return "grammar"
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "grammar"
            
            original_text = "The specials are very nice today."
            modified_text = simulator._introduce_error(original_text)
            
            # Text should be modified with a grammar error
            assert modified_text != original_text
            assert "The specials is very nice today." == modified_text 