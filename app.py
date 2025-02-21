import streamlit as st
from utils.config import db_credentials, MAX_TOKENS_ALLOWED, MAX_MESSAGES_TO_OPENAI, TOKEN_BUFFER
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import run_chat_sequence, clear_chat_history, count_tokens, prepare_sidebar_data
from utils.database_functions import database_schema_dict, execute_menu_query
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





if __name__ == "__main__":

    ########### A. SIDEBAR ###########

    # Add location selector at the top of sidebar
    st.sidebar.title("📍 Location Selection")
    try:
        # Query to get locations, ordered by ID descending
        location_query = """
            SELECT id, name 
            FROM locations 
            WHERE deleted_at IS NULL 
            ORDER BY id DESC
        """
        locations = execute_menu_query(location_query)
        
        if locations:
            # Create a list of location options in "id - name" format
            location_options = ["All"] + [f"{loc['id']} - {loc['name']}" for loc in locations]
            
            # Find the index of location 62 in the options list
            default_index = next((i for i, opt in enumerate(location_options) if opt.startswith("62 -")), 0)
            
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

            # Menu Dropdown
            menu_query = """
                SELECT id, name 
                FROM menus 
                WHERE deleted_at IS NULL 
                AND location_id = %s
                ORDER BY name
            """
            menus = execute_menu_query(menu_query, (st.session_state.get("selected_location_id"),)) if st.session_state.get("selected_location_id") else []
            menu_options = ["All"] + [f"{menu['id']} - {menu['name']}" for menu in menus]
            selected_menu = st.sidebar.selectbox("Select Menu", menu_options)
            
            if selected_menu != "All":
                selected_menu_id = int(selected_menu.split(" - ")[0])
                st.session_state["selected_menu_id"] = selected_menu_id
            else:
                st.session_state["selected_menu_id"] = None

            # Category Dropdown
            category_query = """
                SELECT id, name 
                FROM categories 
                WHERE deleted_at IS NULL 
                AND menu_id = %s
                ORDER BY name
            """
            categories = execute_menu_query(category_query, (st.session_state.get("selected_menu_id"),)) if st.session_state.get("selected_menu_id") else []
            category_options = ["All"] + [f"{cat['id']} - {cat['name']}" for cat in categories]
            selected_category = st.sidebar.selectbox("Select Category", category_options)
            
            if selected_category != "All":
                selected_category_id = int(selected_category.split(" - ")[0])
                st.session_state["selected_category_id"] = selected_category_id
            else:
                st.session_state["selected_category_id"] = None

            # Item Dropdown
            item_query = """
                SELECT id, name 
                FROM items 
                WHERE deleted_at IS NULL 
                AND category_id = %s
                ORDER BY name
            """
            items = execute_menu_query(item_query, (st.session_state.get("selected_category_id"),)) if st.session_state.get("selected_category_id") else []
            item_options = ["All"] + [f"{item['id']} - {item['name']}" for item in items]
            selected_item = st.sidebar.selectbox("Select Item", item_options)
            
            if selected_item != "All":
                selected_item_id = int(selected_item.split(" - ")[0])
                st.session_state["selected_item_id"] = selected_item_id
            else:
                st.session_state["selected_item_id"] = None

            # Option Dropdown
            option_query = """
                SELECT id, name 
                FROM options 
                WHERE deleted_at IS NULL 
                AND item_id = %s
                ORDER BY name
            """
            options = execute_menu_query(option_query, (st.session_state.get("selected_item_id"),)) if st.session_state.get("selected_item_id") else []
            option_options = ["All"] + [f"{opt['id']} - {opt['name']}" for opt in options]
            selected_option = st.sidebar.selectbox("Select Option", option_options)
            
            if selected_option != "All":
                selected_option_id = int(selected_option.split(" - ")[0])
                st.session_state["selected_option_id"] = selected_option_id
            else:
                st.session_state["selected_option_id"] = None

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
    
    # Add menu operation buttons
    operation = None
    if st.sidebar.button("🔍 View Menu Items"):
        operation = "query"
        st.session_state["operation"] = "query"
        
        try:
            # Build the WHERE clause based on selections
            where_clauses = ["i.deleted_at IS NULL"]
            params = []
            
            if st.session_state.get("selected_location_id"):
                where_clauses.append("l.id = %s")
                params.append(st.session_state["selected_location_id"])
            
            if st.session_state.get("selected_menu_id"):
                where_clauses.append("m.id = %s")
                params.append(st.session_state["selected_menu_id"])
            
            if st.session_state.get("selected_category_id"):
                where_clauses.append("c.id = %s")
                params.append(st.session_state["selected_category_id"])
            
            if st.session_state.get("selected_item_id"):
                where_clauses.append("i.id = %s")
                params.append(st.session_state["selected_item_id"])
            
            if st.session_state.get("selected_option_id"):
                where_clauses.append("o.id = %s")
                params.append(st.session_state["selected_option_id"])
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
                SELECT 
                    l.name as location_name,
                    m.name as menu_name,
                    c.name as category_name,
                    i.id as item_id,
                    i.name as item_name,
                    i.price,
                    i.description,
                    o.name as option_name,
                    CASE WHEN i.disabled THEN 'Disabled' ELSE 'Enabled' END as status
                FROM items i
                JOIN categories c ON i.category_id = c.id
                JOIN menus m ON c.menu_id = m.id
                JOIN locations l ON m.location_id = l.id
                LEFT JOIN options o ON o.item_id = i.id
                WHERE {where_clause}
                ORDER BY l.name, m.name, c.name, i.name, o.name
            """
            
            results = execute_menu_query(query, tuple(params))
            
            if results:
                df = pd.DataFrame(results)
                st.header("Menu Items")
                search = st.text_input("Search items", "")
                if search:
                    df = df[df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No menu items found for the selected filters.")
                
        except Exception as e:
            st.error(f"Error retrieving menu items: {str(e)}")

    # Apply dark theme by default
    st.markdown(dark, unsafe_allow_html=True)

    ########### B. CHAT INTERFACE ###########
    
    ### TITLE ###
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

    # Display previous chat messages from full_chat_history (ignore system prompt message)
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
