# First, set environment variables to suppress warnings
import os
os.environ["STREAMLIT_LOG_LEVEL"] = "critical"  # Even stricter than error
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SILENCE_NON_RUNTIME_WARNING"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings

# Import streamlit at the top level and set page config as the very first Streamlit command
try:
    import streamlit as st
    
    # Define the Swoop logo SVG for use as favicon (use a simplified version for favicon)
    # Convert SVG to base64 for use as favicon
    import base64
    from PIL import Image
    import io
    
    # Create a simplified SVG for the favicon (simpler version works better as a small icon)
    favicon_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 278.91 239.64">
      <path fill="white" d="M288,65l-5.57-2.08c-36.59-13.68-42.36-15.33-43.86-15.53a40.71,40.71,0,0,0-70.51,4.28c-.85-.06-1.7-.11-2.56-.13h-.94c-.56,0-1.11,0-1.66,0a58.92,58.92,0,0,0-22.8,5A58.11,58.11,0,0,0,118.45,72.7L9.09,178.42l95.22-5.11-1.73,95.33L207.09,151.29a59.63,59.63,0,0,0,15.68-38.1c0-.11,0-.23,0-.34,0-.6,0-1.2,0-1.8s0-1,0-1.45c0-.24,0-.49,0-.74,0-.85-.07-1.69-.14-2.54a41,41,0,0,0,21-24.82,15.56,15.56,0,0,0,3.57-1Z" transform="translate(-9.09 -29)"/>
    </svg>
    """
    
    # Encode the SVG as a data URL
    svg_b64 = base64.b64encode(favicon_svg.encode()).decode()
    favicon_url = f"data:image/svg+xml;base64,{svg_b64}"
    
    # Set page config with the SVG logo as favicon
    st.set_page_config(
        page_title="Swoop AI",
        page_icon=favicon_url,  # Use the SVG logo instead of the emoji
        layout="wide",
        initial_sidebar_state="expanded",
    )
except ImportError:
    st = None
except Exception as e:
    # Fallback to emoji if there's any issue with the SVG
    try:
        import streamlit as st
        st.set_page_config(
            page_title="Swoop AI", 
            page_icon="🦅",  # Fallback to an eagle emoji if SVG fails
            layout="wide",
            initial_sidebar_state="expanded",
        )
        print(f"Error setting favicon: {e}")
    except:
        st = None

import sys
import json
import logging
from io import StringIO, BytesIO
from dotenv import load_dotenv
import requests
from unittest.mock import patch, MagicMock
import warnings
import datetime
import re
import time
import threading
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, Union, Tuple, List, Dict, Any

# Global variables for voice feature availability
ELEVENLABS_AVAILABLE = False
USE_NEW_API = False
PYGAME_AVAILABLE = False
pygame = None

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
from utils.create_sql_statement import generate_sql_from_user_query, load_schema, create_prompt, generate_sql_with_custom_prompt
from utils.query_processing import process_query_results

# Import the conversation paths
import sys
import os

# Add the tests/simulations directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'simulations'))


from utils.test_conversation_paths import get_path_for_testing

# Import system and business rules
from prompts.system_rules import (
    ORDER_STATUS, 
    RATING_SIGNIFICANCE, 
    ORDER_TYPES,
    QUERY_RULES
)

# Import business-specific rules
from prompts.business_rules import (
    get_business_context,
    BUSINESS_METRICS,
    TIME_PERIOD_GUIDANCE,
    DEFAULT_LOCATION_ID,
    ORDER_DETAIL_FIELDS
)

# Import the prompt templates
from utils.prompt_templates import (
    create_categorization_prompt,
    create_gemini_prompt,
    create_summary_prompt,
    create_system_prompt_with_business_rules,
    is_followup_query
)

# Import the summarization prompt
from prompts.summarization_prompt import create_summarization_prompt

# Import the personas from the dedicated file
from prompts.personas import get_persona_prompt, get_persona_voice_id, get_persona_info

# Define the available personas (only the non-commented ones from the personas.py file)
AVAILABLE_PERSONAS = ["casual", "professional", "enthusiastic"]

# Ensure logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up a file logger for Gemini communications
current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
gemini_logger = logging.getLogger('gemini_communications')
gemini_logger.setLevel(logging.INFO)
gemini_log_file = f"logs/gemini_comms_{current_time}.log"
gemini_file_handler = logging.FileHandler(gemini_log_file, mode='w', encoding='utf-8')
gemini_file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
gemini_file_handler.setFormatter(formatter)
gemini_logger.addHandler(gemini_file_handler)
gemini_logger.propagate = False  # Don't propagate to root logger

# Log start of session
gemini_logger.info(f"=== New Gemini Session Started at {current_time} ===")
gemini_logger.info("Gemini communication logging initialized")

# Set up OpenAI communications logger
openai_logger = logging.getLogger('openai_communications')
openai_logger.setLevel(logging.INFO)
openai_log_file = f"logs/openai_comms_{current_time}.log"
openai_file_handler = logging.FileHandler(openai_log_file, mode='w', encoding='utf-8')
openai_file_handler.setLevel(logging.INFO)
openai_file_handler.setFormatter(formatter)
openai_logger.addHandler(openai_file_handler)
openai_logger.propagate = False

# Log start of OpenAI session
openai_logger.info(f"=== New OpenAI Session Started at {current_time} ===")
openai_logger.info("OpenAI communication logging initialized")

# Create a Session State class with attribute access
class MockSessionState:
    def __init__(self):
        self.selected_location_id = 62  # Default to Idle Hour Country Club
        self.selected_location_ids = [62]  # Default to Idle Hour as a list
        self.selected_club = "Idle Hour Country Club"  # Default club
        
        # Club to location mapping
        self.club_locations = {
            "Idle Hour Country Club": {
                "locations": [62],
                "default": 62
            },
            "Pinetree Country Club": {
                "locations": [61, 66],
                "default": 61
            },
            "East Lake Golf Club": {
                "locations": [16],
                "default": 16
            }
        }
        
        # Location ID to name mapping
        self.location_names = {
            62: "Idle Hour Country Club",
            61: "Pinetree Country Club (Location 61)",
            66: "Pinetree Country Club (Location 66)",
            16: "East Lake Golf Club"
        }
        self.last_sql_query = None
        self.api_chat_history = [{"role": "system", "content": "Test system prompt"}]
        self.full_chat_history = []
        self.date_filter_cache = {
            'start_date': datetime.datetime.now().strftime("%Y-%m-%d"),
            'end_date': datetime.datetime.now().strftime("%Y-%m-%d")
        }  # Initialize with current date
    
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)

class CategorizationResult(BaseModel):
    request_type: str = Field(..., description="Type of request from predefined categories")
    time_period: Optional[str] = Field(None, description="Time period for order history queries")
    analysis_type: Optional[str] = Field(None, description="Type of analysis being requested")
    start_date: Optional[str] = Field(
        None, 
        description="Start date filter in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: Optional[str] = Field(
        None, 
        description="End date filter in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    item_name: Optional[str] = Field(None, description="Menu item name for update/enable/disable requests")
    new_price: Optional[float] = Field(None, description="New price for menu items", ge=0)

    # Validator to ensure date ordering
    @validator('start_date', 'end_date', pre=True)
    def check_dates(cls, v):
        start = v['start_date']
        end = v['end_date']
        
        if start and end:
            if start > end:
                raise ValueError("start_date must be before end_date")
                
        # Only modify dates if BOTH are missing
        if not start and not end:
            # Let calling code handle fallback to cached dates
            return v
            
        # If only one date provided, use it for both
        if start and not end:
            v['end_date'] = start
        elif end and not start:
            v['start_date'] = end
            
        return v

def get_clients():
    """Get the OpenAI and xAI clients"""
    from app import get_openai_client, get_xai_config
    return get_openai_client(), get_xai_config()

def load_application_context():
    """Load all application context files and configuration in one place
    
    Returns:
        dict: A dictionary containing all application context including
              business rules, database schema, and example queries
    """
    try:
        # Import all business rules from both system and business-specific modules
        from prompts.system_rules import ORDER_STATUS, RATING_SIGNIFICANCE, ORDER_TYPES, QUERY_RULES
        from prompts.business_rules import get_business_context, BUSINESS_METRICS, TIME_PERIOD_GUIDANCE, DEFAULT_LOCATION_ID
        
        # Get the combined business context
        business_context = get_business_context()
        
        # Load database schema
        with open('prompts/database_schema.md', 'r', encoding='utf-8') as f:
            database_schema = f.read()
            
        # Load example queries
        from prompts.example_queries import EXAMPLE_QUERIES
        
        # Create an integrated context object with all business rules
        return {
            'business_rules': business_context,
            'database_schema': database_schema,
            'example_queries': EXAMPLE_QUERIES
        }
    except Exception as e:
        print(f"Error loading application context: {str(e)}")
        return None

def demonstrate_complete_flow(test_query=None, previous_context=None, persona=None, voice=None, mock_session=None):
    """
    Demonstrates a complete end-to-end flow with four main steps:
      1. OpenAI Query Categorization
      2. Contextual Google Gemini SQL Generation
      3. SQL Execution with Error Handling
      4. OpenAI Result Summarization
      
    Args:
        test_query (str, optional): Query to test. Defaults to a sample query if not provided.
        previous_context (dict, optional): Context from previous queries for follow-up handling.
        persona (str, optional): Persona to use for verbal answers. Options: 'casual', 'professional', 'enthusiastic'
        voice (ElevenLabsVoice, optional): Voice instance to use for text-to-speech. None to disable voice.
        mock_session (MockSessionState, optional): Session state with location settings. If None, a default instance is created.
        
    Returns:
        dict: Flow results containing success status, summary, and step details
    """
    # IMPROVEMENT 1 - EFFICIENCY: Optimized flow logic with better caching and reuse
    print("\n>> EXECUTING ENHANCED FLOW")
    
    # Initialize client and session
    openai_client, _ = get_clients()
    
    # Use provided mock_session or create a default one
    if mock_session is None:
        mock_session = MockSessionState()
    
    # Use provided test query or default to a sample
    if not test_query:
        test_query = "How many orders were completed on 2/21/2025?"
    
    # Initialize or retrieve conversation history
    conversation_history = []
    if previous_context and 'conversation_history' in previous_context:
        conversation_history = previous_context['conversation_history']
        # Restore date cache from previous context
        if 'date_filter' in previous_context:
            mock_session.date_filter_cache = previous_context['date_filter']
    
    # IMPROVEMENT 2 - READABILITY: Better step tracking with detailed status dictionary
    flow_steps = {
        'categorization': {'name': 'OpenAI Categorization', 'status': 'pending', 'data': None},
        'sql_generation': {'name': 'SQL Generation', 'status': 'pending', 'data': None},
        'execution': {'name': 'SQL Execution', 'status': 'pending', 'data': None},
        'summarization': {'name': 'Result Summarization', 'status': 'pending', 'data': None}
    }
    
    try:
        # STEP 1: Load context files (with improved error handling)
        context_files = load_application_context()
        if not context_files:
            print("❌ Error: Failed to load context files. Using fallback empty contexts.")
            context_files = {
                'business_rules': '',
                'database_schema': '',
                'example_queries': ''
            }
        
        # STEP 2: OpenAI Categorization - Updated prompt reference
        print(f"\nStep 1: OpenAI Categorization of query: '{test_query}'")
        
        # Get cached dates from previous context
        cached_dates = previous_context.get('date_filter') if previous_context else None
        
        # Create prompt with cached dates context
        categorization_result = create_categorization_prompt(cached_dates=cached_dates)
        categorization_prompt = categorization_result['prompt']
        
        # Log OpenAI request
        openai_logger.info(f"PROMPT TO OpenAI:\n{categorization_prompt}\nUSER QUERY: {test_query}")
        
        categorization_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": categorization_prompt},
                {"role": "user", "content": f"Analyze this query and return a JSON response: {test_query}"}
            ],
            response_format={"type": "json_object"}
        )
        
        # Log OpenAI response
        openai_logger.info(f"RESPONSE FROM OpenAI:\n{json.dumps(json.loads(categorization_response.choices[0].message.content), indent=2)}")
        openai_logger.info(f"Model: {categorization_response.model}")
        openai_logger.info(f"Tokens Used: {categorization_response.usage.total_tokens}")
        
        # Process OpenAI response
        raw_response = categorization_response.choices[0].message.content
        json_response = json.loads(raw_response)
        categorization = CategorizationResult(**json_response)
        
        # Store validated data
        flow_steps['categorization']['data'] = categorization.dict()
        flow_steps['categorization']['status'] = 'completed'
        query_type = categorization.request_type
        
        # Log successful categorization
        openai_logger.info(f"Valid categorization: {categorization}")
        
        # Check if this is an order_history query (most common category)
        is_order_history = query_type == 'order_history'
        
        # Create a context object for subsequent steps
        result_context = {
            'date_filter': None,
            'context': categorization_result.get('context', {}),
            'conversation_history': conversation_history
        }
        
        # Update date cache if new dates provided
        if categorization.start_date and categorization.end_date:
            date_filter_cache = {
                'start_date': categorization.start_date,
                'end_date': categorization.end_date
            }
            mock_session.date_filter_cache = date_filter_cache
            result_context['date_filter'] = date_filter_cache
            print(f"  Updated date cache: {categorization.start_date} to {categorization.end_date}")
        # Clear date cache if a new time period is mentioned but no specific dates provided
        elif categorization.time_period and categorization.time_period.lower() not in ['', 'none', 'no specific period', 'not specified']:
            # Clear the date cache and set it to None to force new date calculation
            mock_session.date_filter_cache = None
            result_context['date_filter'] = None
            print(f"  Cleared date cache due to new time period: {categorization.time_period}")
        elif mock_session.date_filter_cache:
            result_context['date_filter'] = mock_session.date_filter_cache
            print(f"  Using cached dates: {mock_session.date_filter_cache['start_date']} to {mock_session.date_filter_cache['end_date']}")
        
        # STEP 3: SQL Generation - Updated with proper error handling
        print(f"\nStep 2: SQL Generation for {query_type} query")
        
        print("\n>> DEBUG: Preparing to call Google Gemini...")
        
        try:
            # Get previous SQL query context (if available)
            base_sql_query = mock_session.get("last_sql_query", None)
            
            # Check if this is a follow-up query
            is_followup = is_followup_query(test_query, conversation_history)
            
            # Get cached dates from session
            cached_dates = mock_session.date_filter_cache
            
            # Get date context from our categorization result
            date_context_obj = categorization_result.get('context', {}).get('date_context', None)
            
            # Format date context string if available
            date_context_str = ""
            if cached_dates:
                date_context_str = f"""
                ACTIVE DATE FILTERS:
                - Start Date: {cached_dates['start_date'] if cached_dates else 'Not specified'}
                - End Date: {cached_dates['end_date'] if cached_dates else 'Not specified'}
                """
            elif categorization.time_period:
                # If we have a time period but no cached dates, include that as context
                date_context_str = f"""
                ACTIVE DATE FILTERS: 
                - Time Period: {categorization.time_period}
                - Cached dates have been cleared. Use appropriate date filters for this time period.
                """
            
            # Default execution control flag
            continue_to_execution = False
            
            # Path selection based on query type
            if is_order_history:
                print("  Using PATH 1: Enhanced Gemini prompt with full business context")
            elif query_type in ['update_price', 'disable_item', 'enable_item']:
                # PATH 2: For menu update operations, use specialized functions
                print(f"  Using PATH 2: Specialized functions for {query_type}")
                
                # Production-ready parameter handling
                item_name = flow_steps['categorization']['data']['item_name']
                if not item_name:
                    raise ValueError("Missing item_name for menu update operation")
                
                # Production SQL validation
                if query_type == 'update_price':
                    new_price = flow_steps['categorization']['data']['new_price']
                    if not isinstance(new_price, (int, float)) or new_price <= 0:
                        raise ValueError("Invalid price value")
                    
                    # Handle multiple location IDs for menu updates
                    if len(mock_session.selected_location_ids) > 1:
                        locations_str = ", ".join(map(str, mock_session.selected_location_ids))
                        sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                    else:
                        sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {mock_session.selected_location_id} RETURNING *"
                else:
                    state = 'false' if query_type == 'enable_item' else 'true'
                    
                    # Handle multiple location IDs for enabling/disabling items
                    if len(mock_session.selected_location_ids) > 1:
                        locations_str = ", ".join(map(str, mock_session.selected_location_ids))
                        sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                    else:
                        sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id = {mock_session.selected_location_id} RETURNING *"
                
                # Skip SQL generation for direct update operations
                flow_steps['sql_generation']['data'] = {'sql_query': sql_query}
                flow_steps['sql_generation']['status'] = 'completed'
                print(f"  Generated SQL: {sql_query}")
                
                # Skip to execution step - but don't exit the function
                mock_session["last_sql_query"] = sql_query
                
                # Continue to execution step without calling the SQL generator
                continue_to_execution = True
            else:
                print("  Using PATH 3: Standard SQL generation with context")
                continue_to_execution = False
                
            # Generate SQL only if not using direct SQL operations
            if not continue_to_execution:
                try:
                    # Get time period from categorization if available
                    time_period = categorization.time_period if hasattr(categorization, 'time_period') else None
                    
                    sql_query = call_sql_generator(
                        test_query,
                        context_files,
                        location_id=mock_session.selected_location_id,
                        previous_sql=base_sql_query,
                        conversation_history=conversation_history,
                        date_context=date_context_str,
                        time_period=time_period,
                        location_ids=mock_session.selected_location_ids
                    )
                    
                    # Store and display the generated SQL
                    mock_session["last_sql_query"] = sql_query
                    flow_steps['sql_generation']['data'] = {'sql_query': sql_query}
                    flow_steps['sql_generation']['status'] = 'completed'
                    
                    # Format SQL for display (one line, no extra spaces)
                    display_sql = sql_query.strip().replace('\n', ' ').replace('  ', ' ')
                    print(f"  Generated SQL: {display_sql}")

                except Exception as e:
                    print(f"  Error in SQL generation: {str(e)}")
                    flow_steps['sql_generation']['status'] = 'error'
                    flow_steps['sql_generation']['data'] = {'error': str(e)}
                    
                    # Create a context to return even if there's an error
                    error_context = {
                        'date_filter': mock_session.date_filter_cache,
                        'error': str(e),
                        'context': categorization_result.get('context', {}),
                        'conversation_history': conversation_history
                    }
                    
                    return {
                        'success': False, 
                        'error': f"SQL generation failed: {str(e)}",
                        'context': error_context
                    }
        except Exception as e:
            print(f"  Critical error in SQL generation: {str(e)}")
            flow_steps['sql_generation']['status'] = 'error'
            flow_steps['sql_generation']['data'] = {'error': str(e)}
            
            # Create a context to return even if there's a critical error
            error_context = {
                'date_filter': mock_session.date_filter_cache,
                'error': str(e),
                'context': categorization_result.get('context', {}),
                'conversation_history': conversation_history
            }
            
            return {
                'success': False,
                'error': str(e),
                'steps': flow_steps,
                'context': error_context
            }
        
        # STEP 4: SQL Execution - Enhanced with more robust error handling
        print("\nStep 3: SQL Execution")
        
        try:
            # IMPROVEMENT 3 - ROBUSTNESS: Execute SQL query with timeout and retries
            max_retries = 2
            execution_result = None
            
            for attempt in range(max_retries + 1):
                try:
                    execution_result = app.execute_menu_query(sql_query)
                    break
                except Exception as retry_error:
                    if attempt < max_retries:
                        print(f"  Retry {attempt+1}/{max_retries} after execution error")
                    else:
                        raise
            
            # Store execution result
            flow_steps['execution']['data'] = execution_result
            flow_steps['execution']['status'] = 'completed'
            
            # Process execution result
            if execution_result.get('success'):
                result_count = len(execution_result.get('results', []))
                if result_count > 0:
                    print(f"  Query returned {result_count} result(s)")
                    first_result = execution_result['results'][0]
                    # IMPROVEMENT 2 - READABILITY: Truncate large results for display
                    displayed_result = {k: v for k, v in first_result.items() if len(str(v)) < 50}
                    print(f"  First result: {displayed_result}")
                else:
                    print("  Query executed successfully, but returned no results")
            else:
                error_msg = execution_result.get('error', 'Unknown error')
                print(f"  SQL Execution Error: {error_msg}")
                
                # Continue with empty results for robustness
                execution_result = {'success': False, 'error': error_msg, 'results': []}
        except Exception as e:
            print(f"  Error executing SQL: {str(e)}")
            
            # Create a more descriptive error result
            execution_result = {
                'success': False, 
                'error': f"Execution error: {str(e)}", 
                'results': [],
                'query': sql_query
            }
            flow_steps['execution']['status'] = 'error'
            flow_steps['execution']['data'] = execution_result
        
        # STEP 5: Result Summarization - Updated prompt reference
        print("\nStep 4: Result Summarization")
        
        try:
            if execution_result and execution_result.get('results'):
                # Convert datetime objects to strings in the execution results
                for i, result in enumerate(execution_result['results']):
                    for key, value in result.items():
                        # Convert datetime objects to ISO format strings
                        if isinstance(value, datetime.datetime):
                            execution_result['results'][i][key] = value.isoformat()
                        # Also handle date objects (not just datetime objects)
                        elif isinstance(value, datetime.date):
                            execution_result['results'][i][key] = value.isoformat()
                
                # Get verbal response history from previous_context if available
                verbal_history = None
                if previous_context and 'verbal_response_history' in previous_context:
                    verbal_history = previous_context['verbal_response_history']
                
                # Use the specialized summarization prompt with verbal history
                summarization_prompt = create_summarization_prompt(
                    execution_result['results'],
                    test_query,
                    verbal_history
                )
                
                # Also keep the existing summary prompt for backward compatibility
                summary_prompt = create_summary_prompt(
                    test_query, 
                    sql_query, 
                    execution_result,
                    query_type=query_type,
                    conversation_history=conversation_history
                )
                
                # IMPROVEMENT 3 - ROBUSTNESS: Make OpenAI API call with retry logic
                max_retries = 2
                summary = None
                
                for attempt in range(max_retries + 1):
                    try:
                        # Get system prompt with business rules
                        system_prompt = create_system_prompt_with_business_rules()
                        
                        # Updated prompt to request both verbal and text answers with more concise verbal instructions
                        enhanced_summary_prompt = f"""
{summary_prompt}

