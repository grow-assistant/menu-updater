"""
LangChain integration for the Swoop AI application.
This module provides classes and functions to integrate LangChain functionality
into the existing Swoop AI application.
"""

# Standard library imports
import os
import re
import json
import logging
import datetime
from typing import List, Dict, Any, Optional

# Third-party imports
from dotenv import load_dotenv
import pytz
import streamlit as st

# Store current session ID
current_session_id = None

# Configure logging
def setup_logging(session_id=None):
    """Configure the shared logger for all components"""
    if not session_id:
        session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    log_filename = f"logs/app_log_{session_id}.log"
    
    # Configure root logger to write to the consolidated log file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Keep console output
        ]
    )
    
    # Get the ai_menu_updater logger that's used by all prompt modules
    logger = logging.getLogger("ai_menu_updater")
    logger.info(f"=== New Session Started at {session_id} ===")
    logger.info(f"All logs consolidated in {log_filename}")
    
    return logger

# Set up logging
logger = setup_logging()

# Load environment variables
load_dotenv()

# LangChain imports for version 0.0.150
from langchain.chains import ConversationChain
from langchain.agents import AgentType, initialize_agent, Tool, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Timezone Constants
USER_TIMEZONE = pytz.timezone("America/Phoenix")  # Arizona (no DST)
CUSTOMER_DEFAULT_TIMEZONE = pytz.timezone("America/New_York")  # EST
DB_TIMEZONE = pytz.timezone("UTC")

def convert_to_user_timezone(dt, target_tz=USER_TIMEZONE):
    """Convert UTC datetime to user's timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DB_TIMEZONE)
    return dt.astimezone(target_tz)

def get_location_timezone(location_id):
    """Get timezone for a specific location, defaulting to EST if not found"""
    # This would normally query the database, but for testing we'll hardcode
    location_timezones = {
        62: CUSTOMER_DEFAULT_TIMEZONE,  # Idle Hour Country Club
        # Add other locations as needed
    }
    return location_timezones.get(location_id, CUSTOMER_DEFAULT_TIMEZONE)

def adjust_query_timezone(query, location_id):
    """Adjust SQL query to handle timezone conversion"""
    location_tz = get_location_timezone(location_id)

    # Replace any date/time comparisons with timezone-aware versions
    if "updated_at" in query:
        # First convert CURRENT_DATE to user timezone (Arizona)
        current_date_in_user_tz = datetime.datetime.now(USER_TIMEZONE).date()

        # Handle different date patterns
        if "CURRENT_DATE" in query:
            # Convert current date to location timezone for comparison
            query = query.replace(
                "CURRENT_DATE",
                f"(CURRENT_DATE AT TIME ZONE 'UTC' AT TIME ZONE '{USER_TIMEZONE.zone}')",
            )

        # Handle the updated_at conversion
        query = query.replace(
            "(o.updated_at - INTERVAL '7 hours')",
            f"(o.updated_at AT TIME ZONE 'UTC' AT TIME ZONE '{location_tz.zone}')",
        )

    return query

def convert_user_date_to_location_tz(date_str, location_id):
    """Convert a date string from user timezone to location timezone"""
    try:
        # Parse the date in user's timezone (Arizona)
        if isinstance(date_str, str):
            if date_str.lower() == "today":
                user_date = datetime.datetime.now(USER_TIMEZONE)
            elif date_str.lower() == "yesterday":
                user_date = datetime.datetime.now(USER_TIMEZONE) - datetime.timedelta(days=1)
            else:
                # Try to parse the date string
                user_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                user_date = USER_TIMEZONE.localize(user_date)
        else:
            # If it's already a datetime
            user_date = USER_TIMEZONE.localize(date_str)

        # Convert to location timezone
        location_tz = get_location_timezone(location_id)
        location_date = user_date.astimezone(location_tz)

        return location_date.strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error converting date: {e}")
        return date_str

# Function to get clients (from integrate_app.py)
def get_clients():
    """Get the OpenAI and xAI clients"""
    try:
        return get_openai_client(), get_xai_config()
    except Exception as e:
        # Fallback if client functions fail
        logger.warning(f"Unable to initialize clients: {str(e)}")
        return None, None

# Function to detect follow-up queries
def is_followup_query(
    user_query: str, conversation_history: Optional[List[Dict]] = None
) -> bool:
    """Determine if a query is a follow-up to previous conversation with more sophisticated detection.

    Args:
        user_query (str): The current user query
        conversation_history (list, optional): Previous exchanges in the conversation

    Returns:
        bool: True if the query appears to be a follow-up, False otherwise
    """
    # Normalize the query
    query_lower = user_query.lower().strip()

    # 1. Check for explicit follow-up indicators
    explicit_indicators = [
        "those", "these", "that", "it", "they", "them", "their", "previous",
        "last", "again", "more", "further", "additional", "also", "too",
        "as well", "what about", "how about", "tell me more", "can you elaborate",
        "show me", "what else", "and", "what if",
    ]

    # Check if query starts with certain phrases
    starting_phrases = [
        "what about", "how about", "what if", "and what", "and how",
        "can you also", "could you also", "show me", "tell me more",
    ]

    # Check if query is very short (likely a follow-up)
    is_short_query = len(query_lower.split()) <= 3

    # 2. Check for pronouns without clear referents
    has_pronoun_without_referent = False
    pronouns = ["it", "they", "them", "those", "these", "that", "this"]
    for pronoun in pronouns:
        # Check if pronoun exists as a standalone word
        has_pronoun = f" {pronoun} " in f" {query_lower} "
        no_referent = not any(
            noun in query_lower
            for noun in ["order", "revenue", "sales", "item", "menu", "customer"]
        )
        if has_pronoun and no_referent:
            has_pronoun_without_referent = True
            break

    # 3. Check for incomplete queries that would need context
    incomplete_indicators = [
        query_lower.startswith("what about"),
        query_lower.startswith("how about"),
        query_lower.startswith("and "),
        query_lower.startswith("but "),
        query_lower.startswith("also "),
        query_lower.startswith("what if"),
        query_lower == "why",
        query_lower == "how",
        query_lower == "when",
        is_short_query and not any(x in query_lower for x in ["show", "list", "get", "find"]),
    ]

    # 4. Context-based detection (if conversation history is available)
    context_based = False
    if conversation_history and len(conversation_history) > 0:
        # Get the most recent query for comparison
        last_query = ""
        if "query" in conversation_history[-1]:
            last_query = conversation_history[-1].get("query", "").lower()

        # Check for shared key terms between queries
        last_query_terms = set(last_query.split())
        current_query_terms = set(query_lower.split())

        # Remove common stop words
        stop_words = {
            "the", "a", "an", "in", "on", "at", "by", "for", 
            "with", "about", "from", "to", "of",
        }
        last_query_terms = last_query_terms - stop_words
        current_query_terms = current_query_terms - stop_words

        # If the current query has significantly fewer terms and shares some with the previous query
        if len(current_query_terms) < len(last_query_terms) * 0.7:
            common_terms = current_query_terms.intersection(last_query_terms)
            if len(common_terms) > 0:
                context_based = True
                
    # Combine all detection methods
    return (
        any(indicator in query_lower.split() for indicator in explicit_indicators)
        or any(query_lower.startswith(phrase) for phrase in starting_phrases)
        or has_pronoun_without_referent
        or any(incomplete_indicators)
        or context_based
    )

# OpenAI client function from app.py
def get_openai_client():
    """Get OpenAI client with compatibility for different API versions"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Handle both old and new OpenAI package versions
    try:
        # For OpenAI >= 1.0.0
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        # For OpenAI < 1.0.0
        import openai
        openai.api_key = api_key
        
        # Create compatible wrapper for old API
        class OpenAICompatWrapper:
            def __init__(self, api_key=None):
                self.api_key = api_key
                
            def chat(self):
                class ChatCompletions:
                    @staticmethod
                    def create(*args, **kwargs):
                        return openai.ChatCompletion.create(*args, **kwargs)
                return ChatCompletions()
                
            def completions(self):
                return openai
        
        return OpenAICompatWrapper(api_key=api_key)

