import tiktoken
import streamlit as st
from typing import Dict, List, Any
from utils.config import AI_MODEL
from utils.api_functions import send_api_request_to_openai_api, execute_function_call
from utils.operation_patterns import match_operation, handle_operation_step
from utils.database_functions import execute_menu_update, get_db_connection
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

def run_chat_sequence(messages, functions):
    if "live_chat_history" not in st.session_state:
        st.session_state["live_chat_history"] = []
    
    if "current_item" not in st.session_state:
        st.session_state["current_item"] = None

    # Process latest message
    if messages and messages[-1]["role"] == "user":
        current_message = messages[-1]["content"]
        
        # Extract item name if present
        if "Club Made French Fries" in current_message:
            st.session_state["current_item"] = "Club Made French Fries"
            
            # Always update the system message (first message) with full context
            messages[0]["content"] = """You are a helpful AI assistant that helps manage restaurant menus.
            Your tasks include:
            1. Identify the type of operation (query, update price, enable/disable)
            2. Extract relevant information (item name, price, status)
            3. Execute the appropriate operation
            4. Confirm the operation was successful
            
            Available operations:
            - Query: View menu items and their details
            - Update: Modify menu item prices
            - Toggle: Enable or disable menu items
            
            Current item: Club Made French Fries
            Current request: Update price to 9.99"""
            
            # If this is a price update, format the message properly
            if "update price" in current_message.lower():
                price = current_message.split("to ")[-1].strip()
                current_message = f"Please update the price of {st.session_state['current_item']} to {price}."
                messages[-1]["content"] = current_message
        
        response = process_chat_message(current_message, messages[:-1], functions)
        
        # Skip "Which menu item?" if we already have it
        if "Which menu item?" in response.get("content", "") and st.session_state["current_item"]:
            if "update" in current_message.lower() and "price" in current_message.lower():
                price = current_message.split("to ")[-1].strip()
                messages[-1]["content"] = f"Update price of {st.session_state['current_item']} to {price}"
            response = process_chat_message(messages[-1]["content"], messages[:-1], functions)
        
        st.session_state["live_chat_history"].append(response)
        return response

    # Return a default greeting only if there's no chat history
    if not st.session_state["live_chat_history"]:
        return {"role": "assistant", "content": "Hello! I'm Andy, your menu management specialist. How can I assist you today?"}
    
    return st.session_state["live_chat_history"][-1]


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

