import streamlit as st
from utils.config import (
    db_credentials,
    MAX_TOKENS_ALLOWED,
    MAX_MESSAGES_TO_OPENAI,
    TOKEN_BUFFER,
)
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import (
    run_chat_sequence,
    clear_chat_history,
    count_tokens,
    prepare_sidebar_data,
    process_query_results,
)
from utils.database_functions import (
    get_db_connection,
    execute_menu_query,
    database_schema_dict,
)
from utils.function_calling_spec import functions as get_functions_list
from utils.helper_functions import save_conversation
from utils.ui_components import (
    render_price_input,
    render_time_input,
    render_option_limits,
    validate_menu_update,
)
from assets.dark_theme import dark
from assets.light_theme import light
from assets.made_by_sdw import made_by_sdw
import pandas as pd

# Handle both old and new OpenAI package versions
try:
    # For OpenAI >= 1.0.0
    from openai import OpenAI

    HAS_NEW_OPENAI = True
except ImportError:
    # For OpenAI < 1.0.0
    import openai

    HAS_NEW_OPENAI = False

    class OpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
            if api_key:
                openai.api_key = api_key

        def chat(self):
            class ChatCompletions:
                @staticmethod
                def create(*args, **kwargs):
                    return openai.ChatCompletion.create(*args, **kwargs)

            return ChatCompletions()

        def completions(self):
            return openai


import os
from itertools import takewhile
from utils.create_sql_statement import generate_sql_from_user_query
from typing import List, Dict, Any
import logging
import json
from dotenv import load_dotenv
from utils.query_processing import process_query_results
import psycopg2
import requests
from datetime import datetime, timezone, timedelta
import re
import pytz

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
        current_date_in_user_tz = datetime.now(USER_TIMEZONE).date()

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
                user_date = datetime.now(USER_TIMEZONE)
            elif date_str.lower() == "yesterday":
                user_date = datetime.now(USER_TIMEZONE) - timedelta(days=1)
            else:
                # Try to parse the date string
                user_date = datetime.strptime(date_str, "%Y-%m-%d")
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


# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Clear existing handlers to prevent multiple file handles
for handler in logger.handlers[:]:
    if isinstance(handler, logging.FileHandler):
        handler.close()
    logger.removeHandler(handler)

log_file_path = "logs/app_log.log"

# Remove existing log file if possible
try:
    if os.path.exists(log_file_path):
        os.remove(log_file_path)
except PermissionError:
    logger.warning(
        "Could not delete previous log file - it might be open in another process"
    )

# Create fresh log file
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
file_handler = logging.FileHandler(log_file_path)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- Streamlit App ---
logger.info("Starting app.py")

load_dotenv()
logger.info(".env file loaded")

# Enable debug mode in sidebar
debug_mode = st.sidebar.checkbox(
    "Enable Debug Mode", value=False
)  # Set to False by default
st.session_state.debug_mode = False  # Ensure it's False in session state
logger.info(f"Debug mode set to: {debug_mode}")


def get_recent_messages():
    logger.info("Entering get_recent_messages")
    messages = st.session_state["api_chat_history"]
    logger.debug(f"Current api_chat_history: {messages}")

    if not messages:
        logger.info("No messages in history. Returning system prompt.")
        return [
            {
                "role": "system",
                "content": get_final_system_prompt(db_credentials=db_credentials),
            }
        ]

    total_tokens = 0
    for i in range(len(messages) - 1, -1, -1):
        tokens = count_tokens(messages[i]["content"])
        logger.debug(f"Message {i} has {tokens} tokens.")
        if total_tokens + tokens > MAX_MESSAGES_TO_OPENAI - TOKEN_BUFFER:
            logger.info(f"Token limit reached. Returning messages from index {i + 1}.")
            return messages[i + 1 :] if i + 1 < len(messages) else messages[-1:]
        total_tokens += tokens

    logger.info("Returning all messages.")
    return messages


