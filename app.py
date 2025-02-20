import streamlit as st
from utils.config import db_credentials, MAX_TOKENS_ALLOWED, MAX_MESSAGES_TO_OPENAI, TOKEN_BUFFER
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import run_chat_sequence, clear_chat_history, count_tokens, prepare_sidebar_data
from utils.database_functions import database_schema_dict
from utils.function_calling_spec import functions
from utils.helper_functions import save_conversation
from utils.search import render_search_filters, search_menu_items, render_search_results
from utils.operation_patterns import match_operation
from utils.ui_components import (
    render_price_input,
    render_time_input,
    render_option_limits,
    validate_menu_update
)
from assets.dark_theme import dark
from assets.light_theme import light
from assets.made_by_sdw import made_by_sdw





if __name__ == "__main__":

    ########### A. SIDEBAR ###########

    # Prepare data for the sidebar dropdowns
    sidebar_data = prepare_sidebar_data(database_schema_dict)
    st.sidebar.markdown("<div class='made_by'>Made by SDW🔋</div>", unsafe_allow_html=True)

    ### MENU OPERATIONS ###
    st.sidebar.title("🍽️ Menu Operations")
    
    # Location selector
    location_id = st.sidebar.number_input("Location ID", min_value=1, step=1)
    
    # Create tabs
    tabs = st.tabs(["📊 Dashboard", "🔧 Operations", "🔍 Search"])
    
    # Set active tab from session state
    if st.session_state.active_tab != 0:
        st.session_state.active_tab = 0  # Reset after switching
    
    # Initialize session state
    if "operation_type" not in st.session_state:
        st.session_state.operation_type = "Price Updates"
    if "last_operation" not in st.session_state:
        st.session_state.last_operation = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0
    
    # Dashboard tab
    with tabs[0]:
        if st.session_state.get("show_dashboard", True):
            from utils.visualization import render_analytics_dashboard
            render_analytics_dashboard(st.session_state.get("postgres_connection"), location_id)
    
    # Operations tab
    with tabs[1]:
        st.subheader("Menu Operations")
        
        # Operation type selection
        operation_type = st.radio(
            "Operation Type",
            ["Price Updates", "Time Ranges", "Enable/Disable", "Copy Options"],
            horizontal=True,
            key="operation_type"
        )
        
        # Price update section
        if operation_type == "Price Updates":
            update_type = st.radio(
                "Update Type",
                ["Single Item", "Bulk Update"],
                key="price_update_type"
            )
            
            # Auto-fill from matched operation
            if operation := st.session_state.get('last_operation'):
                if (
                    isinstance(operation, dict) 
                    and operation.get('operation') == st.session_state.operation_type
                    and operation.get('type') == 'price_update'
                    and isinstance(operation.get('params'), dict)
                    and (item_name := operation['params'].get('item_name'))
                ):
                    st.info(f"Auto-filling price update for: {item_name}")
                    # Query item ID from name
                    with st.session_state["postgres_connection"].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM items WHERE name ILIKE %s AND disabled = false",
                            (item_name,)
                        )
                        if result := cursor.fetchone():
                            item_id = result[0]
                            if new_price := operation['params'].get('price'):
                                st.session_state[f"price_{item_id}"] = new_price
            
            if update_type == "Single Item":
                item_id = st.number_input("Item ID", min_value=1, step=1)
                new_price = render_price_input("New Price", f"price_{item_id}")
                
                # Validate price input
                validation_data = {'price': new_price}
                if errors := validate_menu_update(validation_data):
                    st.error("\n".join(errors))
            else:
                from utils.bulk_operations import render_bulk_editor, apply_bulk_updates
                with st.spinner("Loading items..."):
                    cursor = st.session_state["postgres_connection"].cursor()
                    cursor.execute("""
                        SELECT i.*, c.name as category_name
                        FROM items i
                        JOIN categories c ON i.category_id = c.id
                        WHERE i.disabled = false
                        ORDER BY c.name, i.name
                    """)
                    items = [dict(zip([col[0] for col in cursor.description], row))
                            for row in cursor.fetchall()]
                    cursor.close()
                
                updates = render_bulk_editor(items, 'price')
                if updates and st.button("Apply Updates"):
                    result = apply_bulk_updates(
                        st.session_state["postgres_connection"],
                        updates,
                        'price'
                    )
                    if "Error" in result:
                        st.error(result)
                    else:
                        st.success(result)
        
        # Time range section
        elif operation_type == "Time Ranges":
            # Auto-fill from matched operation
            if operation := st.session_state.get('last_operation'):
                if (
                    isinstance(operation, dict)
                    and operation.get('operation') == st.session_state.operation_type
                    and operation.get('type') == 'time_range'
                    and isinstance(operation.get('params'), dict)
                    and (category_name := operation['params'].get('category_name'))
                ):
                    st.info(f"Auto-filling time range for: {category_name}")
                    # Query category ID from name
                    with st.session_state["postgres_connection"].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM categories WHERE name ILIKE %s AND disabled = false",
                            (category_name,)
                        )
                        if result := cursor.fetchone():
                            category_id = result[0]
                            if start_time := operation['params'].get('start_time'):
                                st.session_state[f"start_{category_id}"] = start_time
                            if end_time := operation['params'].get('end_time'):
                                st.session_state[f"end_{category_id}"] = end_time
            
            category_id = st.number_input("Category ID", min_value=1, step=1)
            start_time = render_time_input("Start Time", f"start_{category_id}")
            end_time = render_time_input("End Time", f"end_{category_id}")
            
            # Validate time inputs
            validation_data = {'start_time': start_time, 'end_time': end_time}
            if errors := validate_menu_update(validation_data):
                st.error("\n".join(errors))
        
        # Enable/disable section
        elif operation_type == "Enable/Disable":
            # Auto-fill from matched operation
            if operation := st.session_state.get('last_operation'):
                if (
                    isinstance(operation, dict)
                    and operation.get('operation') == st.session_state.operation_type
                    and operation.get('type') == 'enable_disable'
                    and isinstance(operation.get('params'), dict)
                    and (item_name := operation['params'].get('item_name'))
                    and (action := operation['params'].get('action'))
                ):
                    st.info(f"Auto-filling {action} for: {item_name}")
                    # Query item ID from name
                    with st.session_state["postgres_connection"].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM items WHERE name ILIKE %s",
                            (item_name,)
                        )
                        if result := cursor.fetchone():
                            item_id = result[0]
                            enable = action in ('enable', 'activate', 'on')
                            st.session_state[f"toggle_{item_id}"] = enable
            
            item_id = st.number_input("Item ID", min_value=1, step=1)
            current_state = st.checkbox("Enabled", key=f"toggle_{item_id}")
            
            if st.button("Save Status"):
                with st.session_state["postgres_connection"].cursor() as cursor:
                    cursor.execute(
                        "UPDATE items SET disabled = %s WHERE id = %s",
                        (not current_state, item_id)
                    )
                    st.session_state["postgres_connection"].commit()
                    st.success(f"Item {item_id} {'enabled' if current_state else 'disabled'}")
        
        # Option copying section
        elif operation_type == "Copy Options":
            # Auto-fill from matched operation
            if operation := st.session_state.get('last_operation'):
                if (
                    isinstance(operation, dict)
                    and operation.get('operation') == st.session_state.operation_type
                    and operation.get('type') == 'copy_options'
                    and isinstance(operation.get('params'), dict)
                    and (source_item := operation['params'].get('source_item'))
                    and (target_item := operation['params'].get('target_item'))
                ):
                    st.info(f"Auto-filling option copy from {source_item} to {target_item}")
                    # Store source and target for option_operations.py
                    st.session_state['source_item_name'] = source_item
                    st.session_state['target_item_name'] = target_item
            
            from utils.option_operations import render_option_copy_interface
            render_option_copy_interface(st.session_state["postgres_connection"])
        
    # Search tab
    with tabs[2]:
        st.subheader("Search Menu Items")
        
        # Get available categories for filter
        with st.session_state["postgres_connection"].cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT c.name 
                FROM categories c 
                JOIN menus m ON c.menu_id = m.id 
                WHERE m.location_id = %s
                ORDER BY c.name
            """, (location_id,))
            categories = [row[0] for row in cursor.fetchall()]
        
        # Render filters and search
        filters = render_search_filters()
        filters['category'] = st.sidebar.multiselect(
            "Categories",
            options=categories,
            help="Filter by category"
        )
        
        # Execute search
        with st.spinner("Searching..."):
            results = search_menu_items(st.session_state["postgres_connection"], filters)
            render_search_results(results)
    
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
    
    # Price update section
    if st.sidebar.button("💰 Update Prices"):
        operation = "update"
        st.session_state["operation"] = "update"
        # Show price input options
        if "operation" in st.session_state and st.session_state["operation"] == "update":
            st.sidebar.subheader("Update Price")
            update_type = st.sidebar.radio(
                "Update Type",
                ["Single Item", "Bulk Update"],
                key="price_update_type"
            )
            
            if update_type == "Single Item":
                item_id = st.sidebar.number_input("Item ID", min_value=1, step=1)
                new_price = render_price_input("New Price", f"price_{item_id}")
                
                # Validate price input
                validation_data = {'price': new_price}
                if errors := validate_menu_update(validation_data):
                    st.sidebar.error("\n".join(errors))
            else:
                from utils.bulk_operations import render_bulk_editor, apply_bulk_updates
                with st.spinner("Loading items..."):
                    cursor = st.session_state["postgres_connection"].cursor()
                    cursor.execute("""
                        SELECT i.*, c.name as category_name
                        FROM items i
                        JOIN categories c ON i.category_id = c.id
                        WHERE i.disabled = false
                        ORDER BY c.name, i.name
                    """)
                    items = [dict(zip([col[0] for col in cursor.description], row))
                            for row in cursor.fetchall()]
                    cursor.close()
                
                updates = render_bulk_editor(items, 'price')
                if updates and st.button("Apply Updates"):
                    result = apply_bulk_updates(
                        st.session_state["postgres_connection"],
                        updates,
                        'price'
                    )
                    if "Error" in result:
                        st.error(result)
                    else:
                        st.success(result)
    
    # Time range section
    if st.sidebar.button("⏰ Update Time Range"):
        operation = "time"
        st.session_state["operation"] = "time"
        # Show time inputs when time range update is selected
        if "operation" in st.session_state and st.session_state["operation"] == "time":
            st.sidebar.subheader("Update Time Range")
            category_id = st.sidebar.number_input("Category ID", min_value=1, step=1)
            start_time = render_time_input("Start Time", f"start_{category_id}")
            end_time = render_time_input("End Time", f"end_{category_id}")
            
            # Validate time inputs
            validation_data = {'start_time': start_time, 'end_time': end_time}
            if errors := validate_menu_update(validation_data):
                st.sidebar.error("\n".join(errors))
    
    # Option limits section
    if st.sidebar.button("🔢 Update Option Limits"):
        operation = "limits"
        st.session_state["operation"] = "limits"
        # Show option limit inputs when selected
        if "operation" in st.session_state and st.session_state["operation"] == "limits":
            st.sidebar.subheader("Update Option Limits")
            option_id = st.sidebar.number_input("Option ID", min_value=1, step=1)
            min_val, max_val = render_option_limits(
                "Minimum Selections",
                "Maximum Selections",
                f"option_{option_id}"
            )
            
            # Validate option limits
            validation_data = {'min_selections': min_val, 'max_selections': max_val}
            if errors := validate_menu_update(validation_data):
                st.sidebar.error("\n".join(errors))
    
    # Enable/disable section
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
        st.rerun()



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
        # Try to match operation first
        if operation := match_operation(prompt):
            st.session_state.operation_type = operation['operation']
            st.session_state.last_operation = operation
            st.session_state.active_tab = 1  # Switch to operations tab
            st.rerun()
            
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
