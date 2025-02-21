import tiktoken
import streamlit as st
import json
from typing import Dict, List, Any
from utils.config import AI_MODEL
from utils.api_functions import send_api_request_to_openai_api, execute_function_call
from utils.operation_patterns import match_operation, handle_operation_step
from utils.database_functions import execute_menu_update as db_execute_menu_update, get_db_connection
from utils.menu_analytics import (
    get_recent_operations,
    get_popular_items,
    analyze_time_patterns,
    get_category_relationships
)







def process_chat_message(message: str, history: List[Dict], functions: List[Dict]) -> Dict:
    """Process chat message with error handling
    
    Args:
        message: User message
        history: Chat history
        functions: OpenAI function definitions
        
    Returns:
        Response dict with role and content
    """
    try:
        # Check for operation in progress
        if "current_operation" in st.session_state:
            operation = st.session_state["current_operation"]
            step = operation["steps"][operation["current_step"]]
            response = handle_operation_step(operation, message)
            
            if response:
                if response["role"] == "function":
                    try:
                        # Execute operation
                        result = execute_menu_update(
                            get_db_connection,
                            response["params"]["query"],
                            operation["type"]
                        )
                        # Clear operation state
                        del st.session_state["current_operation"]
                        return {"role": "assistant", "content": result}
                    except Exception as e:
                        return {"role": "assistant", "content": f"Error executing operation: {str(e)}. Please try again."}
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
                history + [{"role": "user", "content": message}],
                functions
            )
            response_json = response.json()
            
            if not response_json.get("choices"):
                return {"role": "assistant", "content": "I encountered an error processing your request. Please try again."}
                
            assistant_message = response_json["choices"][0]["message"]
            
            if assistant_message["role"] == "assistant":
                if assistant_message.get("function_call"):
                    try:
                        results = execute_function_call(assistant_message)
                        return {"role": "assistant", "content": results}
                    except Exception as e:
                        return {"role": "assistant", "content": f"Error executing operation: {str(e)}. Please try again."}
                return assistant_message
            
            return {"role": "assistant", "content": "I encountered an unexpected response. Please try again."}
            
        except Exception as e:
            return {"role": "assistant", "content": f"Error communicating with AI: {str(e)}. Please try again."}
            
    except Exception as e:
        return {"role": "assistant", "content": f"I encountered an error: {str(e)}. Please try again."}

