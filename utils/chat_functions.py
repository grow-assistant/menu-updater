import tiktoken
import streamlit as st
from utils.config import AI_MODEL
from utils.api_functions import send_api_request_to_openai_api, execute_function_call
from utils.menu_analytics import (
    get_recent_operations,
    get_popular_items,
    analyze_time_patterns,
    get_category_relationships
)







def run_chat_sequence(messages, functions):
    if "live_chat_history" not in st.session_state:
        st.session_state["live_chat_history"] = [{"role": "assistant", "content": "Hello! I'm Andy, how can I assist you?"}]
        # st.session_state["live_chat_history"] = []

    internal_chat_history = st.session_state["live_chat_history"].copy()
    
    # Make a copy of messages to avoid modifying the original
    messages = messages.copy()

    # Add enhanced context if location_id available
    if "location_id" in st.session_state and "postgres_connection" in st.session_state:
        location_id = st.session_state["location_id"]
        connection = st.session_state["postgres_connection"]
        
        # Get context data
        context = {
            'recent_operations': get_recent_operations(connection, location_id, limit=10),
            'popular_items': get_popular_items(connection, location_id),
            'time_patterns': analyze_time_patterns(connection, location_id),
            'category_relationships': get_category_relationships(connection, location_id)
        }
        
        # Format context sections
        context_sections = []
        
        # Format operations
        if context['recent_operations']:
            ops = "\n".join(f"- {op['operation_type']}: {op['operation_name']} ({op['result_summary']})"
                          for op in context['recent_operations'])
            context_sections.append(f"Recent operations:\n{ops}")
        
        # Format popular items
        if context['popular_items']:
            items = "\n".join(f"- {item['name']} (${item['price']:.2f}, {item['orders']} orders)"
                           for item in context['popular_items'])
            context_sections.append(f"Popular items:\n{items}")
        
        # Format time patterns
        if 'time_based_categories' in context['time_patterns']:
            patterns = "\n".join(f"- {p['category']} ({p['time_range']}: {p['orders']} orders)"
                              for p in context['time_patterns']['time_based_categories'])
            context_sections.append(f"Time-based patterns:\n{patterns}")
        
        # Format category relationships
        if context['category_relationships']:
            relationships = []
            for cat1, related in context['category_relationships'].items():
                related_str = ", ".join(f"{r['category']} ({r['frequency']} orders)" 
                                      for r in related[:3])
                relationships.append(f"- {cat1} often ordered with: {related_str}")
            if relationships:
                context_sections.append("Category relationships:\n" + "\n".join(relationships))
        
        # Add context to message
        if context_sections:
            context_str = "Context:\n" + "\n\n".join(context_sections)
            messages[-1]["content"] = context_str + "\n\nUser query: " + messages[-1]["content"]

    # Add query template context if available
    if "query_template" in st.session_state:
        messages[-1]["content"] += f"\nUse this query template: {st.session_state['query_template']}"
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