# xAI config function from app.py  
def get_xai_config():
    """Get configuration for xAI API"""
    return {
        "XAI_TOKEN": os.getenv("XAI_TOKEN"),
        "XAI_API_URL": os.getenv("XAI_API_URL"),
        "XAI_MODEL": os.getenv("XAI_MODEL", "grok-2-1212"),
    }

# Function to load application context (from integrate_app.py)
def load_application_context():
    """Load all application context files and configuration in one place

    Returns:
        dict: A dictionary containing all application context including
              business rules, database schema, and example queries
    """
    try:
        # Import all business rules from both system and business-specific modules
        try:
            from prompts.system_rules import (
                ORDER_STATUS,
                RATING_SIGNIFICANCE,
                ORDER_TYPES,
                QUERY_RULES,
            )
            from prompts.business_rules import (
                get_business_context,
                BUSINESS_METRICS,
                TIME_PERIOD_GUIDANCE,
                DEFAULT_LOCATION_ID,
            )
            
            # Get the combined business context
            business_context = get_business_context()
        except ImportError:
            logger.warning("Could not import business rules, using empty values")
            business_context = {}
            
        # Load database schema
        try:
            with open("prompts/database_schema.md", "r", encoding="utf-8") as f:
                database_schema = f.read()
        except FileNotFoundError:
            logger.warning("Database schema file not found, using empty value")
            database_schema = ""
            
        # Load example queries from prompts module
        try:
            from prompts import EXAMPLE_QUERIES
        except ImportError:
            logger.warning("Example queries not found, using empty list")
            EXAMPLE_QUERIES = []

        # Create an integrated context object with all business rules
        return {
            "business_rules": business_context,
            "database_schema": database_schema,
            "example_queries": EXAMPLE_QUERIES,
        }
    except Exception as e:
        logger.error(f"Error loading application context: {str(e)}")
        return None

# Function to create categorization prompt (from integrate_app.py)
def create_categorization_prompt(cached_dates=None):
    """Create an optimized categorization prompt for OpenAI

    Args:
        cached_dates: Optional previously cached date context

    Returns:
        Dict containing the prompt string and context information
    """
    try:
        # Try to import from external source first
        from prompts.openai_categorization_prompt import create_categorization_prompt as external_create_prompt
        
        # Get the base prompt from external source
        prompt_data = external_create_prompt(cached_dates=cached_dates)
        
        # Add explicit JSON instruction to satisfy OpenAI's requirements
        prompt_data["prompt"] = (
            f"{prompt_data['prompt']}\n\nIMPORTANT: Respond using valid JSON format."
        )
        
        return prompt_data
        
    except ImportError:
        # Fallback implementation if the import fails
        logger.warning("External categorization prompt not available, using fallback")
        
        # Create basic prompt data structure
        prompt = (
            "Analyze the following user query and categorize it according to the given schema. "
            "Extract any relevant dates, items, or other entities mentioned:\n\n"
            "USER QUERY: {query}\n\n"
            "RESPOND WITH VALID JSON ONLY using this schema: {\n"
            '  "request_type": "order_history" | "query_menu" | "update_price" | "disable_item" | "enable_item",\n'
            '  "time_period": "today" | "yesterday" | "this_week" | "last_week" | "this_month" | "last_month" | null,\n'
            '  "item_name": <extracted item name> | null,\n'
            '  "start_date": <YYYY-MM-DD> | null,\n'
            '  "end_date": <YYYY-MM-DD> | null\n'
            "}\n\n"
            "IMPORTANT: Respond using valid JSON format."
        )
        
        # Add date context if provided
        context = {}
        if cached_dates:
            context["cached_dates"] = cached_dates
            
        return {"prompt": prompt, "context": context}

# Function to call SQL generator (from integrate_app.py)
def call_sql_generator(
    query,
    context_files,
    location_id,
    previous_sql=None,
    conversation_history=None,
    date_context=None,
    time_period=None,
    location_ids=None,
):
    """
    Call SQL generator to create SQL from user query
    
    Args:
        query: User query text
        context_files: Dictionary of context files
        location_id: Primary location ID (for backward compatibility)
        previous_sql: Previously executed SQL query
        conversation_history: List of previous interactions
        date_context: Date context information
        time_period: Time period mentioned in the query
        location_ids: List of selected location IDs (takes precedence over location_id)
        
    Returns:
        str: Generated SQL query
    """
    try:
        # Try to import the external function
        try:
            from prompts.google_gemini_prompt import create_gemini_prompt as external_gemini_prompt
            from utils.create_sql_statement import generate_sql_with_custom_prompt
            
            # First create the enhanced prompt with the correct parameter name
            prompt = external_gemini_prompt(
                query,
                context_files,
                location_id,
                conversation_history=conversation_history,
                previous_sql=previous_sql,
                date_context=date_context,
            )
            
            # Enhance prompt with additional time period context if available
            if time_period:
                # Check if the original query contains the phrase "in the last year"
                contains_in_the_last_year = (
                    "in the last year" in query.lower() or "in last year" in query.lower()
                )

                if time_period == "last_year" and not contains_in_the_last_year:
                    # Specifically handle "last year" to reference 2024 data (calendar year)
                    prompt += (
                        f"\n\nIMPORTANT TIME CONTEXT: The query refers to 'last year' as a specific calendar year (2024). "
                        f"Filter data where EXTRACT(YEAR FROM (updated_at - INTERVAL '7 hours')) = 2024."
                    )
                elif time_period == "last_year" and contains_in_the_last_year:
                    # Handle "in the last year" to mean the last 365 days
                    prompt += (
                        f"\n\nIMPORTANT TIME CONTEXT: The query refers to 'in the last year' which means the last 365 days. "
                        f"Filter data where (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '365 days'."
                    )
                else:
                    prompt += f"\n\nIMPORTANT TIME CONTEXT: The query refers to the time period: {time_period}. Use the appropriate SQL date filters."

            # Add location context for multiple locations if provided
            if location_ids and len(location_ids) > 1:
                locations_str = ", ".join(map(str, location_ids))
                prompt += (
                    f"\n\nIMPORTANT LOCATION CONTEXT: The query should filter for multiple locations with IDs: {locations_str}. "
                    f"Use IN clause for location_id filter instead of equality (location_id IN ({locations_str}))."
                )

            # Use the specific location_id or first ID from location_ids if provided
            final_location_id = location_id
            if location_ids and len(location_ids) > 0:
                final_location_id = location_ids[0]

            logger.info(f"Generating SQL with location_id: {final_location_id}")
            return generate_sql_with_custom_prompt(prompt, final_location_id)
            
        except ImportError:
            # Fallback if external functions are not available
            logger.warning("External SQL generation functions not available")
            return f"SELECT * FROM orders WHERE location_id = {location_id} AND status = 7 LIMIT 10;"
            
    except Exception as e:
        logger.error(f"SQL generation error: {str(e)}")
        raise Exception(f"SQL generation error: {str(e)}")

