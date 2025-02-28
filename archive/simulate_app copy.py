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

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def process_user_query(user_query, mock_session, conversation_history=None):
    """
    Process a user query through the complete flow:
    1. OpenAI Categorization
    2. Google Gemini SQL Generation
    3. SQL Execution
    4. OpenAI Summarization
    """
    if conversation_history is None:
        conversation_history = []

    # Setup clients and test query
    openai_client, _ = get_clients()  # We won't use xAI client
    
    # Step 1: OpenAI Categorization
    print("\n🧠 Categorizing your query...")
    categorization_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_query}],
        functions=get_functions_list
    )
    
    function_call = categorization_response.choices[0].message.function_call
    if function_call:
        print(f"✓ Query identified as: {function_call.name}")
    
    # Step 2: Google Gemini SQL Generation
    print("\n🔍 Generating SQL query...")
    
    # Get previous SQL query context if available
    base_sql_query = mock_session.get("last_sql_query", None)
    
    # Generate SQL using the same approach as app.py
    sql_query = generate_sql_from_user_query(user_query, mock_session.selected_location_id, base_sql_query=base_sql_query)
    
    # Apply the same transformations as in app.py
    sql_query = sql_query.replace("created_at", "updated_at")
    
    # Store the SQL query in session state, as in app.py
    mock_session["last_sql_query"] = sql_query
    
    print(f"✓ Generated SQL: {sql_query.strip().replace(chr(10), ' ')}")
    
    # Step 3: SQL Execution
    print("\n💾 Executing SQL query...")
    
    # Apply the same timezone adjustments as in app.py
    sql_query = app.adjust_query_timezone(sql_query, mock_session.selected_location_id)
    
    result = app.execute_menu_query(sql_query)
    
    if result.get('success'):
        if result.get('results') and len(result['results']) > 0:
            print(f"✓ Query executed successfully with {len(result['results'])} results.")
            # Show the first result
            print(f"  First result: {result['results'][0]}")
            # Also print all people's names if it's a who query
            if "who" in user_query.lower() and "first_name" in result['results'][0]:
                names = [f"{r['first_name']} {r['last_name']}" for r in result['results']]
                print(f"  All people: {names}")
        else:
            print("✓ Query executed successfully, no results found.")
    else:
        print(f"✗ SQL Execution Error: {result.get('error', 'Unknown error')}")
        return "I encountered an error executing your query. Please try rephrasing your question."
    
    # Step 4: Handle follow-up question about "who" without relying as much on OpenAI
    if "who" in user_query.lower() and "first_name" in result.get('results', [{}])[0]:
        # For "who" questions with clear names in the result, construct the answer directly
        names = [f"{r['first_name']} {r['last_name']}" for r in result.get('results', [])]
        if len(names) == 1:
            return f"The order was placed by {names[0]}."
        elif len(names) > 1:
            return f"The orders were placed by:\n- " + "\n- ".join(names)
        else:
            return "I could not find any people associated with these orders."
    
    # For other questions, proceed with OpenAI summarization
    print("\n📝 Summarizing results...")
    
    # Create a context that includes conversation history
    context = ""
    if conversation_history:
        context = "Previous conversation:\n"
        # Include the most recent exchange
        last_q, last_a = conversation_history[-1]
        context += f"Q: {last_q}\nA: {last_a}\n\n"
    
    # Create a prompt for OpenAI that includes the user question and SQL results
    prompt = (
        f"{context}\n\n" if context else ""
        f"NEW QUESTION: {user_query}\n\n"
        f"DATABASE RESULTS:\n{json.dumps(result['results'], indent=2)}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Answer the NEW QUESTION above using ONLY the DATABASE RESULTS.\n"
        f"2. DO NOT repeat the previous answer.\n"
        f"3. Be specific and mention ALL data points from the results.\n"
        f"4. Format currency values with dollar signs ($).\n"
    )
    
    print(f"  Prompt length: {len(prompt)} characters")
    
    # Make the OpenAI API call for summarization
    summarization_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a direct database assistant. Answer ONLY the NEW QUESTION using the database results provided."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    # Extract the summary from the response
    summary = summarization_response.choices[0].message.content
    
    # Check if the summary is too similar to the last answer in conversation history
    if conversation_history and summary.lower().strip() == conversation_history[-1][1].lower().strip():
        # If it's repeating the last answer, create a more appropriate response
        if "count" in result['results'][0]:
            return f"There were {result['results'][0]['count']} results found."
        elif "sum" in result['results'][0]:
            return f"The total amount is ${result['results'][0]['sum']}."
        else:
            return f"The database returned {len(result['results'])} results with fields: {', '.join(result['results'][0].keys())}."
    
    print("✓ Summary generated")
    return summary

def run_interactive_session():
    """
    Run an interactive terminal session with the AI.
    """
    mock_session = MockSessionState()
    conversation_history = []
    
    print("\n" + "="*50)
    print("🤖 Welcome to the Restaurant AI Terminal Assistant")
    print("="*50)
    print("Ask questions about orders, menu items, or operations.")
    print("Type 'exit', 'quit', or Ctrl+C to end the session.")
    print("="*50 + "\n")
    
    while True:
        try:
            # Get user input
            user_query = input("\n💬 You: ").strip()
            
            # Check for exit command
            if user_query.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                print("\n👋 Thank you for using the Swoop AI. Goodbye!")
                break
            
            if not user_query:
                continue
            
            # Process the query and get response
            response = process_user_query(user_query, mock_session, conversation_history)
            
            # Display the response
            print("\n🤖 Assistant: " + response)
            
            # Save to conversation history
            conversation_history.append((user_query, response))
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n⚠️ An error occurred: {str(e)}")
            print("Let's try again with a different question.")

if __name__ == "__main__":
    run_interactive_session()