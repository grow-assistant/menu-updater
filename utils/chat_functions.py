import streamlit as st
import os
import tiktoken
import json
import datetime
from typing import Dict, List, Any
from utils.config import AI_MODEL
from utils.api_functions import send_api_request_to_openai_api, execute_function_call
from utils.operation_patterns import match_operation, handle_operation_step
from utils.database_functions import (
    execute_menu_update as db_execute_menu_update,
    get_db_connection,
    execute_menu_query,
)
import logging
from pathlib import Path
from utils.create_sql_statement import generate_sql_from_user_query
import requests

# Set up logging
# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Clear existing handlers to prevent duplicate logging
logging.getLogger().handlers.clear()

# Get current timestamp for the log file
current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = f"logs/openai_chat_{current_time}.log"

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        # File handler - new file each run with timestamp
        logging.FileHandler(
            filename=log_file,
            mode="w",  # 'w' mode overwrites the file each time
            encoding="utf-8",
        ),
        # Console handler
        logging.StreamHandler(),
    ],
)

# Start the log file with a header
logger = logging.getLogger(__name__)
logger.info(f"=== New Session Started at {current_time} ===")
logger.info("Logging initialized with fresh log file")


def log_openai_interaction(messages: List[Dict], response: Any, interaction_type: str):
    """Log OpenAI API interactions for debugging and auditing"""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "type": interaction_type,
        "messages": messages,
        "response": (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        ),
    }

    # Pretty print the log entry
    formatted_log = (
        f"\n{'='*80}\n"
        f"INTERACTION TYPE: {interaction_type}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGES:\n{json.dumps(messages, indent=2)}\n"
        f"RESPONSE:\n{json.dumps(log_entry['response'], indent=2)}\n"
        f"{'='*80}\n"
    )

    logger.info(formatted_log)