# Add this new DateTimeEncoder class after the imports
class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

# Function to create a summary prompt (from utils/prompt_templates.py)
def create_summary_prompt(
    user_query: str,
    sql_query: str,
    result: Dict[str, Any],
    query_type: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None,
) -> str:
    """Generate an optimized prompt for OpenAI summarization with conversation history

    Args:
        user_query (str): The original user query
        sql_query (str): The executed SQL query
        result (dict): The database result dictionary
        query_type (str, optional): The type of query (order_history, query_menu, etc.)
        conversation_history (list, optional): Previous exchanges in the conversation

    Returns:
        str: The optimized prompt for summarization
    """
    # Format SQL query for better readability
    formatted_sql = sql_query.strip().replace("\n", " ").replace("  ", " ")

    # Extract query type from result if not provided
    if not query_type and "function_call" in result:
        query_type = result.get("function_call", {}).get("name", "unknown")

    # Add query-specific context based on query type
    type_specific_instructions = {
        "order_history": "Present order counts, revenue figures, and trends with proper formatting. "
        "Use dollar signs for monetary values and include percent changes for trends.",
        "query_performance": "Highlight key performance metrics, compare to benchmarks when available, "
        "and provide actionable business insights.",
        "query_menu": "Structure menu information clearly, listing items with their prices "
        "and availability status in an organized way.",
        "query_ratings": "Present rating metrics with context (e.g., 'above average', 'concerning') "
        "and suggest possible actions based on feedback.",
        "update_price": "Confirm the exact price change with both old and new values clearly stated.",
        "disable_item": "Confirm the item has been disabled and explain the impact "
        "(no longer available to customers).",
        "enable_item": "Confirm the item has been re-enabled and is now available to customers again.",
    }

    type_guidance = type_specific_instructions.get(
        query_type, "Provide a clear, direct answer to the user's question."
    )
    
    # Determine if we have empty results to provide better context
    results = result.get("results", [])
    results_count = len(results)
    result_context = ""
    if results_count == 0:
        result_context = (
            "The query returned no results, which typically means no data matches "
            "the specified criteria for the given time period or filters."
        )
    
    # Limit the number of results to prevent token overflow
    MAX_RESULTS = 20
    if results_count > MAX_RESULTS:
        limited_results = results[:MAX_RESULTS]
        result_context += f"\nNOTE: Showing only the first {MAX_RESULTS} of {results_count} total results."
    else:
        limited_results = results
        
    # Use the custom encoder to handle datetime objects
    results_json = json.dumps(limited_results, indent=2, cls=DateTimeEncoder)
    
    # Further truncate if the JSON string is still too large
    MAX_JSON_CHARS = 8000
    if len(results_json) > MAX_JSON_CHARS:
        results_json = results_json[:MAX_JSON_CHARS] + f"\n... (truncated, {len(results_json)} total characters)"

    # Add conversation context for follow-up queries
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        # Extract the last 2-3 exchanges to provide context
        recent_exchanges = (
            conversation_history[-3:]
            if len(conversation_history) >= 3
            else conversation_history
        )
        conversation_context = "CONVERSATION HISTORY:\n"
        for i, exchange in enumerate(recent_exchanges):
            if "query" in exchange and "answer" in exchange:
                # Truncate long answers in conversation history
                answer = exchange['answer']
                if len(answer) > 300:
                    answer = answer[:300] + "... (truncated)"
                conversation_context += f"User: {exchange['query']}\nAssistant: {answer}\n\n"

    # Check if this is a follow-up query using the proper function
    is_followup = is_followup_query(user_query, conversation_history)

    followup_guidance = ""
    if is_followup:
        followup_guidance = (
            "This appears to be a follow-up question. Connect your answer to the previous context. "
            "Reference specific details from previous exchanges when relevant. "
            "Maintain continuity in your explanation style and terminology."
        )

    # Build optimized prompt with enhanced context and guidance
    return (
        f"USER QUERY: '{user_query}'\n\n"
        f"{conversation_context}\n"
        f"SQL QUERY: {formatted_sql}\n\n"
        f"QUERY TYPE: {query_type}\n\n"
        f"DATABASE RESULTS: {results_json}\n\n"
        f"RESULT CONTEXT: {result_context}\n\n"
        f"BUSINESS CONTEXT:\n"
        f"- Order statuses: 0=Open, 1=Pending, 2=Confirmed, 3=In Progress, 4=Ready, 5=In Transit, "
        f"6=Cancelled, 7=Completed, 8=Refunded\n"
        f"- Order types: 1=Delivery, 2=Pickup, 3=Dine-In\n"
        f"- Revenue values are in USD\n"
        f"- Ratings are on a scale of 1-5, with 5 being highest\n\n"
        f"SPECIFIC GUIDANCE FOR {query_type.upper()}: {type_guidance}\n\n"
        f"{followup_guidance}\n\n"
        f"SUMMARY INSTRUCTIONS:\n"
        f"1. Provide a clear, direct answer to the user's question\n"
        f"2. Include relevant metrics with proper formatting ($ for money, % for percentages)\n"
        f"3. If no results were found, explain what that means in business terms\n"
        f"4. Use natural, conversational language with a friendly, helpful tone\n"
        f"5. Be specific about the time period mentioned in the query\n"
        f"6. Keep the response concise but informative\n"
    )