def get_xai_client():
    logger.info("Entering get_xai_client")
    env_vars = {
        "XAI_TOKEN": os.getenv("XAI_TOKEN"),
        "XAI_API_URL": os.getenv("XAI_API_URL"),
        "XAI_MODEL": os.getenv("XAI_MODEL"),
    }
    logger.debug(f"XAI environment variables: {env_vars}")

    missing = [k for k, v in env_vars.items() if not v]
    if missing:
        error_message = f"Missing XAI environment variables: {', '.join(missing)}"
        logger.error(error_message)
        raise ValueError(error_message)

    logger.info("XAI client initialized successfully.")
    return env_vars


def run_chat_sequence(
    messages: List[Dict[str, str]],
    functions: List[Dict[str, Any]],
    openai_client,
    xai_client,
) -> Dict[str, str]:
    logger.info("Entering run_chat_sequence")
    user_message = messages[-1]["content"] if messages else ""
    logger.info(f"User message: {user_message}")

    try:
        location_id = st.session_state.get("selected_location_id", 62)
        logger.info(f"Location ID: {location_id}")

        if not location_id:
            logger.warning("No location selected.")
            return {
                "role": "assistant",
                "content": "Please select a location first to view order information.",
            }

        # Add timezone info to logging
        location_tz = get_location_timezone(location_id)
        user_tz = USER_TIMEZONE
        logger.info(
            f"Using location timezone: {location_tz.zone}, User timezone: {user_tz.zone}"
        )

        logger.info("Categorizing user request using OpenAI.")
        # Force function calling for follow-up order queries
        if st.session_state.get("last_sql_query") and "order" in user_message.lower():
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                functions=functions,
                function_call={"name": "query_orders"},  # Force function call
            )
        else:
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, functions=functions
            )
        logger.debug(f"Categorization response: {categorization_response}")

        function_call = categorization_response.choices[0].message.function_call

        if function_call is None:
            logger.error("No function call in OpenAI response")
            return {
                "role": "assistant",
                "content": "I need more details to help with that.",
            }

        request_type = function_call.name
        args = json.loads(function_call.arguments)
        logger.info(f"Request type: {request_type}, Arguments: {args}")

        # Log the function call
        st.session_state.api_chat_history.append(
            {
                "role": "assistant",
                "content": None,
                "function_call": {"name": request_type, "arguments": json.dumps(args)},
            }
        )

        # Check if this is an order-related request
        if request_type in ["query_orders", "query_menu"]:
            logger.info("Handling query request.")
            base_sql_query = st.session_state.get("last_sql_query")
            sql_query = generate_sql_from_user_query(
                user_message, location_id, base_sql_query=base_sql_query
            )
            sql_query = sql_query.replace("created_at", "updated_at")
            st.session_state["last_sql_query"] = sql_query
            logger.info(f"Generated SQL query: {sql_query}")

            # Convert any date parameters to location timezone
            if "date" in args:
                args["date"] = convert_user_date_to_location_tz(
                    args["date"], location_id
                )

            # Adjust any generated SQL to handle timezones properly
            sql_query = adjust_query_timezone(sql_query, location_id)
            logger.info(f"Timezone-adjusted SQL query: {sql_query}")

            result = execute_menu_query(sql_query)
            logger.debug(f"SQL query result: {result}")

            # Add explicit result mapping for count queries
            if "COUNT(" in sql_query.upper():
                result_keys = result.get("results", [{}])[0].keys()
                count_key = next((k for k in result_keys if "count" in k.lower()), None)
                count_value = result.get("results", [{}])[0].get(count_key, 0)
                summary = f"There were {count_value} completed orders in the specified period."
            else:
                # For detail queries, process normally
                summary = process_query_results(
                    query_result=result,
                    user_question=user_message,
                    openai_client=openai_client,
                    xai_client=xai_client,
                )

            # Check if user is asking for details explicitly;
            # Instead of referencing cached orders, use the fresh query result.
            show_details = any(
                keyword in user_message.lower()
                for keyword in ["detail", "list", "show me", "display"]
            )

            if show_details and result.get("success") and result.get("results"):
                return format_order_response(summary, result.get("results", []))
            else:
                return {"role": "assistant", "content": summary}

        elif request_type == "update_price":
            logger.info(f"Handling price update: {args}")
            # ... (rest of update_price logic)
        elif request_type == "disable_item":
            logger.info(f"Handling disable item: {args}")
            # ... (rest of disable_item logic)
        elif request_type == "enable_item":
            logger.info(f"Handling enable item: {args}")
            # ... (rest of enable_item logic)
        else:
            logger.warning(f"Unknown request type: {request_type}")
            return {
                "role": "assistant",
                "content": "Sorry, I couldn't understand your request.",
            }

    except Exception as e:
        logger.exception(f"Error in run_chat_sequence: {e}")
        return {"role": "assistant", "content": f"I encountered an error: {str(e)}"}


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
            if isinstance(order_date, datetime):
                order_date = order_date.strftime("%Y-%m-%d %H:%M:%S")
            total_revenue = f"${o.get('order_total', 0):.2f}"
            phone = o.get("phone", "N/A")
            table_lines.append(
                f"| {order_id} | {customer} | {order_date} | {total_revenue} | {phone} |"
            )
        table_text = "\n".join(table_lines)

    final_summary = f"{summary}\n\n" f"**Order Details:**\n\n" f"{table_text}"
    return {"role": "assistant", "content": final_summary}


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

            # DIRECTLY USE SQL RESULT VALUE (14 in your case)
            count_value = (
                results[0]["count"] if results else 0
            )  # This gets the 14 from your SQL result

            # Build prompt with actual database value
            prompt = (
                f"The SQL query for '{user_question}' returned {count_value} completed orders. "
                "Provide a concise summary of this result in plain language."
            )

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

            response = requests.post(
                xai_client["XAI_API_URL"], headers=headers, json=data
            )
            grok_response = response.json()

            try:
                final_message = grok_response["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                # Fallback summary if LLM output not available
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


def get_openai_client():
    # Using the internal OpenAI class for compatibility with different versions
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_xai_config():
    return {
        "XAI_TOKEN": os.getenv("XAI_TOKEN"),
        "XAI_API_URL": os.getenv("XAI_API_URL"),
        "XAI_MODEL": os.getenv("XAI_MODEL"),
    }


if __name__ == "__main__":
    logger.info("Initializing session state variables")
    if "operation" not in st.session_state:
        st.session_state["operation"] = None
        logger.debug("Initialized 'operation'")

    if "selected_location_id" not in st.session_state:
        st.session_state["selected_location_id"] = None
        logger.debug("Initialized 'selected_location_id'")

    if "full_chat_history" not in st.session_state:
        st.session_state["full_chat_history"] = [
            {
                "role": "system",
                "content": get_final_system_prompt(db_credentials=db_credentials),
            },
            {
                "role": "assistant",
                "content": "Hello! I'm your menu management assistant. How can I help you today? I can:\n\n• Update menu item prices\n• Enable/disable menu items\n• Show menu information\n\nWhat would you like to do?",
            },
        ]
        logger.debug("Initialized 'full_chat_history'")

    if "api_chat_history" not in st.session_state:
        st.session_state["api_chat_history"] = [
            {
                "role": "system",
                "content": get_final_system_prompt(db_credentials=db_credentials),
            },
            {
                "role": "assistant",
                "content": "Hello! I'm your menu management assistant. How can I help you today?",
            },
        ]
        logger.debug("Initialized 'api_chat_history'")

    if "xai_config" not in st.session_state:
        st.session_state.xai_config = {
            "XAI_TOKEN": os.getenv("XAI_TOKEN"),
            "XAI_API_URL": os.getenv("XAI_API_URL"),
            "XAI_MODEL": os.getenv("XAI_MODEL"),
        }

    logger.info("Initializing XAI and OpenAI clients")
    xai_client = get_xai_client()
    openai_client = get_openai_client()
    logger.info("Clients initialized")

    ########### A. SIDEBAR ###########

    st.sidebar.title("📍 Location Selection")
    logger.info("Starting location selection logic")
    try:
        query_result = execute_menu_query(
            """
            SELECT id, name
            FROM locations
            WHERE deleted_at IS NULL
            ORDER BY id DESC
        """
        )
        logger.info(f"Location query result: {query_result}")

        if query_result["success"] and query_result["results"]:
            locations = query_result["results"]
            location_options = ["All"] + [
                f"{loc['id']} - {loc['name']}" for loc in locations
            ]
            logger.debug(f"Location options: {location_options}")

            default_index = 0
            for i, loc in enumerate(locations):
                if loc["id"] == 62:
                    default_index = i + 1
                    break
            logger.debug(f"Default location index: {default_index}")

            selected_location = st.sidebar.selectbox(
                "Select Location", options=location_options, index=default_index
            )
            logger.info(f"Selected location: {selected_location}")

            if selected_location != "All":
                selected_location_id = int(selected_location.split(" - ")[0])
                st.session_state["selected_location_id"] = selected_location_id
                logger.info(f"Selected location ID: {selected_location_id}")
            else:
                st.session_state["selected_location_id"] = None
                logger.info("Selected location: All")
        else:
            st.sidebar.error("No locations found in database")
            logger.warning("No locations found in the database.")

    except psycopg2.Error as e:
        st.sidebar.error(f"Database error: {e}")
        logger.exception(f"Database error during location selection: {e}")
    except Exception as e:
        st.sidebar.error(f"An unexpected error occurred: {e}")
        logger.exception(f"Unexpected error during location selection: {e}")

    st.sidebar.markdown("---")

    sidebar_data = prepare_sidebar_data(database_schema_dict)
    logger.info("Sidebar data prepared for schema visualization.")
    st.sidebar.markdown(
        "<div class='made_by'>Made by SDW🔋</div>", unsafe_allow_html=True
    )

    ### MENU OPERATIONS ###
    st.sidebar.title("🍽️ Menu Operations")
    logger.info("Menu Operations section loaded.")

    st.markdown(dark, unsafe_allow_html=True)
    logger.info("Dark theme applied.")

    ########### B. CHAT INTERFACE ###########

    st.title("Swoop AI Assistant")
    logger.info("Chat interface loaded.")

    if (prompt := st.chat_input("What do you want to know?")) is not None:
        logger.info(f"User prompt received: {prompt}")
        st.session_state.full_chat_history.append({"role": "user", "content": prompt})
        st.session_state.api_chat_history.append({"role": "user", "content": prompt})
        logger.debug(
            f"Chat history updated. full_chat_history: {st.session_state.full_chat_history}, api_chat_history: {st.session_state.api_chat_history}"
        )

    for message in st.session_state.full_chat_history:
        if message["role"] == "assistant":
            # Handle both string and accidental dictionary formats
            response_text = (
                message["content"].get("content", str(message["content"]))
                if isinstance(message["content"], dict)
                else message["content"]
            )
            st.markdown(f"🤖 {response_text}")
        elif message["role"] == "user":
            st.markdown(f"🧑💻 {message['content']}")

    if st.session_state["api_chat_history"][-1]["role"] != "assistant":
        with st.spinner("⌛Connecting to AI model..."):
            recent_messages = get_recent_messages()
            logger.info("Calling run_chat_sequence")
            new_message = run_chat_sequence(
                recent_messages, get_functions_list, openai_client, xai_client
            )
            logger.info(f"Response from run_chat_sequence: {new_message}")

            st.session_state["api_chat_history"].append(new_message)
            st.session_state["full_chat_history"].append(new_message)
            logger.debug(
                f"Chat history updated. full_chat_history: {st.session_state.full_chat_history}, api_chat_history: {st.session_state.api_chat_history}"
            )

            # Extract clean text content from response
            response_content = new_message["content"]
            if isinstance(response_content, dict):
                response_content = response_content.get(
                    "content", str(response_content)
                )

            st.chat_message("assistant", avatar="🤖").write(response_content)

        max_tokens = MAX_TOKENS_ALLOWED
        current_tokens = sum(
            count_tokens(message["content"])
            for message in st.session_state["full_chat_history"]
        )
        logger.info(f"Current token usage: {current_tokens}/{max_tokens}")
        progress = min(1.0, max(0.0, current_tokens / max_tokens))
        st.progress(progress)
        st.write(f"Tokens Used: {current_tokens}/{max_tokens}")
        if current_tokens > max_tokens:
            st.warning(
                "Note: Due to character limits, some older messages might not be considered in ongoing conversations with the AI."
            )
            logger.warning("Token limit exceeded.")

logger.info("End of app.py execution")
