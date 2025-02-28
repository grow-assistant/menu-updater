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
import datetime
import re
from pydantic import BaseModel, Field, model_validator, ValidationError
from typing import Optional

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
from prompts.personas import get_persona_prompt

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
        self.selected_location_id = 62
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
    @model_validator(mode='after')
    def check_dates(cls, values):
        start = values.start_date
        end = values.end_date
        
        if start and end:
            if start > end:
                raise ValueError("start_date must be before end_date")
                
        # Only modify dates if BOTH are missing
        if not start and not end:
            # Let calling code handle fallback to cached dates
            return values
            
        # If only one date provided, use it for both
        if start and not end:
            values.end_date = start
        elif end and not start:
            values.start_date = end
            
        return values

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

def demonstrate_complete_flow(test_query=None, previous_context=None, persona=None):
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
        
    Returns:
        dict: Flow results containing success status, summary, and step details
    """
    # IMPROVEMENT 1 - EFFICIENCY: Optimized flow logic with better caching and reuse
    print("\n>> EXECUTING ENHANCED FLOW")
    
    # Initialize client and session
    openai_client, _ = get_clients()
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
            date_context_str = f"""
            ACTIVE DATE FILTERS:
            - Start Date: {cached_dates['start_date'] if cached_dates else 'Not specified'}
            - End Date: {cached_dates['end_date'] if cached_dates else 'Not specified'}
            """ if cached_dates else ""

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
                    sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {mock_session.selected_location_id} RETURNING *"
                else:
                    state = 'false' if query_type == 'enable_item' else 'true'
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
                    sql_query = call_sql_generator(
                        test_query,
                        context_files,
                        location_id=mock_session.selected_location_id,
                        previous_sql=base_sql_query,
                        conversation_history=conversation_history,
                        date_context=date_context_str
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
                        
                        # Updated prompt to request both verbal and text answers
                        enhanced_summary_prompt = f"""
{summary_prompt}

IMPORTANT: Please provide TWO distinct responses:
1. VERBAL_ANSWER: A conversational, natural-sounding response that could be read aloud. Keep this concise and friendly.
2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your conversational response here]
TEXT_ANSWER: [Your detailed response here]
"""

                        # If we have a summarization prompt from the specialized function, use it for VERBAL_ANSWER
                        if 'summarization_prompt' in locals() and summarization_prompt:
                            enhanced_summary_prompt = f"""
{summary_prompt}

IMPORTANT: Please provide TWO distinct responses:
1. VERBAL_ANSWER: Use the following specialized prompt for the verbal answer:
{summarization_prompt}

2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your conversational response following the specialized prompt]
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
def call_sql_generator(query, context_files, location_id, previous_sql=None, conversation_history=None, date_context=None):
    """
    Wrapper to handle parameter name differences between imported functions and local usage
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
        
        # Then generate the SQL using the standard function but with enhanced prompt
        from utils.create_sql_statement import generate_sql_with_custom_prompt
        return generate_sql_with_custom_prompt(prompt, location_id)
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
if __name__ == "__main__":
    # Get path1 queries
    initial_query, followup_queries = get_path_for_testing("path1")
    
    # Set persona to clubhouse_legend for all queries
    persona = 'casual'

    # Run initial query
    print(f"\n===== RUNNING INITIAL QUERY WITH {persona.upper()} PERSONA =====")
    result = demonstrate_complete_flow(initial_query, persona=persona)
    
    # Ensure context exists to prevent KeyError
    if 'context' not in result:
        result['context'] = {'error': 'Context not available'}
    
    # Store context for follow-up queries
    context = result['context']

    # Run first followup query
    if followup_queries:
        print(f"\n===== RUNNING FOLLOWUP QUERY WITH {persona.upper()} PERSONA =====")
        result = demonstrate_complete_flow(followup_queries[0], previous_context=context, persona=persona)
        # Update context for next query
        context = result['context']
    
    # Run second followup query
    if len(followup_queries) > 1:
        print(f"\n===== RUNNING FOLLOWUP QUERY WITH {persona.upper()} PERSONA =====")
        result = demonstrate_complete_flow(followup_queries[1], previous_context=context, persona=persona)
        # Update context for next query
        context = result['context']
    
    # Run any remaining followup queries
    for i, query in enumerate(followup_queries[2:], 3):
        print(f"\n===== RUNNING FOLLOWUP QUERY {i} WITH {persona.upper()} PERSONA =====")
        result = demonstrate_complete_flow(query, previous_context=context, persona=persona)
        # Update context for next query
        context = result['context'] 