# Function to create system prompt with business rules (from utils/prompt_templates.py)
def create_system_prompt_with_business_rules() -> str:
    """Create a system prompt that includes business rules for the summarization step

    Returns:
        str: System prompt with business rules context
    """
    try:
        # First try: import directly from prompts.business_rules
        try:
            logger.info("Attempting to import business rules modules")
            from prompts.system_rules import ORDER_STATUS, RATING_SIGNIFICANCE, ORDER_FILTERS
            
            business_context = {
                "order_status": ORDER_STATUS,
                "rating_significance": RATING_SIGNIFICANCE,
                "order_filters": ORDER_FILTERS,
            }
            logger.info("Successfully imported business rules from prompts.system_rules")
        except ImportError:
            # Second try: check if there's a business_rules.py file we can import
            import importlib.util
            import os
            
            # Construct absolute path to business_rules.py if available
            rules_path = os.path.join(os.getcwd(), "prompts", "business_rules.py")
            if os.path.exists(rules_path):
                logger.info(f"Found business_rules.py at {rules_path}")
                try:
                    spec = importlib.util.spec_from_file_location("business_rules", rules_path)
                    br_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(br_module)
                    
                    # Try to get key elements from the module
                    business_context = {}
                    
                    if hasattr(br_module, "ORDER_STATUS"):
                        business_context["order_status"] = br_module.ORDER_STATUS
                    
                    if hasattr(br_module, "RATING_SIGNIFICANCE"):
                        business_context["rating_significance"] = br_module.RATING_SIGNIFICANCE
                    
                    if hasattr(br_module, "ORDER_FILTERS"):
                        business_context["order_filters"] = br_module.ORDER_FILTERS
                    
                    logger.info("Successfully loaded business rules from file")
                except Exception as e:
                    logger.warning(f"Error loading business rules from file: {str(e)}")
                    raise ImportError("Failed to load business rules from file")
            else:
                logger.warning("business_rules.py not found in prompts directory")
                raise ImportError("business_rules.py not found")
            
        # If we get here, we have successfully loaded business_context
    except ImportError:
        # Fallback business context if import fails
        logger.warning("Could not import business rules, using comprehensive fallback values")
        business_context = {
            "order_status": {
                "0": "Open",
                "1": "Pending", 
                "2": "Confirmed",
                "3": "In Progress",
                "4": "Ready",
                "5": "In Transit",
                "6": "Cancelled",
                "7": "Completed", 
                "8": "Refunded",
                "9": "Archived"
            },
            "rating_significance": {
                "5": "Excellent - Very Satisfied",
                "4": "Good - Satisfied",
                "3": "Average - Neutral",
                "2": "Poor - Unsatisfied",
                "1": "Very Poor - Very Unsatisfied"
            },
            "order_filters": {
                "status": "Use status=7 for completed orders",
                "location_id": "Always filter by the current location_id",
                "time_period": "Use appropriate date filters for the requested time period"
            }
        }

    # Enhanced system prompt with business rules and conversational guidelines
    return (
        "You are a helpful restaurant analytics assistant that translates database results "
        "into natural language answers. "
        "Your goal is to provide clear, actionable insights from restaurant order data. "
        f"Use these business rules for context: {json.dumps(business_context, indent=2)}\n\n"
        "CONVERSATIONAL GUIDELINES:\n"
        "1. Use a friendly, professional tone that balances expertise with approachability\n"
        "2. Begin responses with a direct answer to the question, then provide supporting details\n"
        "3. Use natural transitions between ideas and maintain a conversational flow\n"
        "4. Highlight important metrics or insights with bold formatting (**like this**)\n"
        "5. For follow-up questions, explicitly reference previous context\n"
        "6. When appropriate, end with a subtle suggestion for what the user might want to know next\n"
        "7. Keep responses concise but complete - prioritize clarity over verbosity\n"
        "8. Use bullet points or numbered lists for multiple data points\n"
        "9. Format currency values with dollar signs and commas ($1,234.56)\n"
        "10. When discussing ratings, include their significance (e.g., '5.0 - Very Satisfied')\n"
    )

# Process query results function from app.py
def process_query_results(
    query_result: Dict[str, Any], user_question: str, openai_client, xai_client
) -> str:
    """
    Processes SQL query results and returns a formatted plain-language summary.
    Uses LLM to generate the summary (including total orders and notable insights).
    Detailed order information is handled separately (in a table).
    """
    if query_result["success"]:
        try:
            results = query_result["results"]

            # DIRECTLY USE SQL RESULT VALUE
            count_value = (
                results[0]["count"] if results and "count" in results[0] else len(results)
            )

            # Build prompt with actual database value
            prompt = (
                f"The SQL query for '{user_question}' returned {count_value} completed orders. "
                "Provide a concise summary of this result in plain language."
            )

            # Use xAI if available, otherwise use openai
            if xai_client and all(xai_client.get(k) for k in ["XAI_TOKEN", "XAI_API_URL"]):
                headers = {
                    "Authorization": f"Bearer {xai_client['XAI_TOKEN']}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": xai_client.get("XAI_MODEL", "grok-2-1212"),
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert at converting structured SQL results into concise plain language summaries.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                }

                try:
                    import requests
                    response = requests.post(
                        xai_client["XAI_API_URL"], headers=headers, json=data
                    )
                    grok_response = response.json()
                    final_message = grok_response["choices"][0]["message"]["content"]
                except Exception as e:
                    logger.error(f"Error using xAI: {e}")
                    # Fallback to OpenAI if xAI fails
                    if openai_client:
                        response = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an expert at converting structured SQL results into concise plain language summaries.",
                                },
                                {"role": "user", "content": prompt},
                            ],
                        )
                        final_message = response.choices[0].message.content
                    else:
                        # Fallback summary if LLM output not available
                        final_message = (
                            f"Total orders: {count_value}. Detailed order information is available below."
                            if results
                            else "No orders to display."
                        )
            elif openai_client:
                # Use OpenAI directly if xAI not available
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at converting structured SQL results into concise plain language summaries.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                final_message = response.choices[0].message.content
            else:
                # Basic fallback if no LLM available
                final_message = (
                    f"Total orders: {count_value}. Detailed order information is available below."
                    if results
                    else "No orders to display."
                )
                
            return final_message

        except Exception as e:
            logger.error(f"Error processing results: {e}")
            return "Could not process the query results."
    else:
        return "Sorry, I couldn't retrieve the data. Please try again later."

# Wrapper for database functions
def execute_menu_query(sql_query: str, params=None) -> Dict[str, Any]:
    """
    Execute a SQL query against the menu database.
    Direct implementation to avoid dependencies on external modules.
    
    Args:
        sql_query (str): SQL query to execute
        params: Optional parameters for parameterized queries
        
    Returns:
        dict: Result dictionary with keys 'success', 'results', and optionally 'error'
    """
    conn = None
    try:
        # Use the get_db_connection function defined elsewhere in this module
        # or directly establish a connection here
        from utils.database_functions import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        if params:
            cur.execute(sql_query, params)
        else:
            cur.execute(sql_query)

        # Import Decimal for type conversion if needed
        from decimal import Decimal
        
        # Convert Decimal types to float for JSON serialization
        results = [
            {
                col: float(val) if isinstance(val, Decimal) else val
                for col, val in row.items()
            }
            for row in cur.fetchall()
        ]

        return {
            "success": True,
            "results": results,
            "columns": [desc[0] for desc in cur.description],
            "query": sql_query,
        }
    except Exception as e:
        logger.error(f"Error executing menu query: {str(e)}")
        return {"success": False, "error": str(e), "query": sql_query}
    finally:
        if conn:
            conn.close()

# Function to format order response with details in a table
def format_order_response(summary: str, results: List[Dict]) -> Dict[str, str]:
    """Formats order details into a table response"""
    if not results:
        table_text = "No orders to display."
    else:
        table_lines = [
            "| Order ID | Customer | Order Date Time | Total Revenue | Phone |",
            "| --- | --- | --- | --- | --- |",
        ]
        for o in results:
            order_id = o.get("order_id", "N/A")
            customer = (
                f"{o.get('customer_first_name', '')} {o.get('customer_last_name', '')}".strip()
                or "N/A"
            )
            order_date = o.get("order_created_at", "N/A")
            if isinstance(order_date, datetime.datetime):
                order_date = order_date.strftime("%Y-%m-%d %H:%M:%S")
            total_revenue = f"${o.get('order_total', 0):.2f}"
            phone = o.get("phone", "N/A")
            table_lines.append(
                f"| {order_id} | {customer} | {order_date} | {total_revenue} | {phone} |"
            )
        table_text = "\n".join(table_lines)

    final_summary = f"{summary}\n\n" f"**Order Details:**\n\n" f"{table_text}"
    return {"role": "assistant", "content": final_summary}

class StreamlitCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for streaming LangChain output to Streamlit.
    This can be used to update the Streamlit UI in real-time as
    the agent executes.
    """

    def __init__(self, container):
        self.container = container
        self.text = ""
        self.is_thinking = True
        self.tool_used = ""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs
    ) -> None:
        """Called when LLM starts processing"""
        self.text = ""
        self.is_thinking = True
        self.container.empty()
        self.container.markdown("_Thinking..._")

    def on_text(self, text: str, **kwargs) -> None:
        """Called when raw text is available"""
        self.is_thinking = False
        self.text += text
        # Apply a typewriter effect with clean formatting
        self.container.markdown(self.text + "▌")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Stream tokens to Streamlit UI with a cleaner display"""
        self.is_thinking = False
        self.text += token
        # Apply a typewriter effect with clean formatting
        self.container.markdown(self.text + "▌")

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM ends"""
        self.is_thinking = False
        # Remove the cursor at the end
        self.container.markdown(self.text)

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called on LLM error"""
        self.is_thinking = False
        self.container.error(f"Error: {error}")

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs
    ) -> None:
        """Called at the start of a chain"""
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called at the end of a chain"""
        self.is_thinking = False

    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called on chain error"""
        self.is_thinking = False
        self.container.error(f"Chain error: {error}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs
    ) -> None:
        """Called when a tool starts running - show this in the UI"""
        tool_name = serialized.get("name", "unknown")
        self.tool_used = tool_name
        with self.container:
            with st.status(f"Using tool: {tool_name}", state="running"):
                st.write(f"Input: {input_str[:100]}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends - show completion in UI"""
        if self.tool_used:
            with self.container:
                st.success(f"Tool '{self.tool_used}' completed")
        self.tool_used = ""

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called on tool error"""
        self.container.error(f"Tool error: {error}")
        self.tool_used = ""

    def on_agent_action(self, action: AgentAction, **kwargs) -> Any:
        """Run when agent takes action - display nicely"""
        with self.container:
            st.info(
                f"**Action**: {action.tool}\n**Input**: {action.tool_input[:150]}..."
            )

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Run when agent finishes"""
        self.is_thinking = False


def create_sql_database_tool(execute_query_func):
    """
    Create a Tool for executing SQL queries on the database.

    Args:
        execute_query_func: Function that executes SQL queries

    Returns:
        Tool: A LangChain Tool for executing SQL queries
    """

    def _run_query(query: str) -> str:
        result = execute_query_func(query)
        if result.get("success", False):
            return str(result.get("results", []))
        else:
            return f"Error executing query: {result.get('error', 'Unknown error')}"

    return Tool(
        name="sql_database",
        func=_run_query,
        description="""Useful for when you need to execute SQL queries against the database.

Important database schema information:
- The orders table has columns: id, customer_id, location_id, created_at, updated_at, status (NOT order_date or order_status)
- For date filtering, use 'updated_at' instead of 'order_date'
- For status filtering, use 'status' (NOT 'order_status')
- Date format should be 'YYYY-MM-DD'
- When querying orders without a specific status filter, ALWAYS filter for completed orders (status = 7)

Example valid queries:
- SELECT COUNT(*) FROM orders WHERE updated_at::date = '2025-02-21' AND status = 7; -- 7 is the status code for completed orders
- SELECT * FROM orders WHERE updated_at BETWEEN '2025-02-01' AND '2025-02-28' AND status = 7;
- SELECT * FROM orders WHERE status = 7; -- Default to completed orders""",
    )


def create_menu_update_tool(execute_update_func):
    """
    Create a Tool for updating menu items.

    Args:
        execute_update_func: Function that executes menu updates

    Returns:
        Tool: A LangChain Tool for updating menu items
    """

    def _run_update(update_spec: str) -> str:
        try:
            # Parse the update specification
            import json

            spec = json.loads(update_spec)

            # Execute the update
            result = execute_update_func(spec)

            if result.get("success", False):
                return f"Update successful. Affected {result.get('affected_rows', 0)} rows."
            else:
                return f"Error updating menu: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"Error parsing update specification: {str(e)}"

    return Tool(
        name="update_menu",
        func=_run_update,
        description="Useful for updating menu items, prices, or enabling/disabling items.",
    )


def create_langchain_agent(
    openai_api_key: str = None,
    model_name: str = "gpt-3.5-turbo",  # Use model compatible with older OpenAI
    temperature: float = 0.3,
    streaming: bool = True,
    callback_handler=None,
    memory=None,
    tools: List[Tool] = None,
    verbose: bool = False,
) -> AgentExecutor:
    """
    Create a LangChain agent with the specified configuration.

    Args:
        openai_api_key: OpenAI API key (will use env var if not provided)
        model_name: Name of the OpenAI model to use
        temperature: Temperature for the model
        streaming: Whether to stream the output
        callback_handler: Callback handler for streaming output
        memory: Memory to use for the agent
        tools: List of tools for the agent to use
        verbose: Whether to print verbose output

    Returns:
        AgentExecutor: The configured LangChain agent
    """
    # Use provided API key or get from environment
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment")

    # Create the LLM
    llm_kwargs = {
        "model_name": model_name,
        "temperature": temperature,
        "openai_api_key": api_key,
    }

    # Only add streaming if supported in this environment
    if streaming:
        llm_kwargs["streaming"] = True

    # Create the LLM with ChatOpenAI
    llm = ChatOpenAI(**llm_kwargs)

    # Set up callbacks
    callbacks = None
    if callback_handler:
        callbacks = [callback_handler]
    elif streaming and verbose:
        callbacks = [StreamingStdOutCallbackHandler()]

    # Create memory if not provided
    if memory is None:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

    # Initialize tools list if not provided
    if tools is None:
        tools = []

    try:
        # For LangChain 0.0.150, initialize the agent with the callbacks in the specific way that works
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=memory,
            verbose=verbose,
        )

        # Set the callbacks on the agent executor if needed
        if callbacks and hasattr(agent, "callbacks"):
            agent.callbacks = callbacks

        return agent
    except Exception as e:
        # Fallback method if there was an error with the first approach
        try:
            # Try the alternate approach with different parameters
            agent_kwargs = {
                "llm": llm,
                "tools": tools,
                "verbose": verbose,
                "memory": memory,
            }

            if callbacks:
                agent_kwargs["callbacks"] = callbacks

            agent = AgentExecutor.from_agent_and_tools(
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                tools=tools,
                llm=llm,
                verbose=verbose,
                memory=memory,
            )

            return agent
        except Exception as inner_e:
            raise ValueError(
                f"Failed to initialize agent: {str(e)}. Inner error: {str(inner_e)}"
            )


