import streamlit as st
from utils.config import db_credentials, MAX_TOKENS_ALLOWED, MAX_MESSAGES_TO_OPENAI, TOKEN_BUFFER
import psycopg2
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import run_chat_sequence, clear_chat_history, count_tokens, prepare_sidebar_data
from utils.database_functions import database_schema_dict, get_location_settings
from utils.menu_operations import get_location_operations, get_operation_history
from utils.function_calling_spec import functions
from utils.helper_functions import  save_conversation
from assets.dark_theme import dark
from assets.light_theme import light
from assets.made_by_sdw import made_by_sdw





if __name__ == "__main__":
    # Initialize database connection
    postgres_connection = psycopg2.connect(**db_credentials)

    ########### A. SIDEBAR ###########

    # Prepare data for the sidebar dropdowns
    sidebar_data = prepare_sidebar_data(database_schema_dict)
    st.sidebar.markdown("<div class='made_by'>Made by SDW🔋</div>", unsafe_allow_html=True)

    ### MENU OPERATIONS ###
    st.sidebar.title("🍽️ Menu Operations")
    
    # Common operations section
    st.sidebar.subheader("⭐ Common Operations")
    location_id = st.sidebar.number_input("Location ID", min_value=1, step=1)
    
    if location_id:
        settings = get_location_settings(postgres_connection, location_id)
        operations = get_location_operations(settings)
        
        # Operation history section
        st.sidebar.subheader("📜 Recent Operations")
        history = get_operation_history(settings)
        for entry in history[:5]:
            st.sidebar.text(
                f"{entry['operation_type'].title()}: {entry['operation_name']}\n"
                f"Result: {entry['result_summary']}"
            )
        
        # Queries section
        st.sidebar.write("📊 Common Queries")
        for query in operations["queries"]:
            if st.sidebar.button(f"🔍 {query['name']}", key=f"query_{query['name']}"): 
                st.session_state["operation"] = "query"
                st.session_state["query_template"] = query["query_template"]
        
        # Updates section
        st.sidebar.write("✏️ Common Updates")
        for update in operations["updates"]:
            if st.sidebar.button(f"✏️ {update['name']}", key=f"update_{update['name']}"): 
                st.session_state["operation"] = "update"
                st.session_state["query_template"] = update["query_template"]
    
    # Quick actions
    st.sidebar.subheader("🚀 Quick Actions")
    if st.sidebar.button("🔍 View All Items"):
        operation = "query"
        st.session_state["operation"] = "query"
    if st.sidebar.button("💰 Update Prices"):
        operation = "update"
        st.session_state["operation"] = "update"
    if st.sidebar.button("⚡ Enable/Disable Items"):
        operation = "toggle"
        st.session_state["operation"] = "toggle"
    
    # Display current operation
    if "operation" in st.session_state:
        st.sidebar.info(f"Current Operation: {st.session_state['operation'].title()}")

    ### POSTGRES DB OBJECTS VIEWER ###
    st.markdown(made_by_sdw, unsafe_allow_html=True)
    st.sidebar.title("📊 Database Structure")


    # Dropdown for schema selection
    selected_schema = st.sidebar.selectbox("📂 Select a schema", list(sidebar_data.keys()))


    # Dropdown for table selection based on chosen Schema
    selected_table = st.sidebar.selectbox("📜 Select a table", list(sidebar_data[selected_schema].keys()))


    # Display columns of the chosen table with interactivity using checkboxes
    st.sidebar.subheader(f"🔗 Columns in {selected_table}")
    for column in sidebar_data[selected_schema][selected_table]:
        is_checked = st.sidebar.checkbox(f"📌 {column}") 





    ### SAVE CONVERSATION BUTTON ###

    # Add a button to SAVE the chat/conversation
    if st.sidebar.button("Save Conversation💾"):
        saved_file_path = save_conversation(st.session_state["full_chat_history"])
        st.sidebar.success(f"Conversation saved to: {saved_file_path}")
        st.sidebar.markdown(f"Conversation saved! [Open File]({saved_file_path})")

    
    
    

    ### CLEAR CONVERSATION BUTTON ###

    # Add a button to CLEAR the chat/conversation
    if st.sidebar.button("Clear Conversation🗑️"):
        save_conversation(st.session_state["full_chat_history"]) 
        clear_chat_history()





    ### TOGGLE THEME BUTTON ###

    # Retrieve the current theme from session state
    current_theme = st.session_state.get("theme", "light")
    st.markdown(f"<body class='{current_theme}'></body>", unsafe_allow_html=True)


    # Initialize the theme in session state
    if "theme" not in st.session_state:
        st.session_state.theme = "light"


    # Add a button to toggle the UI colour theme
    if st.sidebar.button("Toggle Theme🚨"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.experimental_rerun()



    # Apply the theme based on session state
    theme_style = dark if st.session_state.theme == "dark" else light
    st.markdown(theme_style, unsafe_allow_html=True)











    ########### B. CHAT INTERFACE ###########


    
    ### TITLE ###

    # Add title to the Streamlit chatbot app
    st.title("🤖 AI Database Chatbot 🤓")



    ### SESSION STATE ###

    # Initialize the full chat messages history for UI
    if "full_chat_history" not in st.session_state:
        st.session_state["full_chat_history"] = [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials)}]



    # Initialize the API chat messages history for OpenAI requests
    if "api_chat_history" not in st.session_state:
        st.session_state["api_chat_history"] = [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials)}]



    ### CHAT FACILITATION ###

    # Start the chat
    if (prompt := st.chat_input("What do you want to know?")) is not None:
        st.session_state.full_chat_history.append({"role": "user", "content": prompt})

        # Limit the number of messages sent to OpenAI by token count
        total_tokens = sum(count_tokens(message["content"]) for message in st.session_state["api_chat_history"])
        while total_tokens + count_tokens(prompt) + TOKEN_BUFFER > MAX_TOKENS_ALLOWED:
            removed_message = st.session_state["api_chat_history"].pop(0)
            total_tokens -= count_tokens(removed_message["content"])

        st.session_state.api_chat_history.append({"role": "user", "content": prompt})



    # Display previous chat messages from full_chat_history (ingore system prompt message)
    for message in st.session_state["full_chat_history"][1:]:
        if message["role"] == "user":
            st.chat_message("user", avatar='🧑‍💻').write(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant", avatar='🤖').write(message["content"])

    if st.session_state["api_chat_history"][-1]["role"] != "assistant":
        with st.spinner("⌛Connecting to AI model..."):
            # Send only the most recent messages to OpenAI from api_chat_history
            recent_messages = st.session_state["api_chat_history"][-MAX_MESSAGES_TO_OPENAI:]
            
            # Add operation context if set
            if "operation" in st.session_state:
                operation_context = {
                    "query": "I want to view menu items. ",
                    "update": "I want to update menu prices. ",
                    "toggle": "I want to enable or disable menu items. "
                }.get(st.session_state["operation"], "")
                if operation_context:
                    recent_messages[-1]["content"] = operation_context + recent_messages[-1]["content"]
            
            new_message = run_chat_sequence(recent_messages, functions)  # Get the latest message

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
    
    # Close database connection when app exits
    if "postgres_connection" in locals():
        postgres_connection.close()
