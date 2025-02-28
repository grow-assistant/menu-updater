# First, set environment variables to suppress warnings
import os
os.environ["STREAMLIT_LOG_LEVEL"] = "critical"  # Even stricter than error
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SILENCE_NON_RUNTIME_WARNING"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings

import sys
import json
import logging
from io import StringIO
from dotenv import load_dotenv
import requests
from unittest.mock import patch, MagicMock
import warnings

# Configure minimal logging - suppress ALL logs
logging.basicConfig(level=logging.CRITICAL)  # Only show critical errors

# Suppress all loggers - including absl used by gRPC
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)

# Extra suppression for specific loggers
for logger_name in ['tensorflow', 'absl', 'streamlit', 'google']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Add project root directory to path so we can import app
# Go up two levels: from tests/simulations to the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Now import the app modules
import app
from utils.function_calling_spec import functions as get_functions_list
from utils import database_functions
from utils.create_sql_statement import generate_sql_from_user_query, load_schema, create_prompt
from utils.query_processing import process_query_results

# Create a Session State class with attribute access
class MockSessionState:
    def __init__(self):
        self.selected_location_id = 62
        self.last_sql_query = None
        self.api_chat_history = [{
            "role": "system", 
            "content": "Test system prompt"
        }]
        self.full_chat_history = []
    
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)

def get_clients():
    """Get the OpenAI and xAI clients"""
    from app import get_openai_client, get_xai_config
    return get_openai_client(), get_xai_config()