def create_simple_chain(
    openai_api_key: str = None,
    model_name: str = "gpt-3.5-turbo",  # Use model compatible with older OpenAI
    temperature: float = 0.3,
    streaming: bool = True,
    callback_handler=None,
    prompt_template: str = None,
    system_message: str = None,
) -> ConversationChain:
    """
    Create a simple LangChain conversation chain.

    Args:
        openai_api_key: OpenAI API key (will use env var if not provided)
        model_name: Name of the OpenAI model to use
        temperature: Temperature for the model
        streaming: Whether to stream the output
        callback_handler: Callback handler for streaming output
        prompt_template: Custom prompt template to use
        system_message: System message to use

    Returns:
        ConversationChain: The configured conversation chain
    """
    # Use provided API key or get from environment
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment")

    # Create the LLM
    llm_kwargs = {
        "model_name": model_name,
        "temperature": temperature,
        "openai_api_key": api_key,
    }

    # Only add streaming if supported in this environment
    if streaming:
        llm_kwargs["streaming"] = True

    # Create the LLM instance
    llm = ChatOpenAI(**llm_kwargs)

    # Prepare callbacks for chain initialization - don't set them on LLM
    callbacks = None
    if callback_handler:
        callbacks = [callback_handler]

    # Create memory
    memory = ConversationBufferMemory(return_messages=True)

    # Create prompt template if provided
    chain_kwargs = {"llm": llm, "memory": memory, "verbose": True}

    # Add callbacks to chain initialization if they exist
    if callbacks:
        chain_kwargs["callbacks"] = callbacks

    if prompt_template:
        prompt = PromptTemplate(
            input_variables=["history", "input"], template=prompt_template
        )
        chain_kwargs["prompt"] = prompt

    # Create the chain
    chain = ConversationChain(**chain_kwargs)

    return chain


def integrate_with_existing_flow(
    query: str,
    tools: List[Tool],
    context: Dict[str, Any] = None,
    agent: Optional[AgentExecutor] = None,
    callback_handler=None,
) -> Dict[str, Any]:
    """
    Integrate LangChain with the existing query flow.

    Args:
        query: User query
        tools: List of tools to use
        context: Context from previous queries
        agent: Existing agent to use, or None to create a new one
        callback_handler: Callback handler for streaming

    Returns:
        Dict: Results from the agent execution
    """
    # Log the incoming user query
    logger.info(f"Received user query: '{query}'")
    
    # Using local implementations instead of importing from integrate_app
    # Note: all these functions are now directly implemented in this file
    # get_clients, create_categorization_prompt, call_sql_generator,
    # create_summary_prompt, create_system_prompt_with_business_rules,
    # load_application_context
    
    import openai

    # Initialize callback if provided
    callbacks = [callback_handler] if callback_handler else None

    # Tracking for the 4-step flow
    flow_steps = {
        "categorization": {
            "name": "OpenAI Categorization",
            "status": "pending",
            "data": None,
        },
        "sql_generation": {"name": "SQL Generation", "status": "pending", "data": None},
        "execution": {"name": "SQL Execution", "status": "pending", "data": None},
        "summarization": {
            "name": "Result Summarization",
            "status": "pending",
            "data": None,
        },
    }

    try:
        # Get clients for API access
        openai_client, _ = get_clients()

        # Load context from previous state
        conversation_history = []
        if context and "conversation_history" in context:
            conversation_history = context["conversation_history"]

        # Get cached dates from previous context
        cached_dates = context.get("date_filter") if context else None

        # STEP 1: OpenAI Categorization
        if callback_handler:
            callback_handler.on_text("Step 1: OpenAI Query Categorization\n")

        # Create prompt with cached dates context
        categorization_result = create_categorization_prompt(cached_dates=cached_dates)
        categorization_prompt = categorization_result["prompt"]

        # Check if the OpenAI client has the right structure for the version used
        # Handle both old and new OpenAI API versions
        try:
            # For new OpenAI client (>=1.0.0)
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": categorization_prompt},
                    {
                        "role": "user",
                        "content": f"Analyze this query and return a JSON response: {query}",
                    },
                ],
                response_format={"type": "json_object"},
            )
        except (AttributeError, TypeError):
            # For older OpenAI client (<1.0.0) or if client is a function
            # Try to create a new OpenAI client
            try:
                # Directly try the new API format
                # Use the legacy OpenAI API format for 0.28.1
                categorization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": categorization_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this query and return a JSON response: {query}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )
            except (ImportError, Exception):
                # Try old OpenAI SDK style
                categorization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": categorization_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this query and return a JSON response: {query}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )

        # Process OpenAI response
        if hasattr(categorization_response, "choices"):
            # New OpenAI API format
            raw_response = categorization_response.choices[0].message.content
        else:
            # Old OpenAI API format
            raw_response = categorization_response["choices"][0]["message"]["content"]

        json_response = json.loads(raw_response)
        
        # Log the categorization response
        logger.info(f"Categorization response: {raw_response[:200]}..." if len(raw_response) > 200 else raw_response)
        
        # For long responses, also dump to a file for easier debugging
        if len(raw_response) > 1000:
            log_to_file(raw_response, prefix="categorization")

        # Update flow tracking
        flow_steps["categorization"]["data"] = json_response
        flow_steps["categorization"]["status"] = "completed"

        # Extract query metadata
        query_type = json_response.get("request_type")
        time_period = json_response.get("time_period")
        start_date = json_response.get("start_date")
        end_date = json_response.get("end_date")
        item_name = json_response.get("item_name")
        new_price = json_response.get("new_price")

        if callback_handler:
            callback_handler.on_text(f"Query categorized as: {query_type}\n")

        # STEP 2: Google Gemini SQL Generation
        if callback_handler:
            callback_handler.on_text("\nStep 2: Google Gemini SQL Generation\n")

        # Load application context
        context_files = load_application_context()

        # Determine SQL based on query type
        sql_query = None

        # For direct menu operations, generate SQL directly
        if query_type in ["update_price", "disable_item", "enable_item"]:
            if query_type == "update_price" and item_name and new_price:
                # Get location IDs from session
                location_ids = context.get(
                    "selected_location_ids", [1]
                )  # Default to location 1

                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                else:
                    location_id = location_ids[0] if location_ids else 1
                    sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
            elif query_type in ["disable_item", "enable_item"] and item_name:
                state = "true" if query_type == "disable_item" else "false"

                # Get location IDs from session
                location_ids = context.get(
                    "selected_location_ids", [1]
                )  # Default to location 1

                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                else:
                    location_id = location_ids[0] if location_ids else 1
                    sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        else:
            # For analytics queries, use Google Gemini to generate SQL
            # Format date context
            date_context_str = ""
            if start_date and end_date:
                date_context_str = f"""
                ACTIVE DATE FILTERS:
                - Start Date: {start_date}
                - End Date: {end_date}
                """
            elif time_period:
                date_context_str = f"""
                ACTIVE DATE FILTERS:
                - Time Period: {time_period}
                """

            # Get location ID from context
            location_id = context.get(
                "selected_location_id", 1
            )  # Default to location 1
            location_ids = context.get(
                "selected_location_ids", [1]
            )  # Default to location 1

            # Get previous SQL for context
            previous_sql = None
            if context and "last_sql_query" in context:
                previous_sql = context["last_sql_query"]

            # Call Google Gemini to generate SQL
            sql_query = call_sql_generator(
                query,
                context_files,
                location_id=location_id,
                previous_sql=previous_sql,
                conversation_history=conversation_history,
                date_context=date_context_str,
                time_period=time_period,
                location_ids=location_ids,
            )

            # Log the generated SQL query
            logger.info(f"Generated SQL query: {sql_query}")
            
            # For complex queries, also dump to a file for easier debugging
            if len(sql_query) > 500:
                log_to_file(sql_query, prefix="sql_query")

        # Update flow tracking
        if sql_query:
            flow_steps["sql_generation"]["data"] = {"sql_query": sql_query}
            flow_steps["sql_generation"]["status"] = "completed"

            if callback_handler:
                # Format SQL for display
                display_sql = sql_query.strip().replace("\n", " ").replace("  ", " ")
                callback_handler.on_text(f"Generated SQL: {display_sql}\n")
        else:
            flow_steps["sql_generation"]["status"] = "error"
            flow_steps["sql_generation"]["data"] = {"error": "Failed to generate SQL"}

            if callback_handler:
                callback_handler.on_text("Error: Failed to generate SQL\n")

            # If we can't generate SQL, use the LangChain agent as fallback
            if agent is None:
                agent = create_langchain_agent(
                    tools=tools, verbose=True, callback_handler=callback_handler
                )

            # Run the agent with callbacks passed directly
            agent_result = agent.run(query)

            return {
                "success": True,
                "summary": agent_result,
                "agent_result": agent_result,
                "context": context or {},
                "steps": flow_steps,
            }

        # STEP 3: SQL Execution
        if callback_handler:
            callback_handler.on_text("\nStep 3: SQL Execution\n")

        # Execute SQL query with timeout and retries
        max_retries = 2
        execution_result = None

        for attempt in range(max_retries + 1):
            try:
                execution_result = execute_menu_query(sql_query)
                break
            except Exception:
                if attempt < max_retries:
                    if callback_handler:
                        callback_handler.on_text(
                            f"Retry {attempt+1}/{max_retries} after execution error\n"
                        )
                else:
                    raise

        # Update flow tracking
        if execution_result and execution_result.get("success"):
            flow_steps["execution"]["data"] = execution_result
            flow_steps["execution"]["status"] = "completed"

            result_count = len(execution_result.get("results", []))
            if callback_handler:
                callback_handler.on_text(f"Query returned {result_count} result(s)\n")
        else:
            error_msg = (
                execution_result.get("error", "Unknown error")
                if execution_result
                else "Execution failed"
            )
            flow_steps["execution"]["status"] = "error"
            flow_steps["execution"]["data"] = {"error": error_msg}

            if callback_handler:
                callback_handler.on_text(f"SQL Execution Error: {error_msg}\n")

            # If execution fails, use the LangChain agent as fallback
            if agent is None:
                agent = create_langchain_agent(
                    tools=tools, verbose=True, callback_handler=callback_handler
                )

            # Run the agent with callbacks passed directly
            agent_result = agent.run(query)

            return {
                "success": True,
                "summary": agent_result,
                "agent_result": agent_result,
                "context": context or {},
                "steps": flow_steps,
            }

        # STEP 4: Result Summarization
        if callback_handler:
            callback_handler.on_text("\nStep 4: Result Summarization\n")

        # Create summary prompt
        summary_prompt = create_summary_prompt(
            query,
            sql_query,
            execution_result,
            query_type=query_type,
            conversation_history=conversation_history,
        )

        # Get system prompt with business rules
        system_prompt = create_system_prompt_with_business_rules()

        # Updated prompt to request both verbal and text answers
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
   - When mentioning dates, use "on February 21st, 2025" format with clear comma pauses
   - Avoid ambiguous date formats that might be misinterpreted when spoken
   - Always add a comma before the year when mentioning a full date
   - For number ranges, say "from X to Y" rather than "X-Y"