def execute_order_query(query: str) -> str:
    """Execute order-related database queries"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        return f"Error executing query: {str(e)}"
    finally:
        if conn:
            conn.close()


def process_chat_message(
    message: str, history: List[Dict], functions: List[Dict]
) -> Dict:
    """Process chat messages and determine appropriate action"""
    try:
        # Check for operation in progress
        if "current_operation" in st.session_state:
            operation = st.session_state["current_operation"]
            response = handle_operation_step(operation, message)

            if response:
                if response["role"] == "function":
                    try:
                        # Execute operation
                        result = execute_menu_update(
                            get_db_connection,
                            response["params"]["query"],
                            operation["type"],
                        )
                        # Clear operation state
                        del st.session_state["current_operation"]
                        return {"role": "assistant", "content": result}
                    except Exception as e:
                        return {
                            "role": "assistant",
                            "content": f"Error executing operation: {str(e)}. Please try again.",
                        }
                else:
                    operation["current_step"] += 1
                    st.session_state["current_operation"] = operation
                    return response

        # Try to match new operation
        if operation := match_operation(message):
            operation["current_step"] = 0
            st.session_state["current_operation"] = operation
            return handle_operation_step(operation, message)

        # Fallback to OpenAI
        try:
            response = send_api_request_to_openai_api(
                history + [{"role": "user", "content": message}], functions
            )
            response_json = response.json()

            if not response_json.get("choices"):
                return {
                    "role": "assistant",
                    "content": "I encountered an error processing your request. Please try again.",
                }

            assistant_message = response_json["choices"][0]["message"]

            if assistant_message["role"] == "assistant":
                if assistant_message.get("function_call"):
                    try:
                        results = execute_function_call(assistant_message)
                        return {"role": "assistant", "content": results}
                    except Exception as e:
                        return {
                            "role": "assistant",
                            "content": f"Error executing operation: {str(e)}. Please try again.",
                        }
                return assistant_message

            return {
                "role": "assistant",
                "content": "I encountered an unexpected response. Please try again.",
            }

        except Exception as e:
            return {
                "role": "assistant",
                "content": f"Error communicating with AI: {str(e)}. Please try again.",
            }

    except Exception as e:
        return {
            "role": "assistant",
            "content": f"I encountered an error: {str(e)}. Please try again.",
        }


def process_query_results(result: dict, xai_client: dict, user_question: str) -> str:
    """Process query results and format as human-readable response"""
    try:
        data = result.get("results", [])
        prompt = (
            "You are a data translator. Convert these database results into a natural language answer.\n\n"
            "Example 1:\n"
            "Input: [{'count': 3}]\n"
            "Output: There were 3 orders completed yesterday.\n\n"
            "Example 2:\n"
            "Input: [{'sum': 149.99}]\n"
            "Output: The total revenue last month was $149.99.\n\n"
            "Now, convert the following data into a natural language answer:\n"
            f"{json.dumps(data)}\n"
            f"User question: {user_question}"
        )

        response = requests.post(
            xai_client["XAI_API_URL"],
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": xai_client["XAI_MODEL"],
                "temperature": 0.3,
            },
            headers={
                "Authorization": f"Bearer {xai_client['XAI_TOKEN']}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        summary_response = response.json()["choices"][0]["message"]["content"]
        summary_content = summary_response.get(
            "content", summary_response
        )  # Extract inner content

        return {"role": "assistant", "content": f"{summary_content}"}

    except Exception as e:
        logger.error(f"XAI summarization failed: {str(e)}")
        return f"Found {len(data)} matching records: {data}"


def run_chat_sequence(
    messages: List[Dict[str, str]],
    functions: List[Dict[str, Any]],
    openai_client,
    grok_client,
) -> Dict[str, str]:
    """Run a sequence of chat operations with OpenAI API"""
    user_message = messages[-1]["content"] if messages else ""

    logger.info(f"\n{'='*50}\nNew Chat Request: {user_message}\n{'='*50}")

    try:
        # For example, checking if a location is selected (your logic might vary)
        location_id = 62  # For demonstration; in practice, use the real location_id from session state.
        if not location_id:
            return {
                "role": "assistant",
                "content": "Please select a location first to view order information.",
            }

        # Categorize user request by calling the categorization function (as you already do)
        categorize_functions = [
            f for f in functions if f["name"] == "categorize_request"
        ]
        categorize_response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            functions=categorize_functions,
            function_call={"name": "categorize_request"},
        )

        # Log the OpenAI interaction for categorization
        logger.info("Received categorization response.")
        assistant_message = categorize_response.choices[0].message
        if assistant_message.function_call:
            args = json.loads(assistant_message.function_call.arguments)
            request_type = args.get("request_type", "unknown")
            order_metric = args.get("order_metric")
            logger.info(f"Request type: {request_type}")

            # ------------------------------
            # Query Handling via Gemini
            # ------------------------------
            if request_type in ["query_orders", "query_menu"]:
                # Generate SQL query using Gemini
                sql_query = generate_sql_from_user_query(user_message, location_id)

                logger.info(f"Generated SQL query via Gemini: {sql_query}")

                # Execute the SQL query
                result = execute_menu_query(sql_query)

                logger.info(f"Raw SQL results: {json.dumps(result)}")

                # Process and summarize the results using Grok
                summary = process_query_results(result, grok_client, user_message)
                summary_content = summary.get(
                    "content", summary
                )  # Extract inner content

                logger.info(f"Summary: {summary_content}")
                return {"role": "assistant", "content": summary_content}

            # ------------------------------
            # Query Handling with Preset Order Metrics
            # (Your already-implemented branches based on specific metrics)
            # ------------------------------
            elif (
                request_type == "query_orders"
                and order_metric == "completed_orders"
                and args.get("date")
            ):
                query = f"""
                    SELECT COUNT(*) as completed_orders
                    FROM orders
                    WHERE location_id = {location_id}
                      AND status = 7  -- Assuming 7 means 'Completed'
                      AND DATE(created_at) = '{args.get("date")}';
                """
                logger.info(f"Executing query: {query}")
                result = execute_menu_query(query)
                if result["success"] and result["results"]:
                    completed_orders = result["results"][0].get("completed_orders", 0)
                    response = f"There were {completed_orders} orders completed on {args.get('date')} for location ID {location_id}."
                    logger.info(f"Final response: {response}")
                    return {"role": "assistant", "content": response}
                else:
                    error_msg = f"No data found for location #{location_id} on {args.get('date')}."
                    logger.warning(error_msg)
                    return {"role": "assistant", "content": error_msg}

            # ------------------------------
            # Menu Updates (e.g., price changes, enable/disable)
            # ------------------------------
            elif request_type in ["update_price", "disable_item", "enable_item"]:
                # The existing approach: Construct UPDATE queries and execute them.
                if (
                    request_type == "update_price"
                    and args.get("item_name")
                    and args.get("new_price") is not None
                ):
                    sql_query = f"""
                        UPDATE items
                        SET price = {args['new_price']}
                        WHERE name ILIKE '%{args['item_name']}%'
                            AND deleted_at IS NULL
                            AND price >= 0;
                    """
                    return execute_menu_update(
                        messages,
                        functions,
                        sql_query,
                        "update_menu_item",
                        openai_client,
                    )
                elif request_type == "disable_item" and args.get("item_name"):
                    sql_query = f"UPDATE items SET disabled = true WHERE name ILIKE '%{args['item_name']}%';"
                    return execute_menu_update(
                        messages,
                        functions,
                        sql_query,
                        "toggle_menu_item",
                        openai_client,
                    )
                elif request_type == "enable_item" and args.get("item_name"):
                    sql_query = f"UPDATE items SET disabled = false WHERE name ILIKE '%{args['item_name']}%';"
                    return execute_menu_update(
                        messages,
                        functions,
                        sql_query,
                        "toggle_menu_item",
                        openai_client,
                    )

            # ------------------------------
            # Fallback / Help Message
            # ------------------------------
            else:
                help_message = (
                    "I'm not quite sure what you'd like to do. Here are the actions I can help with:\n\n"
                    "• Update prices (e.g., 'Update the price of French Fries to 9.99')\n"
                    "• Disable menu items (e.g., 'Disable the Chicken Wings')\n"
                    "• Enable menu items (e.g., 'Enable the Caesar Salad')\n"
                    "• Query orders/menu (e.g., 'Show today's orders' or 'Query the menu')\n\n"
                    "Could you please rephrase your request?"
                )
                return {"role": "assistant", "content": help_message}
        else:
            return {
                "role": "assistant",
                "content": "Sorry, I couldn't determine your request. Could you please rephrase?",
            }

    except Exception as e:
        logger.error(f"Error in chat sequence: {str(e)}", exc_info=True)
        return {
            "role": "assistant",
            "content": "Sorry, I encountered an error. Please try again or contact support.",
        }


def execute_menu_update(
    messages: List[Dict[str, str]],
    functions: List[Dict[str, Any]],
    sql_query: str,
    function_name: str,
    openai_client,
) -> Dict[str, str]:
    """Helper function to execute menu updates with the appropriate function"""
    try:
        # Get database connection
        conn = get_db_connection()

        # Execute the update query
        result = db_execute_menu_update(conn, sql_query, operation_name=function_name)

        if "successful" in result.lower():
            # Customize message based on operation type
            if function_name == "update_menu_item":
                return {
                    "role": "assistant",
                    "content": f"✅ Successfully updated the price. {result}",
                }
            elif function_name == "toggle_menu_item":
                action = "enabled" if "disabled = false" in sql_query else "disabled"
                return {
                    "role": "assistant",
                    "content": f"✅ Successfully {action} the menu item. {result}",
                }
        else:
            operation_type = (
                "price update"
                if function_name == "update_menu_item"
                else "status update"
            )
            return {
                "role": "assistant",
                "content": f"❌ Failed to perform {operation_type}: {result}",
            }

    except Exception as e:
        print(f"Database error: {e}")
        operation_type = (
            "price update" if function_name == "update_menu_item" else "status update"
        )
        return {
            "role": "assistant",
            "content": f"❌ Sorry, I encountered a database error during {operation_type}: {str(e)}",
        }
    finally:
        if conn:
            conn.close()


def clear_chat_history():
    """Clear the chat history stored in the Streamlit session state"""
    del st.session_state["live_chat_history"]
    del st.session_state["full_chat_history"]
    del st.session_state["api_chat_history"]


def count_tokens(text):
    """Count the total tokens used in a text string"""
    if not isinstance(text, str):
        return 0
    encoding = tiktoken.encoding_for_model(AI_MODEL)
    total_tokens_in_text_string = len(encoding.encode(text))

    return total_tokens_in_text_string


def prepare_sidebar_data(database_schema_dict):
    """Add a sidebar for visualizing the database schema objects"""
    sidebar_data = {}
    for table in database_schema_dict:
        schema_name = table["schema_name"]
        table_name = table["table_name"]
        columns = table["column_names"]

        if schema_name not in sidebar_data:
            sidebar_data[schema_name] = {}

        sidebar_data[schema_name][table_name] = columns
    return sidebar_data


def call_grok(prompt: str) -> str:
    """Make a call to the XAI Grok API"""
    try:
        # Get environment variables
        xai_token = os.getenv("XAI_TOKEN")
        xai_url = os.getenv("XAI_API_URL")
        xai_model = os.getenv("XAI_MODEL")

        # Validate configuration
        if not all([xai_token, xai_url, xai_model]):
            raise ValueError("Missing XAI environment variables")

        # Construct the payload
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that converts database results into natural language answers.",
                },
                {"role": "user", "content": prompt},
            ],
            "model": xai_model,
            "temperature": 0.3,
            "stream": False,
        }

        # Make the API call
        response = requests.post(
            xai_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {xai_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"XAI API call failed: {str(e)}")
        return None


def save_conversation(messages, directory="conversations"):
    """Save conversation history to a JSON file"""
    try:
        os.makedirs(directory, exist_ok=True)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{directory}/conversation_{current_time}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)
        
        return True, filename
    except Exception as e:
        return False, str(e)


def add_user_feedback(conversation_id, query, response, feedback, notes=""):
    """Add user feedback about an AI response to the feedback log"""
    try:
        os.makedirs("feedback", exist_ok=True)
        feedback_file = "feedback/user_feedback.json"
        
        # Create feedback entry
        timestamp = datetime.datetime.now().isoformat()
        feedback_entry = {
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "feedback": feedback,
            "notes": notes
        }

        # Append to existing feedback file
        with open(feedback_file, 'a', encoding='utf-8') as f:
            json.dump(feedback_entry, f)
            f.write('\n')
        
        return True, f"Feedback added successfully. Feedback ID: {timestamp}"
    except Exception as e:
        return False, str(e)