def demonstrate_complete_flow():
    """
    Demonstrates a simplified complete flow with four main steps:
      1. OpenAI Categorization
      2. Google Gemini SQL Generation
      3. SQL Execution
      4. OpenAI Summarization (instead of xAI)
    """
    # Setup clients and test query
    openai_client, _ = get_clients()  # We won't use xAI client
    test_query = "How many orders were completed on 2/21/2025?"
    mock_session = MockSessionState()

    # Variables to track each step
    openai_categorization_completed = False
    gemini_step_completed = False
    sql_step_completed = False
    openai_summarization_completed = False
    
    # Track OpenAI API calls
    original_openai_create = openai_client.chat.completions.create
    openai_categorization_response = None
    openai_summarization_response = None
    
    def track_openai_create(*args, **kwargs):
        nonlocal openai_categorization_completed, openai_summarization_completed
        nonlocal openai_categorization_response, openai_summarization_response
        
        # Check if this is a categorization or summarization call
        if 'functions' in kwargs:
            # This is likely a categorization call
            if not openai_categorization_completed:
                print("\nStep 1: OpenAI Categorization")
                print("  OpenAI API call for categorization")
                openai_categorization_completed = True
                response = original_openai_create(*args, **kwargs)
                openai_categorization_response = response
                return response
        else:
            # This is likely a summarization call
            if not openai_summarization_completed and sql_step_completed:
                print("\nStep 4: OpenAI Summarization")
                print("  OpenAI API call for summarizing SQL results")
                if 'messages' in kwargs:
                    # Print the prompt being sent to OpenAI
                    print("  Messages sent to OpenAI:")
                    for msg in kwargs['messages']:
                        role = msg.get('role', 'unknown')
                        content_preview = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
                        print(f"    {role}: {content_preview}")
                
                openai_summarization_completed = True
                response = original_openai_create(*args, **kwargs)
                openai_summarization_response = response
                return response
        
        # For any other OpenAI calls
        return original_openai_create(*args, **kwargs)
    
    # Start the test flow
    print("\n▶️ EXECUTING COMPLETE FLOW")
    
    # Patch OpenAI's create method for tracking
    with patch.object(openai_client.chat.completions, 'create', side_effect=track_openai_create):
        # Step 1: OpenAI Categorization
        print("\nStep 1: OpenAI Categorization")
        with patch('streamlit.session_state', mock_session):
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": test_query}],
                functions=get_functions_list
            )
            openai_categorization_completed = True
            function_call = categorization_response.choices[0].message.function_call
            if function_call:
                print(f"  Function: {function_call.name}")
                args = json.loads(function_call.arguments)
                print(f"  Arguments: {json.dumps(args, indent=2)}")
        
        # Step 2: Google Gemini SQL Generation
        print("\nStep 2: Google Gemini SQL Generation")
        
        # Get previous SQL query context if available - mimic app.py approach
        base_sql_query = mock_session.get("last_sql_query", None)
        
        # Display the schema and prompt being used for SQL generation
        schema = load_schema()
        prompt = create_prompt(schema, test_query)
        
        print(f"  Using Gemini prompt template:")
        print(f"  {prompt[:200]}...")
        
        # Generate SQL using the same approach as app.py
        sql_query = generate_sql_from_user_query(test_query, mock_session.selected_location_id, base_sql_query=base_sql_query)
        
        # Apply the same transformations as in app.py
        sql_query = sql_query.replace("created_at", "updated_at")
        
        # Store the SQL query in session state, as in app.py
        mock_session["last_sql_query"] = sql_query
        
        gemini_step_completed = True
        print(f"  Generated SQL: {sql_query.strip().replace(chr(10), ' ')}")
        
        # Step 3: SQL Execution
        print("\nStep 3: SQL Execution")
        
        # Apply the same timezone adjustments as in app.py
        sql_query = app.adjust_query_timezone(sql_query, mock_session.selected_location_id)
        print(f"  Timezone-adjusted SQL query: {sql_query.strip().replace(chr(10), ' ')}")
        
        result = app.execute_menu_query(sql_query)
        sql_step_completed = True
        if result.get('success'):
            if result.get('results') and len(result['results']) > 0:
                print("  Query executed successfully.")
                print(f"  Sample result: {result['results'][0]}")
            else:
                print("  Query executed successfully, no results.")
        else:
            print(f"  SQL Execution Error: {result.get('error', 'Unknown error')}")
        
        # Step 4: OpenAI Summarization
        print("\nStep 4: OpenAI Summarization")
        
        # Use same COUNT detection logic as in app.py
        if "COUNT(" in sql_query.upper():
            result_keys = result.get("results", [{}])[0].keys()
            count_key = next((k for k in result_keys if "count" in k.lower()), None)
            count_value = result.get("results", [{}])[0].get(count_key, 0)
            summary = f"There were {count_value} completed orders in the specified period."
        else:
            # Create a prompt for OpenAI that includes the user question and SQL results
            prompt = (
                f"The user asked: '{test_query}'\n\n"
                f"The database returned this result: {json.dumps(result, indent=2)}\n\n"
                f"Please provide a clear, natural language answer to the user's question based on these results."
            )
            
            # Make the OpenAI API call for summarization
            summarization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use an appropriate model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that translates database results into natural language answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Extract the summary from the response
            summary = summarization_response.choices[0].message.content
        
        # Mark summarization as completed
        openai_summarization_completed = True
    
    # Final summary display
    print("\n✅ FINAL RESULT")
    print(f"  Query: {test_query}")
    print(f"  Answer: {summary}")
    
    print("\n📋 FLOW SUMMARY")
    print(f"  1. OpenAI Categorization: {'✓' if openai_categorization_completed else '✗'}")
    print(f"  2. Google Gemini SQL Generation: {'✓' if gemini_step_completed else '✗'}")
    print(f"  3. SQL Execution: {'✓' if sql_step_completed else '✗'}")
    print(f"  4. OpenAI Summarization: {'✓' if openai_summarization_completed else '✗'}")
    
    missing_steps = []
    if not openai_categorization_completed: missing_steps.append("OpenAI Categorization")
    if not gemini_step_completed: missing_steps.append("Google Gemini SQL Generation")
    if not sql_step_completed: missing_steps.append("SQL Execution")
    if not openai_summarization_completed: missing_steps.append("OpenAI Summarization")
    
    if missing_steps:
        print("\n⚠️ MISSING STEPS:")
        for step in missing_steps:
            print(f"  • {step}")

if __name__ == "__main__":
    # Run the demonstration
    demonstrate_complete_flow() 