import streamlit as st
from utils.config import db_credentials, MAX_TOKENS_ALLOWED, MAX_MESSAGES_TO_OPENAI, TOKEN_BUFFER
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import run_chat_sequence, clear_chat_history, count_tokens, prepare_sidebar_data
from utils.database_functions import (
    get_db_connection,
    execute_menu_query,
    database_schema_dict
)
from utils.function_calling_spec import functions
from utils.helper_functions import save_conversation
from utils.ui_components import (
    render_price_input,
    render_time_input,
    render_option_limits,
    validate_menu_update
)
from assets.dark_theme import dark
from assets.light_theme import light
from assets.made_by_sdw import made_by_sdw
import pandas as pd
from openai import OpenAI
import os
from itertools import takewhile

def get_recent_messages():
    """Get recent messages that fit within token limits"""
    messages = st.session_state["api_chat_history"]
    if not messages:
        # Always include at least the system message
        return [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials)}]
        
    total_tokens = 0
    
    # Count tokens from newest to oldest until we hit the limit
    for i in range(len(messages)-1, -1, -1):
        tokens = count_tokens(messages[i]["content"])
        if total_tokens + tokens > MAX_MESSAGES_TO_OPENAI - TOKEN_BUFFER:
            return messages[i+1:] if i+1 < len(messages) else messages[-1:]
        total_tokens += tokens
    
    return messages

if __name__ == "__main__":

    # Initialize session state variables
    if "operation" not in st.session_state:
        st.session_state["operation"] = None

    if "selected_location_id" not in st.session_state:
        st.session_state["selected_location_id"] = None

    if "full_chat_history" not in st.session_state:
        st.session_state["full_chat_history"] = [
            {"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials)},
            {"role": "assistant", "content": "Hello! I'm your menu management assistant. How can I help you today? I can:\n\n"
             "• Update menu item prices\n"
             "• Enable/disable menu items\n"
             "• Show menu information\n"
             "\nWhat would you like to do?"}
        ]

    if "api_chat_history" not in st.session_state:
        st.session_state["api_chat_history"] = [
            {"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials)},
            {"role": "assistant", "content": "Hello! I'm your menu management assistant. How can I help you today?"}
        ]

    # Ensure openai_client is available in the global scope
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ########### A. SIDEBAR ###########

    # Add location selector at the top of sidebar
    st.sidebar.title("📍 Location Selection")
    try:
        location_query = """
            SELECT id, name 
            FROM locations 
            WHERE deleted_at IS NULL 
            ORDER BY id DESC
        """
        query_result = execute_menu_query(location_query)
        
        if query_result["success"] and query_result["results"]:
            locations = query_result["results"]  # This is now a list of dicts with 'id' and 'name' keys
            
            # Create a list of location options in "id - name" format
            location_options = ["All"] + [f"{loc['id']} - {loc['name']}" for loc in locations]
            
            # Find the index of location 16 in the options list
            default_index = next((i for i, opt in enumerate(location_options) if opt.startswith("16 -")), 0)
            
            selected_location = st.sidebar.selectbox(
                "Select Location",
                options=location_options,
                index=default_index
            )
            
            # Extract the location ID from the selection
            if selected_location != "All":
                selected_location_id = int(selected_location.split(" - ")[0])
                st.session_state["selected_location_id"] = selected_location_id
            else:
                st.session_state["selected_location_id"] = None

        else:
            st.sidebar.error("No locations found in database")
            
    except Exception as e:
        st.sidebar.error(f"Error loading locations: {str(e)}")

    st.sidebar.markdown("---")  # Add a visual separator

    # Prepare data for the sidebar dropdowns
    sidebar_data = prepare_sidebar_data(database_schema_dict)
    st.sidebar.markdown("<div class='made_by'>Made by SDW🔋</div>", unsafe_allow_html=True)

    ### MENU OPERATIONS ###
    st.sidebar.title("🍽️ Menu Operations")
    
    # Add custom CSS for tooltips
    st.markdown("""
        <style>
        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            background-color: #555;
            color: #fff;
            text-align: center;
            padding: 5px;
            border-radius: 6px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -60px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # All operations are now handled through chat interface
    # Users can query menu items by asking in the chat

    # Apply dark theme by default
    st.markdown(dark, unsafe_allow_html=True)

    ########### B. CHAT INTERFACE ###########
    
    ### TITLE ###
    st.title("Swoop AI Assistant")

    ### CHAT FACILITATION ###
    if (prompt := st.chat_input("What do you want to know?")) is not None:
        # Add the user message to chat history
        st.session_state.full_chat_history.append({"role": "user", "content": prompt})
        st.session_state.api_chat_history.append({"role": "user", "content": prompt})

    # Display previous chat messages from full_chat_history (ignore system prompt message)
    for message in st.session_state["full_chat_history"][1:]:
        if message["role"] == "user":
            st.chat_message("user", avatar='🧑‍💻').write(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant", avatar='🤖').write(message["content"])

    if st.session_state["api_chat_history"][-1]["role"] != "assistant":
        with st.spinner("⌛Connecting to AI model..."):
            # Get recent messages
            recent_messages = get_recent_messages()
            
            # Call run_chat_sequence with the OpenAI client
            new_message = run_chat_sequence(recent_messages, functions, openai_client)
            
            # Add this latest message to both api_chat_history and full_chat_history
            st.session_state["api_chat_history"].append(new_message)
            st.session_state["full_chat_history"].append(new_message)

            # Display the latest message from the assistant
            st.chat_message("assistant", avatar='🤖').write(new_message["content"])

        max_tokens = MAX_TOKENS_ALLOWED
        current_tokens = sum(count_tokens(message["content"]) for message in st.session_state["full_chat_history"])
        progress = min(1.0, max(0.0, current_tokens / max_tokens))
        st.progress(progress)
        st.write(f"Tokens Used: {current_tokens}/{max_tokens}")
        if current_tokens > max_tokens:
            st.warning("Note: Due to character limits, some older messages might not be considered in ongoing conversations with the AI.")
