"""
Unit tests for the TestingOrchestrator class.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch
from ai_testing_agent.test_orchestrator import TestingOrchestrator
from ai_testing_agent.headless_streamlit import HeadlessStreamlit
from ai_testing_agent.ai_user_simulator import AIUserSimulator
from ai_testing_agent.database_validator import DatabaseValidator


@pytest.fixture
def mock_headless_app():
    """Create a mock HeadlessStreamlit app."""
    mock_app = MagicMock(spec=HeadlessStreamlit)
    mock_app.terminal_output = []
    
    # Mock context manager for chat_message
    mock_container = MagicMock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_container
    mock_app.chat_message.return_value = mock_context_manager
    
    return mock_app


@pytest.fixture
def mock_user_simulator():
    """Create a mock AIUserSimulator."""
    mock_simulator = MagicMock(spec=AIUserSimulator)
    mock_simulator.generate_initial_query.return_value = "What are your specials today?"
    mock_simulator.generate_followup.return_value = "How much does it cost?"
    mock_simulator.error_rate = 0.0
    return mock_simulator


@pytest.fixture
def mock_db_validator():
    """Create a mock DatabaseValidator."""
    mock_validator = MagicMock(spec=DatabaseValidator)
    mock_validator.validate_response.return_value = {
        "validation_results": [],
        "accuracy_score": 1.0,
        "valid": True
    }
    return mock_validator


@pytest.fixture
def test_scenarios():
    """Create test scenarios for testing."""
    return {
        "test_scenario": {
            "description": "A test scenario",
            "persona": "casual_diner",
            "context": {
                "inquiry_type": "menu"
            },
            "response_type": "menu_query",
            "max_turns": 2,
            "error_rate": 0.0
        }
    }


@pytest.fixture
def orchestrator(mock_headless_app, mock_user_simulator, mock_db_validator, test_scenarios):
    """Create a TestingOrchestrator with mock components."""
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = TestingOrchestrator(
            mock_headless_app,
            mock_user_simulator,
            mock_db_validator,
            test_scenarios,
            results_dir=temp_dir
        )
        yield orchestrator


class TestTestingOrchestrator:
    """Tests for the TestingOrchestrator class."""
    
    def test_initialization(self, orchestrator, mock_headless_app, mock_user_simulator, 
                          mock_db_validator, test_scenarios):
        """Test that the orchestrator initializes correctly."""
        assert orchestrator.headless_app == mock_headless_app
        assert orchestrator.user_simulator == mock_user_simulator
        assert orchestrator.db_validator == mock_db_validator
        assert orchestrator.test_scenarios == test_scenarios
        assert isinstance(orchestrator.test_results, list)
        assert len(orchestrator.test_results) == 0
        assert isinstance(orchestrator.monitoring_callbacks, list)
        assert len(orchestrator.monitoring_callbacks) == 0
        
    def test_run_test_scenario(self, orchestrator, mock_headless_app, mock_user_simulator, mock_db_validator):
        """Test running a single test scenario."""
        # Setup mock app to return a response
        def set_input_side_effect(text):
            # Add a response to terminal_output when set_input is called
            mock_headless_app.current_input = text
            mock_headless_app.terminal_output.append({
                "text": f"Echo: {text}",
                "role": "assistant",
                "timestamp": 0,
                "response_time": 0,
                "session_id": "test_session"
            })
        
        mock_headless_app.set_input.side_effect = set_input_side_effect
        
        # Run the test scenario
        result = orchestrator.run_test_scenario("test_scenario")
        
        # Verify the app was reset
        mock_headless_app.reset.assert_called_once()
        
        # Verify user simulator was used with the right context
        mock_user_simulator.set_context.assert_called_once()
        mock_user_simulator.set_persona.assert_called_once_with("casual_diner")
        mock_user_simulator.generate_initial_query.assert_called_once()
        
        # We set max_turns to 2 in the test scenario, so generate_followup should be called once
        mock_user_simulator.generate_followup.assert_called_once()
        
        # Verify validation was called
        assert mock_db_validator.validate_response.call_count == 2
        
        # Check the result structure
        assert result["scenario"] == "test_scenario"
        assert result["status"] == "success"
        assert result["error"] is None
        assert len(result["interactions"]) == 2
        assert len(result["validation_results"]) == 2
        assert "execution_time" in result
        assert "timestamp" in result
        
        # Verify the result was saved
        assert len(orchestrator.test_results) == 1
        assert orchestrator.test_results[0] == result
        
    def test_run_nonexistent_scenario(self, orchestrator):
        """Test running a scenario that doesn't exist."""
        result = orchestrator.run_test_scenario("nonexistent_scenario")
        
        assert result["scenario"] == "nonexistent_scenario"
        assert result["status"] == "error"
        assert "not found" in result["error"]
        assert len(result["interactions"]) == 0
        assert len(result["validation_results"]) == 0
        
    def test_run_all_scenarios(self, orchestrator):
        """Test running all scenarios."""
        # Add another test scenario
        orchestrator.test_scenarios["another_test"] = {
            "description": "Another test scenario",
            "persona": "new_user",
            "context": {
                "inquiry_type": "general"
            },
            "response_type": "general",
            "max_turns": 1,
            "error_rate": 0.0
        }
        
        # Mock the run_test_scenario method to avoid actual execution
        with patch.object(orchestrator, 'run_test_scenario') as mock_run:
            mock_run.side_effect = lambda name: {"scenario": name, "status": "success"}
            
            results = orchestrator.run_all_scenarios()
            
            # Verify both scenarios were run
            assert mock_run.call_count == 2
            assert len(results) == 2
            assert results[0]["scenario"] == "test_scenario"
            assert results[1]["scenario"] == "another_test"
            
    def test_add_monitoring_callback(self, orchestrator):
        """Test adding a monitoring callback."""
        callback = MagicMock()
        orchestrator.add_monitoring_callback(callback)
        
        assert len(orchestrator.monitoring_callbacks) == 1
        assert orchestrator.monitoring_callbacks[0] == callback
        
    def test_generate_report(self, orchestrator):
        """Test generating a report from test results."""
        # Add some mock results
        orchestrator.test_results = [
            {
                "scenario": "test1",
                "status": "success",
                "interactions": [{}, {}],  # 2 interactions
                "validation_results": [{"valid": True}, {"valid": True}],
                "execution_time": 1.5
            },
            {
                "scenario": "test2",
                "status": "validation_error",
                "interactions": [{}, {}, {}],  # 3 interactions
                "validation_results": [{"valid": True}, {"valid": False}],
                "execution_time": 2.0
            },
            {
                "scenario": "test3",
                "status": "error",
                "error": "Test error",
                "interactions": [{}],  # 1 interaction
                "validation_results": [],
                "execution_time": 0.5
            }
        ]
        
        report = orchestrator.generate_report()
        
        # Verify the report statistics
        assert report["total_scenarios"] == 3
        assert report["successful_scenarios"] == 1
        assert report["validation_errors"] == 1
        assert report["errors"] == 1
        assert report["warnings"] == 0
        assert report["success_rate"] == 1/3
        assert report["total_interactions"] == 6
        assert report["avg_interactions_per_scenario"] == 2.0
        assert report["total_execution_time"] == 4.0
        assert report["avg_time_per_scenario"] == 4.0/3
        
        # Verify validation statistics
        assert report["validation_statistics"]["validation_count"] == 4
        assert report["validation_statistics"]["valid_responses"] == 3
        assert report["validation_statistics"]["invalid_responses"] == 1
        assert report["validation_statistics"]["validation_success_rate"] == 0.75
        
    def test_process_input(self, orchestrator, mock_headless_app):
        """Test the _process_input method."""
        mock_headless_app.current_input = "Test query"
        
        orchestrator._process_input()
        
        # Verify that chat_message was called correctly
        mock_headless_app.chat_message.assert_called_once_with("assistant")
        
        # Verify that the container's write method was called
        container = mock_headless_app.chat_message.return_value.__enter__.return_value
        container.write.assert_called_once_with("Echo: Test query")
        
    def test_should_terminate_with_phrases(self, orchestrator):
        """Test termination conditions with termination phrases."""
        scenario = {
            "termination_phrases": ["goodbye", "thank you"]
        }
        
        interactions = [
            {"response": "Hello, how can I help you?"},
            {"response": "Thank you for your order. Goodbye!"}
        ]
        
        # Should terminate because the response contains "goodbye"
        assert orchestrator._should_terminate(scenario, 1, interactions) is True
        
        # Change the last response to not include any termination phrases
        interactions[-1]["response"] = "Your order will be ready in 15 minutes."
        assert orchestrator._should_terminate(scenario, 1, interactions) is False
        
    def test_should_terminate_with_success_conditions(self, orchestrator):
        """Test termination conditions with success conditions."""
        scenario = {
            "success_conditions": [
                {"type": "response_contains", "phrase": "order has been confirmed"}
            ]
        }
        
        interactions = [
            {"response": "Hello, how can I help you?"},
            {"response": "Your order has been confirmed and will be ready soon."}
        ]
        
        # Should terminate because the response contains "order has been confirmed"
        assert orchestrator._should_terminate(scenario, 1, interactions) is True
        
        # Change the last response to not include the success condition
        interactions[-1]["response"] = "What else would you like to order?"
        assert orchestrator._should_terminate(scenario, 1, interactions) is False
        
    def test_save_result(self, orchestrator):
        """Test saving a result to a file."""
        # Create a test result
        result = {
            "scenario": "test_save",
            "status": "success",
            "interactions": [],
            "validation_results": [],
            "execution_time": 1.0,
            "timestamp": 1234567890
        }
        
        # Mock the json.dump function to verify it was called correctly
        with patch("json.dump") as mock_json_dump:
            # Mock the open function
            mock_open = MagicMock()
            with patch("builtins.open", mock_open):
                orchestrator._save_result(result)
                
            # Verify the file was opened for writing
            mock_open.assert_called_once()
            file_path = mock_open.call_args[0][0]
            assert "test_save_" in file_path
            
            # Verify json.dump was called with the correct arguments
            mock_json_dump.assert_called_once()
            assert mock_json_dump.call_args[0][0] == result  # First arg should be the result dict
        
    def test_default_scenarios(self):
        """Test the default scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            orchestrator = TestingOrchestrator(
                MagicMock(),
                MagicMock(),
                results_dir=temp_dir
            )
            
        scenarios = orchestrator.test_scenarios
        
        # Verify some common scenario names are present
        assert "menu_inquiry_casual" in scenarios
        assert "order_history_inquiry" in scenarios
        assert "new_user_confusion" in scenarios
        
        # Verify a scenario structure
        menu_scenario = scenarios["menu_inquiry_casual"]
        assert menu_scenario["persona"] == "casual_diner"
        assert menu_scenario["response_type"] == "menu_query"
        assert "max_turns" in menu_scenario
        assert "error_rate" in menu_scenario
        
    def test_generate_ai_test_cases(self, orchestrator, mock_user_simulator):
        """Test generating AI test cases."""
        # Mock the OpenAI response
        mock_openai = MagicMock()
        mock_message = MagicMock()
        mock_message.content = """```json
{
  "vegetarian_menu_inquiry": {
    "description": "Customer asking about vegetarian options",
    "persona": "casual_diner",
    "context": {
      "inquiry_type": "menu",
      "dietary_preference": "vegetarian"
    },
    "response_type": "menu_query",
    "max_turns": 3,
    "error_rate": 0.0
  }
}
```"""
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        mock_user_simulator.openai_client = mock_openai
        
        # Generate test cases
        test_cases = orchestrator.generate_ai_test_cases("vegetarian menu options")
        
        # Verify OpenAI was called correctly
        mock_openai.chat.completions.create.assert_called_once()
        call_args = mock_openai.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4o"
        assert len(call_args["messages"]) == 2
        assert "vegetarian menu options" in call_args["messages"][1]["content"]
        
        # Verify the parsed test case
        assert "vegetarian_menu_inquiry" in test_cases
        assert test_cases["vegetarian_menu_inquiry"]["persona"] == "casual_diner"
        assert test_cases["vegetarian_menu_inquiry"]["context"]["dietary_preference"] == "vegetarian"
        
        # Verify the test case was added to the orchestrator's scenarios
        assert "vegetarian_menu_inquiry" in orchestrator.test_scenarios
        
    def test_parse_generated_test_cases(self, orchestrator):
        """Test parsing generated test cases from different formats."""
        # Test with JSON in code block
        markdown_json = """
Here are the test cases:

```json
{
  "test_case_1": {
    "description": "Test case 1"
  },
  "test_case_2": {
    "description": "Test case 2"
  }
}
```
        """
        parsed = orchestrator._parse_generated_test_cases(markdown_json)
        assert len(parsed) == 2
        assert "test_case_1" in parsed
        assert parsed["test_case_1"]["description"] == "Test case 1"
        
        # Test with raw JSON
        raw_json = '{"test_case_3": {"description": "Test case 3"}}'
        parsed = orchestrator._parse_generated_test_cases(raw_json)
        assert len(parsed) == 1
        assert "test_case_3" in parsed
        
        # Test with invalid JSON
        invalid_json = "This is not JSON"
        parsed = orchestrator._parse_generated_test_cases(invalid_json)
        assert parsed == {} 