IMPORTANT: Please provide TWO distinct responses:
1. VERBAL_ANSWER: Provide a CONCISE but natural-sounding response that will be spoken aloud. 
   - Keep it brief (2-3 conversational sentences)
   - Include key numbers and facts with a natural speaking cadence
   - You can use brief conversational elements like "We had" or "I found"
   - Avoid unnecessary elaboration, metaphors, or overly formal language
   - Focus on the most important information, but sound like a helpful colleague
   - No need for follow-up questions

2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your concise, natural-sounding response here]
TEXT_ANSWER: [Your detailed response here]
"""

                        # If we have a summarization prompt from the specialized function, use it for VERBAL_ANSWER
                        if 'summarization_prompt' in locals() and summarization_prompt:
                            enhanced_summary_prompt = f"""
{summary_prompt}

IMPORTANT: Please provide TWO distinct responses:
1. VERBAL_ANSWER: Provide a CONCISE but natural-sounding response that will be spoken aloud:
   - Keep it brief (2-3 conversational sentences)
   - Include key numbers and facts with a natural speaking cadence
   - You can use brief conversational elements like "We had" or "I found"
   - Avoid unnecessary elaboration, metaphors, or overly formal language
   - Focus on the most important information, but sound like a helpful colleague
   - No need for follow-up questions
   
   Reference information (use the core facts from this): 
   {summarization_prompt}

