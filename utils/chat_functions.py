import tiktoken
import streamlit as st
from utils.config import AI_MODEL
from utils.api_functions import send_api_request_to_openai_api, execute_function_call
from utils.database_functions import get_location_settings
from utils.menu_operations import get_operation_history







def run_chat_sequence(messages, functions):
    if "live_chat_history" not in st.session_state:
        st.session_state["live_chat_history"] = [{"role": "assistant", "content": "Hello! I'm Andy, how can I assist you?"}]
        # st.session_state["live_chat_history"] = []

    internal_chat_history = st.session_state["live_chat_history"].copy()

    # Make a copy of messages to avoid modifying the original
    messages = messages.copy()

    # Add operation history context if available
    if "location_id" in st.session_state and "postgres_connection" in st.session_state:
        settings = get_location_settings(st.session_state["postgres_connection"], st.session_state["location_id"])
        history = get_operation_history(settings)
        if history:
            # Add last 5 operations as context
            context = "Recent operations:\n" + "\n".join(
                f"- {op['operation_type']}: {op['operation_name']} ({op['result_summary']})"
                for op in history[:5]
            )
            messages[-1]["content"] = context + "\n\n" + messages[-1]["content"]

    # Add query template context if available
    if "query_template" in st.session_state:
        # Add template to the last user message
        messages[-1]["content"] += f"\nUse this query template: {st.session_state['query_template']}"
        # Clear template after adding to prevent reuse
        del st.session_state["query_template"]

    chat_response = send_api_request_to_openai_api(messages, functions)
    assistant_message = chat_response.json()["choices"][0]["message"]
    
    if assistant_message["role"] == "assistant":
        internal_chat_history.append(assistant_message)

    if assistant_message.get("function_call"):
        results = execute_function_call(assistant_message)
        internal_chat_history.append({"role": "function", "name": assistant_message["function_call"]["name"], "content": results})
        internal_chat_history.append({"role": "user", "content": "You are a data analyst - provide personalized/customized explanations on what the results provided means and link them to the the context of the user query using clear, concise words in a user-friendly way. Or answer the question provided by the user in a helpful manner - either way, make sure your responses are human-like and relate to the initial user input. Your answers must not exceed 200 characters"})
        chat_response = send_api_request_to_openai_api(internal_chat_history, functions)
        assistant_message = chat_response.json()["choices"][0]["message"]
        if assistant_message["role"] == "assistant":
            st.session_state["live_chat_history"].append(assistant_message)

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