2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your concise, natural-sounding response here]
TEXT_ANSWER: [Your detailed response here]
"""

        # Handle both old and new OpenAI API versions for summarization
        try:
            # For new OpenAI client (>=1.0.0)
            summarization_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_summary_prompt},
                ],
                temperature=0.2,
            )
        except (AttributeError, TypeError):
            # For older OpenAI client (<1.0.0) or if client is a function
            try:
                # Directly try the new API format
                # Use the legacy OpenAI API format for 0.28.1
                summarization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": enhanced_summary_prompt},
                    ],
                    temperature=0.2,
                )
            except (ImportError, Exception):
                # Try old OpenAI SDK style
                summarization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": enhanced_summary_prompt},
                    ],
                    temperature=0.2,
                )

        # Process OpenAI response
        if hasattr(summarization_response, "choices"):
            # New OpenAI API format
            raw_response = summarization_response.choices[0].message.content
        else:
            # Old OpenAI API format
            raw_response = summarization_response["choices"][0]["message"]["content"]
            
        # Apply post-processing to convert ordinals to words in the verbal answer
        from prompts.summarization_prompt import post_process_summarization
        raw_response = post_process_summarization(raw_response)
            
        # Log the summarization response
        logger.info(f"Summarization response: {raw_response[:200]}..." if len(raw_response) > 200 else raw_response)
        
        # For long responses, also dump to a file for easier debugging
        if len(raw_response) > 1000:
            log_to_file(raw_response, prefix="summarization")

        # Parse the verbal and text answers
        verbal_answer = None
        text_answer = None

        # Extract verbal answer
        verbal_match = re.search(
            r"VERBAL_ANSWER:(.*?)(?=TEXT_ANSWER:|$)", raw_response, re.DOTALL
        )
        if verbal_match:
            verbal_answer = verbal_match.group(1).strip()
            # Clean the verbal answer for speech
            verbal_answer = clean_text_for_speech(verbal_answer)

        # Extract text answer
        text_match = re.search(r"TEXT_ANSWER:(.*?)$", raw_response, re.DOTALL)
        if text_match:
            text_answer = text_match.group(1).strip()

        # Create summary
        summary = text_answer or raw_response

        # Update flow tracking
        flow_steps["summarization"]["data"] = {"summary": summary}
        flow_steps["summarization"]["status"] = "completed"

        if callback_handler:
            callback_handler.on_text(f"\nResult: {summary}\n")

        # Update context with the new information
        updated_context = context or {}
        updated_context["last_sql_query"] = sql_query

        # Add the current query and response to conversation history
        conversation_entry = {"query": query, "response": summary, "sql": sql_query}

        if "conversation_history" not in updated_context:
            updated_context["conversation_history"] = []

        updated_context["conversation_history"].append(conversation_entry)

        # Update date filter cache
        if start_date and end_date:
            updated_context["date_filter"] = {
                "start_date": start_date,
                "end_date": end_date,
            }

        # Return results
        return {
            "success": True,
            "summary": summary,
            "verbal_answer": verbal_answer,
            "text_answer": text_answer,
            "sql_query": sql_query,
            "execution_result": execution_result,
            "categorization": json_response,
            "steps": flow_steps,
            "context": updated_context,
        }

    except Exception as e:
        # If anything fails, fall back to the LangChain agent
        if callback_handler:
            callback_handler.on_text(
                f"\nError in flow: {str(e)}\nFalling back to LangChain agent\n"
            )
            
        # Log the error
        logger.error(f"Error in AI flow: {str(e)}", exc_info=True)

        # Create or use existing agent
        if agent is None:
            agent = create_langchain_agent(
                tools=tools, verbose=True, callback_handler=callback_handler
            )

        try:
            # Run the agent with callbacks passed directly
            result = agent.run(query)
        except Exception as agent_error:
            result = f"Error running agent: {str(agent_error)}"

        # Return the result in a format compatible with the existing flow
        return {
            "success": True,
            "summary": result,
            "agent_result": result,
            "fallback": True,
            "error": str(e),
            "context": context or {},
        }


def clean_text_for_speech(text):
    """
    Clean and format text to be more appropriate for text-to-speech engines.
    This ensures dates, numbers, and other elements are properly formatted
    for clear verbal communication.
    
    Uses advanced NLP libraries if available:
    - textacy: For advanced text normalization
    - num2words: For converting numbers to words
    - unidecode: For handling special characters
    - re: For precise pattern matching with regular expressions
    """
    import re
    
    if not text:
        return text
    
    # 1. BASIC CLEANUP
    
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    
    # Remove markdown formatting 
    text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)  # Remove ** and * (bold and italic)
    text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)  # Remove bullet points
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # Remove markdown headers
    
    # Try to import optional advanced libraries
    try:
        from num2words import num2words
        has_num2words = True
    except ImportError:
        logger.warning("num2words library not found, limited number processing available")
        has_num2words = False
        
    try:
        from unidecode import unidecode
        has_unidecode = True
    except ImportError:
        logger.warning("unidecode library not found, limited accent processing available") 
        has_unidecode = False
        
    try:
        import textacy.preprocessing.normalize as tpn
        import textacy.preprocessing.replace as tpr
        has_textacy = True
    except ImportError:
        logger.warning("textacy library not found, limited text normalization available")
        has_textacy = False
    
    # 2. NORMALIZE TEXT WITH TEXTACY IF AVAILABLE
    if has_textacy:
        # Normalize whitespace, quotation marks, dashes, etc.
        text = tpn.whitespace(text)
        text = tpn.hyphenated_words(text)
        text = tpn.quotation_marks(text)
    else:
        # Simple normalization fallbacks
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'["""''‹›«»]', '"', text)  # Normalize quotes
    
    # 3. HANDLE EMAIL AND PHONE FORMATS
    
    # Handle email addresses
    text = re.sub(r'([\w.+-]+@[\w-]+\.[\w.-]+)', ' email address ', text)
    
    # Handle phone numbers more consistently
    text = re.sub(r'(?<!\w)(?:\+?1[-\s]?)?(?:\(?\d{3}\)?[-\s]?)\d{4}(?!\w)', ' phone number ', text)
    
    # 4. DATE FORMATTING
    
    # First remove any spaces in ordinal suffixes like "21 st" -> "21st"
    # This needs to run before any other date formatting
    text = re.sub(r'(\d+)\s+(st|nd|rd|th)\b', r'\1\2', text)
    
    # Apply unidecode if available
    if has_unidecode:
        text = unidecode(text)
    
    return text


