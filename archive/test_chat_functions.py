import unittest
from unittest.mock import Mock, patch
from utils.chat_functions import process_query_results
import json
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path
import requests

def load_env():
    """Load environment variables from .env file"""
    # Get the project root directory (assuming tests is one level down)
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    
    print(f"Looking for .env file at: {env_path}")  # Debug print
    
    # Check if file exists
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")
        
    # Load the .env file with override=True to ensure values are updated
    if not load_dotenv(env_path, override=True):
        raise ValueError(f"Could not load .env file at {env_path}")
    
    # Verify environment variables are loaded
    required_vars = ['GROK_TOKEN', 'GROK_API_URL', 'GROK_MODEL']
    loaded_vars = {}
    
    # Try to load each variable and print its value
    for var in required_vars:
        value = os.getenv(var)
        loaded_vars[var] = value
        if value:
            masked_value = value[:8] + '...' if len(value) > 8 else value
            print(f"Loaded {var}: {masked_value}")
        else:
            print(f"Failed to load {var} from environment")
            # Print all environment variables for debugging (mask sensitive data)
            print("\nAvailable environment variables:")
            for key, val in os.environ.items():
                if any(secret in key.lower() for secret in ['token', 'key', 'password', 'secret']):
                    masked_val = val[:8] + '...' if val else 'None'
                else:
                    masked_val = val
                print(f"{key}: {masked_val}")
    
    # Check if all required variables are present
    missing_vars = [var for var, value in loaded_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return loaded_vars

def call_grok(prompt):
    """
    Make a call to the Grok API
    """
    # Load and verify environment variables
    env_vars = load_env()
    
    # Construct the payload
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that converts database results into natural language answers."},
            {"role": "user", "content": prompt}
        ],
        "model": env_vars['GROK_MODEL'],
        "stream": False,
        "temperature": 0.3
    }

    # Log the request (mask sensitive data)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    masked_payload = payload.copy()
    masked_payload['model'] = f"{masked_payload['model'][:8]}..."
    print(f"{timestamp} - DEBUG - Grok request payload={json.dumps(masked_payload)}")

    try:
        response = requests.post(
            env_vars['GROK_API_URL'],
            json=payload,
            headers={
                "Authorization": f"Bearer {env_vars['GROK_TOKEN']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        # Check for successful response
        response.raise_for_status()
        
        # Log the response
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        print(f"{timestamp} - DEBUG - Grok response status code={response.status_code}")
        
        return response.json()['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        print(f"Error calling Grok API: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return None

class TestChatFunctions(unittest.TestCase):

    @patch('utils.chat_functions.logger')
    def test_process_query_results_success(self, mock_logger):
        # Mock Grok client
        mock_grok_client = Mock()
        mock_grok_client.return_value = "There were 3 orders completed yesterday."

        # Mock query result
        result = {
            "success": True,
            "results": [{"count": 3}],
            "columns": ["count"]
        }

        # Test the function
        user_question = "How many orders were completed yesterday?"
        response = process_query_results(result, mock_grok_client, user_question)

        # Assert the response
        self.assertEqual(response, "There were 3 orders completed yesterday.")

        # Fix: Match exact prompt formatting
        expected_prompt = (
            "You are a data translator. Convert these database results into a natural language answer.\n\n"
            "Example 1:\n"
            "Input: [{'count': 3}]\n"
            "Output: There were 3 orders completed yesterday.\n\n"
            "Example 2:\n"
            "Input: [{'sum': 149.99}]\n"
            "Output: The total revenue last month was $149.99.\n\n"
            "Now, convert the following data into a natural language answer:\n"
            f"{json.dumps([{'count': 3}])}"
        )

        mock_grok_client.assert_called_once_with(expected_prompt)

    @patch('utils.chat_functions.logger')
    def test_process_query_results_failure(self, mock_logger):
        # Mock Grok client to raise an exception
        mock_grok_client = Mock()
        mock_grok_client.side_effect = Exception("API error")

        # Mock query result
        result = {
            "success": True,
            "results": [{"count": 3}],
            "columns": ["count"]
        }

        # Test the function
        user_question = "How many orders were completed yesterday?"
        response = process_query_results(result, mock_grok_client, user_question)

        # Assert the response
        self.assertEqual(response, "Found 1 matching records: [{'count': 3}]")

        # Assert the error was logged
        mock_logger.error.assert_called_once_with("Summarization failed: API error")

    @patch('utils.chat_functions.logger')
    def test_process_query_results_no_results(self, mock_logger):
        # Mock Grok client (not used in this case)
        mock_grok_client = Mock()

        # Mock query result with no results
        result = {
            "success": True,
            "results": [],
            "columns": ["count"]
        }

        # Test the function
        user_question = "How many orders were completed yesterday?"
        response = process_query_results(result, mock_grok_client, user_question)

        # Assert the response
        self.assertEqual(response, "No matching records found for: How many orders were completed yesterday?")

    @patch('utils.chat_functions.logger')
    def test_process_query_results_query_failure(self, mock_logger):
        # Mock Grok client (not used in this case)
        mock_grok_client = Mock()

        # Mock query result with failure
        result = {
            "success": False,
            "error": "Database error"
        }

        # Test the function
        user_question = "How many orders were completed yesterday?"
        response = process_query_results(result, mock_grok_client, user_question)

        # Assert the response
        self.assertEqual(response, "Error retrieving data for: How many orders were completed yesterday?")

if __name__ == '__main__':
    unittest.main() 