def run_chat_sequence(messages: List[Dict[str, str]], functions: List[Dict[str, Any]], openai_client) -> Dict[str, str]:
    """
    Process a chat sequence with function calling:
    1. Categorize the user's request
    2. Execute appropriate function based on request type
    3. Handle unknown requests with clarifying questions
    """
    # Get the user's latest message
    user_message = messages[-1]["content"] if messages else ""

    # First, categorize the request
    categorize_functions = [f for f in functions if f["name"] == "categorize_request"]
    categorize_response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        functions=categorize_functions,
        function_call={"name": "categorize_request"}
    )
    
    assistant_message = categorize_response.choices[0].message

    # Parse the categorization result
    if assistant_message.function_call:
        args = json.loads(assistant_message.function_call.arguments)
        request_type = args.get("request_type", "unknown")
        item_name = args.get("item_name")
        new_price = args.get("new_price")

        # Log the structured output
        print(f"Recognized request structure:")
        print(f"  Request Type: {request_type}")
        print(f"  Item Name: {item_name}")
        print(f"  New Price: {new_price}" if new_price is not None else "")

        # Handle different request types
        if request_type == "update_price" and item_name and new_price is not None:
            try:
                print(f"\nExecuting price update: Setting {item_name} to ${new_price:.2f}")
                # Updated SQL query to match your database schema
                sql_query = f"""
                    UPDATE items 
                    SET price = {new_price} 
                    WHERE name ILIKE '%{item_name}%' 
                        AND deleted_at IS NULL 
                        AND price >= 0
                """
                return execute_menu_update(messages, functions, sql_query, "update_menu_item", openai_client)
                
            except Exception as e:
                print(f"Error executing menu update: {e}")
                return {
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error while trying to update the price. Please try again or contact support if the issue persists."
                }

        elif request_type == "disable_item" and item_name:
            sql_query = f"UPDATE items SET disabled = true WHERE name ILIKE '%{item_name}%';"
            return execute_menu_update(messages, functions, sql_query, "toggle_menu_item", openai_client)

        elif request_type == "enable_item" and item_name:
            sql_query = f"UPDATE items SET disabled = false WHERE name ILIKE '%{item_name}%';"
            return execute_menu_update(messages, functions, sql_query, "toggle_menu_item", openai_client)

        elif request_type == "query_menu":
            return {
                "role": "assistant",
                "content": "I can help you query the menu. What specific information would you like to know?"
            }

        else:
            # Enhanced fallback logic with specific examples
            help_message = (
                "I'm not quite sure what you'd like to do. Here are the actions I can help with:\n\n"
                "• Update prices (e.g., 'Update the price of French Fries to 9.99')\n"
                "• Disable menu items (e.g., 'Disable the Chicken Wings')\n"
                "• Enable menu items (e.g., 'Enable the Caesar Salad')\n"
                "• Query the menu (e.g., 'Show me all active items')\n\n"
                "Could you please rephrase your request using one of these formats?"
            )
            return {
                "role": "assistant",
                "content": help_message
            }

    # Final fallback for parsing errors
    error_message = (
        "I apologize, but I'm having trouble processing your request. "
        "Please make sure your message includes:\n"
        "• The action you want to take (update/enable/disable/query)\n"
        "• The item name (if applicable)\n"
        "• The new price (for price updates)\n\n"
        "For example: 'Update the price of French Fries to 9.99'"
    )
    return {
        "role": "assistant",
        "content": error_message
    }

def execute_menu_update(messages: List[Dict[str, str]], 
                       functions: List[Dict[str, Any]], 
                       sql_query: str, 
                       function_name: str,
                       openai_client) -> Dict[str, str]:
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
                    "content": f"✅ Successfully updated the price. {result}"
                }
            elif function_name == "toggle_menu_item":
                action = "enabled" if "disabled = false" in sql_query else "disabled"
                return {
                    "role": "assistant",
                    "content": f"✅ Successfully {action} the menu item. {result}"
                }
        else:
            operation_type = "price update" if function_name == "update_menu_item" else "status update"
            return {
                "role": "assistant",
                "content": f"❌ Failed to perform {operation_type}: {result}"
            }
            
    except Exception as e:
        print(f"Database error: {e}")
        operation_type = "price update" if function_name == "update_menu_item" else "status update"
        return {
            "role": "assistant",
            "content": f"❌ Sorry, I encountered a database error during {operation_type}: {str(e)}"
        }
    finally:
        if conn:
            conn.close()

def clear_chat_history():
    """ Clear the chat history stored in the Streamlit session state """
    del st.session_state["live_chat_history"]
    del st.session_state["full_chat_history"]
    del st.session_state["api_chat_history"]


def count_tokens(text):
    """ Count the total tokens used in a text string """
    if not isinstance(text, str):  
        return 0 
    encoding = tiktoken.encoding_for_model(AI_MODEL)
    total_tokens_in_text_string = len(encoding.encode(text))
    
    return total_tokens_in_text_string


def prepare_sidebar_data(database_schema_dict):
    """ Add a sidebar for visualizing the database schema objects  """
    sidebar_data = {}
    for table in database_schema_dict:
        schema_name = table["schema_name"]
        table_name = table["table_name"]
        columns = table["column_names"]

        if schema_name not in sidebar_data:
            sidebar_data[schema_name] = {}

        sidebar_data[schema_name][table_name] = columns
    return sidebar_data