def test_speech_cleaning():
    """Test the clean_text_for_speech function with various examples"""
    test_cases = [
        "Orders on February 21st 2025 were higher than expected.",
        "Orders on February 21 2025 were higher than expected.",
        "Orders on February 21 st 2025 were higher than expected.",  # Spaced suffix
        "Revenue for 01/15/2025 was $5000.",
        "Comparing data from 2025-03-10 to 2025-03-15 shows growth.",
        "Sales increased by 15% on March 3rd 2025.",
        "Sales increased by 15% on March 3 rd 2025.",  # Spaced suffix  
        "We sold 15items on Tuesday.",
        "The average order value was $25.5vs.$20.8 last week.",
        "Comparing December 15th 2024 to January 5th 2025, we see a 12% increase.",
        # New test cases
        "Visit https://example.com for more information!",
        "Contact us at +1 (555) 123-4567 or email@example.com",
        "The range 2023-2024 shows a 5-10% improvement.",
        "Our company, Dr. Smith & Co., will host an event.",
        "The temperature is approx. 72° today vs. 65° yesterday.",
        "For small numbers: 1 2 3 show as words, but 25, 100, 1000 stay as digits.",
        "The product costs $9.5 today, down from $10.5 yesterday.",
        # Ordinal date conversion test cases
        "The meeting is on the 21st of July.",
        "Please submit your report by January 3rd.",
        "The event will take place on October 22nd, 2025.",
        "He was born on the 15th of May, 1990.",
        "We'll celebrate the 1st, 2nd, and 3rd place winners.",
        "The 4th quarter results were impressive.",
        "May 5th and June 6th are important dates.",
        "The 31st of December is New Year's Eve."
    ]
    
    print("===== SPEECH CLEANING TEST =====")
    for case in test_cases:
        cleaned = clean_text_for_speech(case)
        print(f"\nOriginal: {case}")
        print(f"Cleaned:  {cleaned}")
    print("===============================")
    return "Test completed."

def get_current_session_id():
    """Return the current session ID for use in other parts of the application"""
    global current_session_id
    return current_session_id

def get_session_log_path():
    """Return the path to the current session's log file"""
    global current_session_id
    if current_session_id:
        return f"logs/session_{current_session_id}.log"
    return None

def log_to_file(content, filename=None, prefix="dump"):
    """
    Dumps content to a file in the logs directory for debugging
    
    Args:
        content: Content to dump (string, dict, or other object)
        filename: Optional filename, if None a timestamped name will be used
        prefix: Prefix for auto-generated filenames
        
    Returns:
        Path to the created file
    """
    global current_session_id
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if current_session_id:
            filename = f"{prefix}_{current_session_id}_{timestamp}.txt"
        else:
            filename = f"{prefix}_{timestamp}.txt"
    
    file_path = os.path.join("logs", filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        if isinstance(content, str):
            f.write(content)
        else:
            try:
                # Try to convert to JSON
                f.write(json.dumps(content, indent=2))
            except (TypeError, ValueError, OverflowError) as e:
                # Fallback to string representation with error note
                f.write(f"Error converting to JSON: {str(e)}\n\n")
                f.write(str(content))
    
    logger = logging.getLogger("ai_menu_updater")
    logger.info(f"Content dumped to {file_path}")
    
    return file_path

def log_session_end():
    """
    Log the end of the current session for easier log analysis
    """
    global current_session_id
    if current_session_id:
        logger = logging.getLogger("ai_menu_updater")
        logger.info(f"Session {current_session_id} ended")
        
        # Create a summary file with session statistics if needed
        # This is where you could add code to analyze the session logs and generate stats

def get_recent_logs(n_lines=20, session_specific=True):
    """
    Get the most recent log entries from either the session log or global log
    
    Args:
        n_lines: Number of lines to retrieve
        session_specific: If True, get logs from the current session only
        
    Returns:
        List of log lines
    """
    if session_specific and current_session_id:
        log_path = get_session_log_path()
    else:
        log_path = "logs/ai_interaction.log"
    
    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                # Read all lines and take the last n_lines
                lines = f.readlines()
                return lines[-n_lines:] if len(lines) > n_lines else lines
    except Exception as e:
        logger = logging.getLogger("ai_menu_updater")
        logger.error(f"Error reading log file: {str(e)}")
    
    return []

def cleanup_old_logs(days_to_keep=30):
    """
    Remove log files older than the specified number of days
    
    Args:
        days_to_keep: Number of days to keep logs for
        
    Returns:
        Number of files deleted
    """
    # Calculate the cutoff time
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_time.timestamp()
    
    # Get all log files
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return 0
    
    files_deleted = 0
    
    # Process each file
    for filename in os.listdir(log_dir):
        if filename.startswith("session_") and filename.endswith(".log"):
            file_path = os.path.join(log_dir, filename)
            
            # Skip the README.md file
            if filename == "README.md":
                continue
                
            # Skip the global log file
            if filename == "ai_interaction.log":
                continue
            
            # Check file modification time
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_timestamp:
                try:
                    os.remove(file_path)
                    files_deleted += 1
                except Exception as e:
                    logger = logging.getLogger("ai_menu_updater")
                    logger.error(f"Error deleting log file {file_path}: {str(e)}")
    
    return files_deleted