2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your concise, natural-sounding response here]
TEXT_ANSWER: [Your detailed response here]
"""

                        # Get persona if specified
                        persona_prompt = ""
                        if persona:
                            persona_prompt = get_persona_prompt(persona)
                            enhanced_summary_prompt = f"{enhanced_summary_prompt}\n\n{persona_prompt}"
                        
                        summarization_response = openai_client.chat.completions.create(
                            model="gpt-4o",  # Using smaller, faster model for summarization
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": enhanced_summary_prompt}
                            ],
                            temperature=0.2  # Lower temperature for more consistent responses
                        )
                        
                        # Extract the summary
                        raw_response = summarization_response.choices[0].message.content
                        
                        # Parse the verbal and text answers
                        verbal_answer = None
                        text_answer = None
                        
                        # Extract verbal answer
                        verbal_match = re.search(r"VERBAL_ANSWER:(.*?)(?=TEXT_ANSWER:|$)", raw_response, re.DOTALL)
                        if verbal_match:
                            verbal_answer = verbal_match.group(1).strip()
                        
                        # Extract text answer
                        text_match = re.search(r"TEXT_ANSWER:(.*?)$", raw_response, re.DOTALL)
                        if text_match:
                            text_answer = text_match.group(1).strip()
                        
                        # If parsing failed, use the entire response as both answers
                        if not verbal_answer and not text_answer:
                            verbal_answer = raw_response.strip()
                            text_answer = raw_response.strip()
                        
                        # Store both answers
                        flow_steps['summarization']['status'] = 'completed'
                        flow_steps['summarization']['data'] = {
                            'verbal_answer': verbal_answer,
                            'text_answer': text_answer,
                            'raw_response': raw_response,
                            'method': 'openai'
                        }
                        
                        # Use text answer as the primary summary for backward compatibility
                        summary = text_answer if text_answer else verbal_answer
                        break
                    except Exception as retry_error:
                        if attempt < max_retries:
                            print(f"  Retry {attempt+1}/{max_retries} after error: {str(retry_error)}")
                        else:
                            raise
                
                if not summary:
                    return {
                        'success': False,
                        'error': "No results to summarize",
                        'summary': "No data found for the query parameters",
                        'verbal_answer': "I'm sorry, I couldn't find any data matching your request.",
                        'text_answer': "No data found for the specified parameters. Please try a different query or time period."
                    }
            else:
                return {
                    'success': False,
                    'error': "No results to summarize",
                    'summary': "No data found for the query parameters",
                    'verbal_answer': "I'm sorry, I couldn't find any data matching your request.",
                    'text_answer': "No data found for the specified parameters. Please try a different query or time period."
                }
        except AttributeError as e:
            print(f"  Summarization error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'summary': "Could not generate summary due to data issues",
                'verbal_answer': "I'm sorry, but I couldn't process your request due to a technical issue.",
                'text_answer': "ERROR: Could not generate summary due to data issues. Please try a different query."
            }
        
        # STEP 6: Final Result Display
        print("\n>> FINAL RESULT")
        print(f"  Query: {test_query}")
        print(f"  Answer: {summary}")
        
        # IMPROVEMENT 2 - READABILITY: Enhanced flow summary with detailed status reporting
        print("\n>> FLOW SUMMARY")
        
        for step_id, step_data in flow_steps.items():
            status_symbol = {
                'completed': 'DONE',
                'pending': 'PENDING',
                'error': 'ERROR',
                'warning': 'WARNING'
            }.get(step_data['status'], '?')
            
            print(f"  {step_data['name']}: {status_symbol}")
        
        # Report any failures
        failed_steps = [step_data['name'] for step_id, step_data in flow_steps.items() 
                        if step_data['status'] in ['error', 'pending']]
        
        if failed_steps:
            print("\n>> STEPS WITH ISSUES:")
            for step in failed_steps:
                print(f"  • {step}")
        
        # Get the verbal and text answers from the flow steps if available
        verbal_answer = flow_steps.get('summarization', {}).get('data', {}).get('verbal_answer', summary)
        text_answer = flow_steps.get('summarization', {}).get('data', {}).get('text_answer', summary)
        
        # Display both answers if available
        if verbal_answer != text_answer:
            print("\n>> VERBAL ANSWER:")
            print(f"  {verbal_answer}")
            
            print("\n>> TEXT ANSWER:")
            print(f"  {text_answer}")
        
        # Speak the verbal answer if voice is enabled
        if voice and voice.initialized and voice.enabled and verbal_answer:
            print("\n🔊 Speaking response...")
            voice.speak(verbal_answer)
        
        # Update conversation history with this exchange
        conversation_history.append({
            'query': test_query,
            'sql': sql_query,
            'results': execution_result.get('results', []),
            'answer': summary,
            'verbal_answer': verbal_answer,
            'text_answer': text_answer
        })
        
        # Store context for potential follow-up queries
        query_context = {
            'previous_query': test_query,
            'previous_sql': sql_query,
            'date_filter': mock_session.date_filter_cache,  # Store current date filter
            'previous_results': execution_result.get('results', []),
            'previous_summary': summary,
            'previous_verbal_answer': verbal_answer,
            'previous_text_answer': text_answer,
            'conversation_history': conversation_history,
            'date_context': categorization_result.get('context', {}).get('date_context', None),  # Include date_context from categorization
            'verbal_history': conversation_history[-3:] if len(conversation_history) >= 3 else []
        }
        
        # Make sure the context includes all necessary fields from result_context if it exists
        if 'result_context' in locals():
            # Merge result_context into query_context
            for key, value in result_context.items():
                if key not in query_context or not query_context[key]:
                    query_context[key] = value
        
        # Update verbal response history
        query_context.setdefault('verbal_response_history', [])
        query_context['verbal_response_history'].append(verbal_answer)
        
        # Return final result with all steps and context
        return {
            'success': True, 
            'summary': summary,
            'query': test_query,
            'data': execution_result,
            'sql': sql_query,
            'steps': flow_steps,
            'context': query_context  # Return the context for subsequent queries
        }
    
    except Exception as e:
        print(f"\n>> CRITICAL ERROR IN FLOW: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'steps': flow_steps,
            'context': query_context if 'query_context' in locals() else {'error': str(e)}  # Ensure context exists
        }

# Helper function for SQL generation with parameter name conversion
def call_sql_generator(query, context_files, location_id, previous_sql=None, conversation_history=None, date_context=None, time_period=None, location_ids=None):
    """
    Wrapper to handle parameter name differences between imported functions and local usage
    
    Args:
        query: User query text
        context_files: Dictionary of context files
        location_id: Primary location ID (for backward compatibility)
        previous_sql: Previously executed SQL query
        conversation_history: List of previous interactions
        date_context: Date context information
        time_period: Time period mentioned in the query
        location_ids: List of selected location IDs (takes precedence over location_id)
    """
    # Import functions with proper parameter handling
    from prompts.google_gemini_prompt import create_gemini_prompt as external_gemini_prompt
    
    try:
        # First create the enhanced prompt with the correct parameter name
        prompt = external_gemini_prompt(
            query, 
            context_files, 
            location_id, 
            conversation_history=conversation_history,
            previous_sql=previous_sql,
            date_context=date_context  # This matches the parameter name in prompts/google_gemini_prompt.py
        )
        
        # Enhance prompt with additional time period context if available
        if time_period:
            # Check if the original query contains the phrase "in the last year"
            contains_in_the_last_year = "in the last year" in query.lower() or "in last year" in query.lower()
            
            if time_period == 'last_year' and not contains_in_the_last_year:
                # Specifically handle "last year" to reference 2024 data (calendar year)
                prompt += f"\n\nIMPORTANT TIME CONTEXT: The query refers to 'last year' as a specific calendar year (2024). " \
                         f"Filter data where EXTRACT(YEAR FROM (updated_at - INTERVAL '7 hours')) = 2024."
            elif time_period == 'last_year' and contains_in_the_last_year:
                # Handle "in the last year" to mean the last 365 days
                prompt += f"\n\nIMPORTANT TIME CONTEXT: The query refers to 'in the last year' which means the last 365 days. " \
                         f"Filter data where (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '365 days'."
            else:
                prompt += f"\n\nIMPORTANT TIME CONTEXT: The query refers to the time period: {time_period}. Use the appropriate SQL date filters."
        
        # Add location context for multiple locations if provided
        if location_ids and len(location_ids) > 1:
            locations_str = ", ".join(map(str, location_ids))
            prompt += f"\n\nIMPORTANT LOCATION CONTEXT: The query should filter for multiple locations with IDs: {locations_str}. " \
                      f"Use IN clause for location_id filter instead of equality (location_id IN ({locations_str}))."
        
        # Then generate the SQL using the standard function but with enhanced prompt
        from utils.create_sql_statement import generate_sql_with_custom_prompt
        
        # Use the specific location_id or first ID from location_ids if provided
        final_location_id = location_id
        if location_ids and len(location_ids) > 0:
            final_location_id = location_ids[0]
        
        print(f"Generating SQL with location_id: {final_location_id}")
        return generate_sql_with_custom_prompt(prompt, final_location_id)
    except Exception as e:
        raise Exception(f"SQL generation error: {str(e)}")

# Helper function to extract dates
def extract_date_from_sql(sql: str) -> str:
    """Extract date filter from SQL query"""
    date_match = re.search(r"::date\s*=\s*'(\d{4}-\d{2}-\d{2})'", sql, re.IGNORECASE)
    return date_match.group(1) if date_match else 'CURRENT_DATE'

# Update the prompt creation function
def create_categorization_prompt(cached_dates=None):
    """Create an optimized categorization prompt for OpenAI
    
    Args:
        cached_dates: Optional previously cached date context
        
    Returns:
        Dict containing the prompt string and context information
    """
    from prompts.openai_categorization_prompt import create_categorization_prompt as external_create_prompt
    
    # Get the base prompt from external source
    prompt_data = external_create_prompt(cached_dates=cached_dates)
    
    # Add explicit JSON instruction to satisfy OpenAI's requirements
    prompt_data['prompt'] = f"{prompt_data['prompt']}\n\nIMPORTANT: Respond using valid JSON format."
    
    return prompt_data

# ElevenLabs Voice Setup Functions
def setup_elevenlabs() -> bool:
    """Setup ElevenLabs and return availability status"""
    global ELEVENLABS_AVAILABLE, USE_NEW_API
    
    try:
        print("Attempting to import ElevenLabs...")
        
        # Try multiple approaches for different package versions
        try:
            # First check if we can import without error
            import elevenlabs
            # Disable new API approach due to ArrayJsonSchemaProperty issue
            raise ImportError("Skipping client API due to known ArrayJsonSchemaProperty issue")
        except ImportError as e:
            print(f"Error with new API approach: {str(e)}")
            print("Falling back to legacy approach...")
            # Older version with direct imports
            try:
                from elevenlabs import generate, play, set_api_key, voices, Voice, VoiceSettings
                if os.getenv("ELEVENLABS_API_KEY"):
                    set_api_key(os.getenv("ELEVENLABS_API_KEY"))
                USE_NEW_API = False
                ELEVENLABS_AVAILABLE = True
                print("✓ ElevenLabs package (older version) loaded successfully with legacy approach")
                return True
            except Exception as legacy_error:
                print(f"Legacy approach also failed: {str(legacy_error)}")
                raise
        ELEVENLABS_AVAILABLE = True
        return True
    except Exception as e:
        print(f"Complete ElevenLabs initialization error: {str(e)}")
        ELEVENLABS_AVAILABLE = False
        USE_NEW_API = False
        print("To enable voice output, run: pip install elevenlabs")
        return False

def setup_audio_playback() -> bool:
    """Setup audio playback and return availability status"""
    global PYGAME_AVAILABLE, pygame
    
    try:
        import pygame as pg
        pygame = pg  # Assign to global variable
        pygame.mixer.init()
        PYGAME_AVAILABLE = True
        print("✓ Pygame audio initialized successfully")
        return True
    except (ImportError, Exception) as e:
        PYGAME_AVAILABLE = False
        print(f"Pygame error: {str(e)}")
        return False

class ElevenLabsVoice:
    """Class to handle ElevenLabs text-to-speech functionality with improved error handling"""
    
    def __init__(self, default_voice_id: str = "UgBBYS2sOqTuMpoF3BR0", persona: str = None):
        self.enabled = True
        # Use persona-specific voice ID if provided, otherwise use default
        self.voice_id = get_persona_voice_id(persona) if persona else default_voice_id
        self.available_voices = []
        self.initialized = False
        self.client = None
        self.voice_name = "Unknown"
        self.persona = persona
        self.last_spoken_text = None  # Track the last spoken text to prevent duplicates
        self.max_verbal_length = 100  # Maximum number of words for verbal responses
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize ElevenLabs with better error handling"""
        if not ELEVENLABS_AVAILABLE:
            print("ElevenLabs is not available. Voice functionality will be disabled.")
            self.initialized = False
            return
            
        try:
            # Get API key from environment variable
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                print("⚠️ ElevenLabs API key not found in environment variables")
                self.initialized = False
                return
                
            if USE_NEW_API:
                # This path is unlikely to be used due to the ArrayJsonSchemaProperty issue
                try:
                    # Create a client with the API key using the correct import
                    from elevenlabs.client import ElevenLabs
                    self.client = ElevenLabs(api_key=api_key)
                    print("✓ Created ElevenLabs client with API key")
                    
                    # Get available voices
                    response = self.client.voices.get_all()
                    self.available_voices = response.voices
                    print(f"✓ Found {len(self.available_voices)} voices")
                    
                    # Default voice is already set, but verify it exists in available voices
                    voice_exists = any(voice.voice_id == self.voice_id for voice in self.available_voices)
                    if not voice_exists:
                        print(f"⚠️ Specified voice ID {self.voice_id} not found, defaulting to first available voice")
                        if self.available_voices:
                            self.voice_id = self.available_voices[0].voice_id
                            
                    self.initialized = True
                except Exception as e:
                    print(f"Error initializing ElevenLabs client: {str(e)}")
                    self.initialized = False
            else:
                # Legacy API approach
                try:
                    import elevenlabs
                    
                    # Set API key
                    elevenlabs.set_api_key(api_key)
                    
                    # Get available voices
                    try:
                        self.available_voices = elevenlabs.voices()
                        print(f"✓ Found {len(self.available_voices)} voices")
                    except Exception as voice_error:
                        print(f"⚠️ Error getting voices: {str(voice_error)}")
                        self.available_voices = []
                    
                    # Check if specified voice exists
                    voice_exists = any(getattr(voice, 'voice_id', None) == self.voice_id for voice in self.available_voices)
                    if not voice_exists and self.available_voices:
                        print(f"⚠️ Specified voice ID {self.voice_id} not found, defaulting to first available voice")
                        self.voice_id = getattr(self.available_voices[0], 'voice_id', self.voice_id)
                    
                    self.initialized = True
                except Exception as e:
                    print(f"Error initializing ElevenLabs with legacy API: {str(e)}")
                    self.initialized = False
        except Exception as e:
            print(f"Unexpected error initializing ElevenLabs: {str(e)}")
            self.initialized = False
    
    def list_voices(self) -> str:
        """List available voices with details"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        if not self.available_voices:
            return "No voices available"
        
        voice_list = []
        current_voice_marker = " ← current"
        
        for i, voice in enumerate(self.available_voices):
            marker = current_voice_marker if voice.voice_id == self.voice_id else ""
            voice_list.append(f"{i+1}. {voice.name} (ID: {voice.voice_id}){marker}")
        
        return "\n".join(voice_list)
    
    def set_voice(self, voice_index_or_id: Union[str, int]) -> str:
        """Set the voice by index (1-based) or by voice ID with improved feedback"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        if not self.available_voices:
            return "No voices available"
            
        # Store old voice ID for comparison
        old_voice_id = self.voice_id
        
        # Check if input is a voice ID
        for voice in self.available_voices:
            if voice.voice_id == voice_index_or_id:
                self.voice_id = voice.voice_id
                self.voice_name = voice.name
                return f"Voice set to {voice.name} (ID: {voice.voice_id})"
        
        # If not a voice ID, try as an index
        try:
            index = int(voice_index_or_id) - 1
            if 0 <= index < len(self.available_voices):
                self.voice_id = self.available_voices[index].voice_id
                self.voice_name = self.available_voices[index].name
                return f"Voice set to {self.voice_name} (ID: {self.voice_id})"
            else:
                return f"Invalid voice index. Choose between 1 and {len(self.available_voices)}"
        except ValueError:
            return "Please provide a valid number or voice ID"
    
    def toggle(self) -> str:
        """Toggle voice on/off with status feedback"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Voice {status} ({self.voice_name})"
    
    def ensure_concise(self, text: str) -> str:
        """Ensure verbal responses are concise by limiting length or summarizing.
        
        Args:
            text (str): Original verbal response text
            
        Returns:
            str: Concise version of the response
        """
        if not text:
            return text
            
        # Count words
        words = text.split()
        if len(words) <= self.max_verbal_length:
            return text
            
        # Simple truncation approach - keep first part with ellipsis
        concise_text = " ".join(words[:self.max_verbal_length]) + "..."
        print(f"Verbal response truncated from {len(words)} to {self.max_verbal_length} words for speech")
        return concise_text
    
    def speak(self, text: str) -> bool:
        """Convert text to speech and play it with better error handling"""
        if not self.initialized or not self.enabled or not text:
            return False
            
        # Make the verbal response concise for speech
        concise_text = self.ensure_concise(text)
            
        # Skip if this exact text was just spoken to prevent duplicates
        if concise_text == self.last_spoken_text:
            print("🔊 Skipping duplicate text-to-speech")
            return True
            
        self.last_spoken_text = concise_text  # Store this text as the last spoken
        
        try:
            audio = None
            
            # Generate audio
            if USE_NEW_API and self.client:
                # New API with client
                try:
                    print(f"Generating speech using voice ID: {self.voice_id}")
                    audio_stream = self.client.text_to_speech.convert(
                        text=concise_text,
                        voice_id=self.voice_id,
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128"
                    )
                    
                    # Check if result is a generator/stream and convert to bytes if needed
                    if not isinstance(audio_stream, bytes):
                        all_audio = bytearray()
                        for chunk in audio_stream:
                            if isinstance(chunk, bytes):
                                all_audio.extend(chunk)
                        audio = bytes(all_audio)
                    else:
                        audio = audio_stream
                    
                    if audio:
                        print(f"✓ Generated audio of size: {len(audio)} bytes")
                    else:
                        print("⚠️ No audio generated")
                        return False
                except Exception as e:
                    print(f"⚠️ Error generating speech with new API: {str(e)}")
                    return False
            else:
                # Legacy API with direct function calls
                try:
                    import elevenlabs
                    print(f"Generating speech using voice ID: {self.voice_id}")
                    
                    # Check if we need to pass voice_id or Voice object
                    try:
                        # First try the simple approach with just voice_id
                        audio = elevenlabs.generate(
                            text=concise_text,
                            voice=self.voice_id,
                            model="eleven_multilingual_v2"
                        )
                    except Exception as generate_error:
                        print(f"Simple voice generation failed: {str(generate_error)}")
                        # Try with Voice object if available
                        voice_obj = None
                        for voice in self.available_voices:
                            if getattr(voice, 'voice_id', None) == self.voice_id:
                                voice_obj = voice
                                break
                                
                        if voice_obj:
                            audio = elevenlabs.generate(
                                text=concise_text,
                                voice=voice_obj,
                                model="eleven_multilingual_v2"
                            )
                        else:
                            raise ValueError(f"Voice with ID {self.voice_id} not found")
                            
                    if audio:
                        print(f"✓ Generated audio of size: {len(audio)} bytes")
                    else:
                        print("⚠️ No audio generated")
                        return False
                except Exception as e:
                    print(f"⚠️ Error generating speech with legacy API: {str(e)}")
                    return False
                    
            # Play audio if available
            if audio:
                # Play using pygame
                if PYGAME_AVAILABLE:
                    try:
                        from io import BytesIO
                        import pygame
                        
                        # Initialize pygame mixer if not already done
                        if not pygame.mixer.get_init():
                            pygame.mixer.init(frequency=44100)
                            
                        # Load and play
                        audio_file = BytesIO(audio)
                        pygame.mixer.music.load(audio_file)
                        pygame.mixer.music.play()
                        
                        print("🔊 Playing audio with pygame")
                        return True
                    except Exception as e:
                        print(f"⚠️ Error playing audio with pygame: {str(e)}")
                
                # Alternative: try to use the elevenlabs play function as fallback
                try:
                    if not USE_NEW_API:  # Legacy API has play function
                        import elevenlabs
                        elevenlabs.play(audio)
                        print("🔊 Playing audio with elevenlabs.play")
                        return True
                except Exception as e:
                    print(f"⚠️ Error playing audio with elevenlabs.play: {str(e)}")
                    
                # Last resort: save to file and try to play with system default
                try:
                    import tempfile
                    import os
                    
                    # Save to temp file
                    fd, temp_path = tempfile.mkstemp(suffix='.mp3')
                    with open(temp_path, 'wb') as f:
                        f.write(audio)
                    
                    # Try to play with system default
                    if os.name == 'nt':  # Windows
                        os.system(f'start {temp_path}')
                    elif os.name == 'posix':  # macOS/Linux
                        os.system(f'open {temp_path}' if os.uname().sysname == 'Darwin' else f'xdg-open {temp_path}')
                    
                    print(f"🔊 Playing audio with system default player from {temp_path}")
                    return True
                except Exception as e:
                    print(f"⚠️ Error playing audio with system default: {str(e)}")
            
            return False
        except Exception as e:
            print(f"⚠️ Unexpected error in speak method: {str(e)}")
            return False

    def update_persona(self, persona_name: str) -> str:
        """Update the voice based on a new persona.
        
        Args:
            persona_name (str): The name of the persona to use.
            
        Returns:
            str: Status message about the voice change.
        """
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        # Get the voice ID for the new persona
        new_voice_id = get_persona_voice_id(persona_name)
        self.persona = persona_name
        
        # Set the voice to the persona-specific voice
        return self.set_voice(new_voice_id)

def initialize_voice_dependencies():
    """Initialize voice dependencies and return overall status"""
    elevenlabs_available = setup_elevenlabs()
    audio_playback_available = setup_audio_playback()
    
    return {
        "elevenlabs": elevenlabs_available,
        "audio_playback": audio_playback_available
    }

def run_interactive_chat():
    """
    Run an interactive chat session with the AI in the terminal.
    This function creates a conversation where the user inputs queries and the AI responds.
    """
    # Initialize session state and history
    mock_session = MockSessionState()
    conversation_history = []
    
    # Initialize voice components
    voice = None
    if ELEVENLABS_AVAILABLE:
        voice = ElevenLabsVoice()
    
    # Selected persona (default to casual)
    selected_persona = "casual"
    
    # Display welcome header
    print("\n" + "="*50)
    print("🍽️ Swoop AI")
    print("="*50)
    
    # Display available personas
    print("\n🎭 Available Personas:")
    for idx, persona in enumerate(AVAILABLE_PERSONAS, 1):
        info = get_persona_info(persona)
        description = info["prompt"].split("\n")[1].strip() if info and "prompt" in info else persona
        if persona == selected_persona:
            print(f"  {idx}. {persona.title()} ← current")
        else:
            print(f"  {idx}. {persona.title()}")
    print("\nTo change persona, type: !persona [name or number]")
    
    # Display voice options if available
    if ELEVENLABS_AVAILABLE and voice and voice.initialized:
        print("\n🔊 Voice Commands:")
        print("  !voice list - List available voices")
        print("  !voice set [number or ID] - Set voice by number or voice ID")
        print("  !voice toggle - Turn voice on/off")
        print("  !voice info - Show current voice information")
        
        # Display current voice info
        print(f"\n🎤 Current voice: {voice.voice_name} (ID: {voice.voice_id})")
        
        # Ensure voice is enabled if available
        if voice.enabled == False:
            voice.toggle()
    
    print("Type 'exit', 'quit', or Ctrl+C to end the session.")
    print("="*50 + "\n")
    
    # Display sample questions
    sample_questions = [
        "What are the most popular menu items this week?",
        "How many orders did we receive yesterday?",
        "What's the total revenue for this month?",
        "Who placed the largest order this week?",
        "Which staff member processed the most orders today?"
    ]
    
    print("📝 Sample questions you can ask:")
    for i, question in enumerate(sample_questions, 1):
        print(f"  {i}. {question}")
    print()
    
    # Welcome message
    welcome_message = "Hello! I'm your Swoop AI. How can I help you today?"
    print("\n🤖 Assistant: " + welcome_message)
    
    # Speak welcome message if voice is enabled
    if voice and voice.initialized and voice.enabled:
        print("🔊 Speaking...")
        voice.speak(welcome_message)
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            user_query = input("\n💬 You: ").strip()
            
            # Check for exit command
            if user_query.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                goodbye_message = "Thank you for chatting with me. Have a great day!"
                print("\n🤖 Assistant: " + goodbye_message)
                if voice and voice.initialized and voice.enabled:
                    voice.speak(goodbye_message)
                break
            
            # Check for voice commands
            if user_query.startswith("!voice") and voice:
                result = handle_voice_command(voice, user_query)
                print(f"\n🔊 {result}")
                continue
                
            # Check for persona change command
            if user_query.startswith("!persona"):
                parts = user_query.split(maxsplit=1)
                if len(parts) > 1:
                    persona_input = parts[1].strip().lower()
                    
                    # Check if input is a number
                    try:
                        persona_idx = int(persona_input) - 1
                        if 0 <= persona_idx < len(AVAILABLE_PERSONAS):
                            selected_persona = AVAILABLE_PERSONAS[persona_idx]
                            print(f"\n🎭 Persona changed to: {selected_persona.title()}")
                            
                            # Update voice if needed
                            if voice and voice.initialized:
                                voice_id = get_persona_voice_id(selected_persona)
                                if voice_id:
                                    voice.set_voice(voice_id)
                                    print(f"Voice updated for {selected_persona} persona")
                        else:
                            print(f"\n⚠️ Invalid persona number. Please choose between 1 and {len(AVAILABLE_PERSONAS)}")
                    except ValueError:
                        # Not a number, try as a name
                        if persona_input in AVAILABLE_PERSONAS:
                            selected_persona = persona_input
                            print(f"\n🎭 Persona changed to: {selected_persona.title()}")
                            
                            # Update voice if needed
                            if voice and voice.initialized:
                                voice_id = get_persona_voice_id(selected_persona)
                                if voice_id:
                                    voice.set_voice(voice_id)
                                    print(f"Voice updated for {selected_persona} persona")
                        else:
                            print(f"\n⚠️ Unknown persona. Available personas: {', '.join(AVAILABLE_PERSONAS)}")
                else:
                    print(f"\n⚠️ Please specify a persona name or number. Example: !persona professional")
                continue
            
            # Skip empty queries
            if not user_query:
                print("Please type something.")
                continue
            
            # Process the query and get response
            print("\n⏳ Checking ...")
            result = demonstrate_complete_flow(
                user_query,
                previous_context=mock_session.context,
                persona=selected_persona,
                voice=voice
            )
            
            # Store the context for follow-up queries
            if 'context' in result:
                mock_session.context = result['context']
            
            # Get the response to display
            if result.get('success'):
                response = result.get('summary', "No response generated")
            else:
                response = f"Error processing query: {result.get('error', 'Unknown error')}"
            
            # Display the response
            print("\n🤖 Assistant: " + response)
            
            # Speak response if voice is enabled
            # Note: demonstrate_complete_flow already speaks if voice is enabled, 
            # so we don't need to speak again here
            
            # Save to conversation history
            conversation_history.append((user_query, response))
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n⚠️ An error occurred: {str(e)}")
            print("Let's try again with a different question.")

def handle_voice_command(voice, command):
    """
    Handle voice commands with improved command parsing
    
    Args:
        voice: The ElevenLabsVoice instance
        command: The command string starting with !voice
        
    Returns:
        str: Command result message
    """
    if not command.startswith("!voice"):
        return "Not a valid voice command"
        
    parts = command.split()
    if len(parts) < 2:
        return "Invalid voice command format"
    
    subcommand = parts[1].lower()
    
    # List all voices
    if subcommand == "list":
        return voice.list_voices()
    
    # Set voice by index or ID
    elif subcommand == "set" and len(parts) > 2:
        voice_id_or_index = ' '.join(parts[2:]) if len(parts) > 3 else parts[2]
        return voice.set_voice(voice_id_or_index)
    
    # Toggle voice on/off
    elif subcommand == "toggle":
        return voice.toggle()
    
    # Show voice info
    elif subcommand == "info":
        voice_name = voice.voice_name or "Unknown"
        return (
            f"Current voice: {voice_name}\n"
            f"Voice ID: {voice.voice_id}\n"
            f"Voice enabled: {voice.enabled}\n"
            f"Available voices: {len(voice.available_voices)}"
        )
    
    # Invalid command
    else:
        return "Invalid voice command. Use !voice list, !voice set [number or ID], !voice toggle, or !voice info"

def run_streamlit_app():
    """Run the application with a Streamlit interface"""
    try:
        import streamlit.components.v1 as components
    except ImportError:
        print("Streamlit is not installed. Please install it with: pip install streamlit")
        return
    
    # Page config is now set at the module level
    # Don't call st.set_page_config() here anymore
    
    # Initialize session state for various settings if not already set
    if 'voice_enabled' not in st.session_state:
        st.session_state.voice_enabled = True
    
    if 'voice_instance' not in st.session_state:
        st.session_state.voice_instance = None
    
    if 'persona' not in st.session_state:
        st.session_state.persona = "casual"
        
    if 'context' not in st.session_state:
        st.session_state.context = None
    
    # Initialize chat history if not exists
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
    # Initialize query input field state and previous_query for tracking
    if 'query' not in st.session_state:
        st.session_state.query = ""
        
    if 'previous_query' not in st.session_state:
        st.session_state.previous_query = ""
        
    # Initialize location settings
    if 'selected_location_id' not in st.session_state:
        st.session_state.selected_location_id = 62  # Default to Idle Hour
        
    if 'selected_location_ids' not in st.session_state:
        st.session_state.selected_location_ids = [62]  # Default to Idle Hour
        
    if 'selected_club' not in st.session_state:
        st.session_state.selected_club = "Idle Hour Country Club"  # Default club
        
    # Define available locations organized by club
    club_locations = {
        "Idle Hour Country Club": {
            "locations": [62],
            "default": 62
        },
        "Pinetree Country Club": {
            "locations": [61, 66],
            "default": 61
        }
    }
    
    # Flat mapping of location IDs to names
    location_options = {
        62: "Idle Hour Country Club",
        61: "Pinetree Country Club (Location 61)",
        66: "Pinetree Country Club (Location 66)"
    }
    
    # Function to clear input field after submission
    def clear_query_input():
        st.session_state.query = ""
        
    # Function to process the query
    def process_query():
        if st.session_state.query and st.session_state.query != st.session_state.previous_query:
            query = st.session_state.query
            st.session_state.previous_query = query
            
            # Add user message to chat history
            st.session_state.chat_history.append((query, None))  # Add placeholder for assistant response
            
            # Create a MockSessionState with the current selected location(s)
            mock_session = MockSessionState()
            mock_session.selected_location_id = st.session_state.selected_location_id
            mock_session.selected_location_ids = st.session_state.selected_location_ids
            mock_session.selected_club = st.session_state.selected_club
            
            with st.spinner(f"Checking ..."):
                # Process the query using the demonstrate_complete_flow function
                result = demonstrate_complete_flow(
                    query, 
                    previous_context=st.session_state.context,
                    persona=st.session_state.persona,
                    voice=st.session_state.voice_instance,
                    mock_session=mock_session
                )
                
                # Store the context for follow-up queries
                if 'context' in result:
                    st.session_state.context = result['context']
                
                # Get the appropriate answer
                if result.get('success'):
                    # Get the verbal and text answers
                    text_answer = result.get('context', {}).get('previous_text_answer', 
                                  result.get('summary', "No response generated"))
                    
                    # Update the last chat history entry with the assistant's response
                    if st.session_state.chat_history:
                        st.session_state.chat_history[-1] = (query, text_answer)
                else:
                    error_msg = f"I'm sorry, I couldn't process that query. Error: {result.get('error', 'Unknown error')}"
                    
                    # Update the last chat history entry with the error message
                    if st.session_state.chat_history:
                        st.session_state.chat_history[-1] = (query, error_msg)
            
            # Clear query after processing by setting session state before next render
            clear_query_input()
    
    # Sidebar for settings
    st.sidebar.title("")
    
    # Location selection in sidebar
    with st.sidebar.expander("Location Settings", expanded=True):
        st.write("👥 Select Country Club")
        st.caption("Choose a country club to view data from. If a club has multiple locations, you can view data from a specific location or all locations.")
        
        # Club selection dropdown (primary)
        club_names = list(club_locations.keys())
        selected_club = st.selectbox(
            "Country Club",
            options=club_names,
            index=club_names.index(st.session_state.selected_club) if st.session_state.selected_club in club_names else 0
        )
        
        # Update club selection in session state
        if selected_club != st.session_state.selected_club:
            st.session_state.selected_club = selected_club
            # Set default location for this club
            default_location_id = club_locations[selected_club]["default"]
            st.session_state.selected_location_id = default_location_id
            
            # If this is Pinetree, default to showing all locations
            if selected_club == "Pinetree Country Club":
                st.session_state.selected_location_ids = club_locations[selected_club]["locations"]
            else:
                st.session_state.selected_location_ids = [default_location_id]
        
        # Show secondary location selector only for clubs with multiple locations
        locations_for_club = club_locations[selected_club]["locations"]
        if len(locations_for_club) > 1:
            st.write(f"#### Select {selected_club} Location")
            
            # Create options for the location dropdown
            location_options_list = [("all", f"Show All {selected_club} Locations")]
            for loc_id in locations_for_club:
                # Extract just the location identifier from the full name
                if "(" in location_options[loc_id]:
                    location_label = location_options[loc_id].split("(")[1].replace(")", "").strip()
                else:
                    location_label = "Primary Location"
                location_options_list.append((str(loc_id), location_label))
            
            # Determine the current selection
            current_selection = "all"
            if len(st.session_state.selected_location_ids) == 1 and st.session_state.selected_location_ids[0] in locations_for_club:
                current_selection = str(st.session_state.selected_location_ids[0])
            
            # Create the secondary dropdown
            location_selection = st.radio(
                f"Select Location", 
                options=[opt[0] for opt in location_options_list],
                format_func=lambda x: next((opt[1] for opt in location_options_list if opt[0] == x), x),
                index=[opt[0] for opt in location_options_list].index(current_selection) if current_selection in [opt[0] for opt in location_options_list] else 0
            )
            
            # Update location IDs based on selection
            if location_selection == "all":
                # Select all locations for this club
                st.session_state.selected_location_ids = locations_for_club
                # Use the first location as the primary
                st.session_state.selected_location_id = locations_for_club[0]
            else:
                # Select just the specific location
                location_id = int(location_selection)
                st.session_state.selected_location_ids = [location_id]
                st.session_state.selected_location_id = location_id
        
        # Show active location filter information
        st.write("##### Active Location Filter:")
        if len(st.session_state.selected_location_ids) == 1:
            location_id = st.session_state.selected_location_ids[0]
            st.write(f"**{location_options[location_id]}**")
        else:
            st.write(f"**All {selected_club} Locations**")
            
    # Persona selection - with updated options
    with st.sidebar.expander("Persona Settings", expanded=True):
        selected_persona = st.radio(
            "Select assistant persona",
            options=AVAILABLE_PERSONAS,
            index=AVAILABLE_PERSONAS.index(st.session_state.persona) if st.session_state.persona in AVAILABLE_PERSONAS else 0,
            format_func=lambda x: x.title()
        )
        
        # Display persona description
        persona_info = get_persona_info(selected_persona)
        if persona_info and "prompt" in persona_info:
            persona_description = persona_info["prompt"].split("\n")[1].strip()
            st.caption(f"**{persona_description}**")
        
        if selected_persona != st.session_state.persona:
            previous_persona = st.session_state.persona
            st.session_state.persona = selected_persona
            
            # Update voice if already initialized
            if st.session_state.voice_instance and st.session_state.voice_instance.initialized:
                result = st.session_state.voice_instance.update_persona(selected_persona)
                st.success(f"Persona set to {selected_persona} with voice update: {result}")
            else:
                # Reset voice instance to use the new persona voice
                st.session_state.voice_instance = None
                st.success(f"Persona set to {selected_persona}")
    
    # Initialize voice if not already done
    if st.session_state.voice_instance is None:
        # Initialize voice dependencies
        with st.sidebar.expander("Voice Settings", expanded=True):
            st.write("🔊 Setting up voice capabilities...")
            voice_status = initialize_voice_dependencies()
            
            if voice_status["elevenlabs"] and voice_status["audio_playback"]:
                # Initialize voice with the selected persona
                voice = ElevenLabsVoice(persona=st.session_state.persona)
                st.session_state.voice_instance = voice
                
                # Add voice control options
                st.session_state.voice_enabled = st.checkbox(
                    "Enable voice responses", 
                    value=st.session_state.voice_enabled
                )
                
                # Update the voice instance's enabled state
                voice.enabled = st.session_state.voice_enabled
                
                # Voice selection
                if voice.available_voices:
                    voice_options = [f"{v.name}" for v in voice.available_voices]
                    
                    # Find current voice name in list
                    current_index = 0
                    for i, v in enumerate(voice.available_voices):
                        if v.voice_id == voice.voice_id:
                            current_index = i
                            break
                    
                    selected_voice = st.selectbox(
                        "Select voice",
                        options=voice_options,
                        index=current_index
                    )
                    
                    # Set the voice based on selection
                    for i, v in enumerate(voice.available_voices):
                        if v.name == selected_voice:
                            if v.voice_id != voice.voice_id:
                                voice.set_voice(v.voice_id)
                                st.success(f"Voice set to {v.name}")
                            break
                else:
                    st.warning("No voices available")
            else:
                st.warning("Voice output unavailable. Install required packages: elevenlabs and pygame")
                st.session_state.voice_instance = None
    else:
        # Voice is already initialized, just show controls
        with st.sidebar.expander("Voice Settings", expanded=False):
            voice = st.session_state.voice_instance
            
            # Toggle voice
            voice_enabled = st.checkbox(
                "Enable voice responses", 
                value=st.session_state.voice_enabled
            )
            
            if voice_enabled != st.session_state.voice_enabled:
                st.session_state.voice_enabled = voice_enabled
                voice.enabled = voice_enabled
                st.success(f"Voice {'enabled' if voice_enabled else 'disabled'}")
            
            # Voice selection if available
            if voice and voice.available_voices:
                voice_options = [f"{v.name}" for v in voice.available_voices]
                
                # Find current voice name in list
                current_index = 0
                for i, v in enumerate(voice.available_voices):
                    if v.voice_id == voice.voice_id:
                        current_index = i
                        break
                
                selected_voice = st.selectbox(
                    "Select voice",
                    options=voice_options,
                    index=current_index
                )
                
                # Set the voice based on selection
                for i, v in enumerate(voice.available_voices):
                    if v.name == selected_voice:
                        if v.voice_id != voice.voice_id:
                            voice.set_voice(v.voice_id)
                            st.success(f"Voice set to {v.name}")
                        break
    
    # Main area
    # Replace the standard title with a custom header using the Swoop logo and new title
    header_col1, header_col2 = st.columns([1, 5])
    with header_col1:
        # Using raw SVG content directly - this is the best and most maintainable approach
        # The SVG is directly embedded in the HTML, making it crisp at any resolution
        swoop_logo_svg = """
        <svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 278.91 239.64" width="80" height="80">
          <defs>
            <style>
              .cls-1, .cls-2 {
                fill: #FFFFFF; /* Changed from blue to white */
              }
              .cls-1 {
                fill-rule: evenodd;
              }
            </style>
          </defs>
          <g>
            <path class="cls-1" d="M288,65l-5.57-2.08c-36.59-13.68-42.36-15.33-43.86-15.53a40.71,40.71,0,0,0-70.51,4.28c-.85-.06-1.7-.11-2.56-.13h-.94c-.56,0-1.11,0-1.66,0a58.92,58.92,0,0,0-22.8,5A58.11,58.11,0,0,0,118.45,72.7L9.09,178.42l95.22-5.11-1.73,95.33L207.09,151.29a59.63,59.63,0,0,0,15.68-38.1c0-.11,0-.23,0-.34,0-.6,0-1.2,0-1.8s0-1,0-1.45c0-.24,0-.49,0-.74,0-.85-.07-1.69-.14-2.54a41,41,0,0,0,21-24.82,15.56,15.56,0,0,0,3.57-1ZM205.38,75.33c1,1.15,1.89,2.36,2.77,3.6.17.26.36.5.54.76.8,1.18,1.55,2.4,2.27,3.65l.67,1.19c.63,1.15,1.21,2.34,1.75,3.54a55.71,55.71,0,0,1,4.46,15.5A36.24,36.24,0,0,1,170.79,56.5,54.25,54.25,0,0,1,205,74.93Zm12.92,37.43v.11A54.82,54.82,0,0,1,185.56,161a54,54,0,0,1-19.88,4.54l-56.79,3,1-52.69v-.12a54.56,54.56,0,0,1,54-59.78c.78,0,1.57.07,2.35.11a40.68,40.68,0,0,0,52.1,52.1l0,.7c0,.29,0,.58,0,.87s0,.77,0,1.15C218.32,111.52,218.32,112.14,218.3,112.76ZM20.87,173.29,110.18,87c-.33.74-.7,1.46-1,2.23a58.88,58.88,0,0,0-3.83,26.87l-.95,52.76Zm87.94-.22L165.88,170a58.56,58.56,0,0,0,21.48-4.91c.82-.36,1.63-.74,2.42-1.13L107.3,256.6Zm113.31-71.51a59.51,59.51,0,0,0-4.22-14.47c-.14-.33-.33-.64-.48-1-.55-1.21-1.13-2.4-1.76-3.57-.29-.52-.58-1-.88-1.55-.74-1.29-1.51-2.55-2.35-3.78-.23-.34-.47-.66-.71-1-.91-1.28-1.86-2.53-2.87-3.74l-.51-.58q-1.69-2-3.57-3.81l-.1-.09a58.34,58.34,0,0,0-19.18-12.38,58.93,58.93,0,0,0-12.67-3.44,36.29,36.29,0,1,1,49.3,49.38Zm22.6-25a39.79,39.79,0,0,0-3.11-23.74c4.45,1.45,13.91,4.79,33.67,12.15L245.54,76.36C245.28,76.47,245,76.52,244.72,76.61Z" transform="translate(-9.09 -29)"/>
            <ellipse class="cls-2" cx="150.18" cy="84.88" rx="16.44" ry="16.53"/>
          </g>
        </svg>
        """
        
        # Inject the SVG directly into the page
        st.markdown(swoop_logo_svg, unsafe_allow_html=True)
    
    with header_col2:
        # Match the styling with the blue used in the logo
        st.markdown("""
            <h1 style='margin-top: 15px; color: white; font-weight: 600;'>
                Swoop AI
            </h1>
        """, unsafe_allow_html=True)
    
    st.write("Ask any question about your restaurant data. I'll analyze your query and provide insights.")
    
    # Add guidance for better queries
    with st.expander("Tips for better results", expanded=False):
        st.markdown("""
        ### How to get the best responses:
        
        - **Be specific about time periods**: Use clear date formats like "last week", "Jan 5 to Jan 10", or "yesterday"
        - **Specify metrics clearly**: Ask for specific metrics like "total sales", "average order value", or "customer count"
        - **For menu items**: Use exact item names when asking about specific dishes
        - **Follow-up questions**: You can ask follow-up questions referring to previous results
        - **Avoid**: Vague queries, complex hypotheticals, or questions outside restaurant data

        **Examples of good queries:**
        - "What were our top 5 selling items yesterday?"
        - "Show me total revenue for March 2025 broken down by day"
        - "How many customers placed orders between 5pm and 7pm last Friday?"
        - "What's the price of the Deluxe Burger?"
        """)
    
    # Display current location selection
    if len(st.session_state.selected_location_ids) == 1:
        location_id = st.session_state.selected_location_ids[0]
        location_name = location_options[location_id]
        st.info(f"📍 Currently querying data for: **{location_name}**")
    else:
        # Must be multiple Pinetree locations
        st.info(f"📍 Currently querying data for: **All {st.session_state.selected_club} Locations**")
    
    # Input area - moved to top for better chat experience
    query = st.text_input(
        "Your query:", 
        key="query", 
        placeholder="E.g., What were our top-selling items last week?",
        on_change=process_query
    )
    submit_button = st.button("Ask", on_click=process_query)
    
    # Chat container for better styling
    chat_container = st.container()
    
    # Display chat history in the container
    with chat_container:
        if not st.session_state.chat_history:
            st.info("Ask a question to start the conversation!")
        else:
            # Create a more sophisticated chat-like interface
            for i, (question, answer) in enumerate(st.session_state.chat_history):
                # User message - right aligned with avatar
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: flex-end;">
                            <div style="background-color: #4D774E; padding: 10px 15px; 
                                border-radius: 15px 0 15px 15px; max-width: 80%; 
                                margin-bottom: 10px; text-align: right; color: white; 
                                font-weight: 500; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                {question}
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        """
                        <div style="display: flex; justify-content: flex-end;">
                            <div style="background-color: #E9ECEF; border-radius: 50%; 
                                width: 35px; height: 35px; text-align: center; 
                                line-height: 35px; font-weight: bold; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                👤
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Only show assistant response if we have one
                if answer:
                    # Assistant message - left aligned with avatar
                    col1, col2 = st.columns([1, 6])
                    with col1:
                        st.markdown(
                            """
                            <div style="display: flex; justify-content: flex-start;">
                                <div style="background-color: #E9ECEF; border-radius: 50%; 
                                    width: 35px; height: 35px; text-align: center; 
                                    line-height: 35px; font-weight: bold; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                    🤖
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with col2:
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-start;">
                                <div style="background-color: #0D6EFD; padding: 10px 15px; 
                                    border-radius: 0 15px 15px 15px; max-width: 80%; 
                                    margin-bottom: 20px; color: white; font-weight: 500;
                                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                {answer}
                            </div>
                        </div>
                        """, 
                            unsafe_allow_html=True
                        )
            
            # Add some space at the bottom for better visuals
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run the Swoop AI")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive terminal mode")
    args = parser.parse_args()
    
    if args.interactive:
        # Run in interactive mode
        print("\n" + "="*50)
        print("💬 Starting Interactive Chat...")
        print("="*50)
        
        # Initialize dependencies
        voice_status = initialize_voice_dependencies()
        
        # Run the interactive chat
        try:
            run_interactive_chat()
        except KeyboardInterrupt:
            print("\n\nScript interrupted by user. Exiting...")
        except Exception as e:
            print(f"\n\nError running interactive chat: {str(e)}")
            import traceback
            traceback.print_exc()
            
        print("\nScript completed. Goodbye!")
    else:
        # Run the Streamlit app, only if streamlit is available
        if st is not None:
            run_streamlit_app()
        else:
            print("Streamlit is not installed. Please install it with: pip install streamlit") 