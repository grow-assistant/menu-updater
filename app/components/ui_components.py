"""
UI components for the Streamlit app.
Contains functions to create various UI components.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logger
logger = logging.getLogger("ai_menu_updater")

def render_welcome_message(st):
    """
    Render a welcome message in the chat interface.
    
    Args:
        st: Streamlit module
    """
    with st.chat_message("assistant"):
        st.markdown(
            """
            <div style="font-family: 'Montserrat', sans-serif;">
            Hello! I'm your Swoop AI assistant. What would you like to know?
            </div>
            """,
            unsafe_allow_html=True,
        )

def render_sidebar(st, app_state):
    """
    Render the sidebar UI components.
    
    Args:
        st: Streamlit module
        app_state: AppState class
    """
    st.sidebar.title("")
    
    # Club selection in sidebar
    selected_club = st.sidebar.selectbox(
        "Select Club",
        options=list(app_state.get_club_locations().keys()),
        index=(
            list(app_state.get_club_locations().keys()).index(st.session_state.selected_club)
            if st.session_state.selected_club in app_state.get_club_locations()
            else 0
        ),
    )

    # Process the club selection
    app_state.process_club_selection(st, selected_club)

    # Voice settings expander
    with st.sidebar.expander("🔊 Voice Settings", expanded=False):
        voice_enabled = st.checkbox(
            "Enable voice responses",
            value=st.session_state.voice_enabled,
            help="Turn on/off voice responses using ElevenLabs",
        )

        # Add persona selector
        available_personas = [
            "casual",
            "professional",
            "enthusiastic", 
            "pro_caddy",
            "clubhouse_legend",
        ]
        selected_persona = st.selectbox(
            "Voice Persona",
            options=available_personas,
            index=(
                available_personas.index(st.session_state.voice_persona)
                if st.session_state.voice_persona in available_personas
                else 0
            ),
            help="Select voice persona style for responses",
        )

        # Update persona if changed
        if selected_persona != st.session_state.voice_persona:
            app_state.set_voice_persona(st, selected_persona)
            st.success(f"Changed to {selected_persona} voice persona")

        # Only update voice status if it changed
        if voice_enabled != st.session_state.voice_enabled:
            app_state.set_voice_enabled(st, voice_enabled)
            if voice_enabled:
                st.success("Voice responses enabled")
            else:
                st.info("Voice responses disabled")

    # Add voice input settings
    with st.sidebar.expander("🎤 Voice Input Settings", expanded=False):
        st.write("Speech recognition settings:")

        # Add auto-listen option
        auto_listen = st.checkbox(
            "Auto-listen after AI responds",
            value=st.session_state.auto_listen_enabled,
            help="Automatically listen for your next question after the AI finishes speaking",
        )

        # Update auto-listen status if changed
        if auto_listen != st.session_state.auto_listen_enabled:
            st.session_state.auto_listen_enabled = auto_listen
            if auto_listen:
                st.success("Auto-listen enabled")
            else:
                st.info("Auto-listen disabled")

        # Set timeout settings for auto-listen
        if st.session_state.auto_listen_enabled:
            st.session_state.auto_listen_timeout = st.slider(
                "Silence timeout (seconds)",
                min_value=1,
                max_value=10,
                value=st.session_state.auto_listen_timeout,
                help="Stop listening if no speech is detected after this many seconds",
            )

    # LangChain settings expander
    with st.sidebar.expander("⚙️ LangChain Settings", expanded=False):
        # Reset LangChain agent button
        if st.button("Reset LangChain Agent"):
            st.session_state.langchain_agent = None
            st.session_state.agent_memory = None
            st.success("LangChain agent reset")
            
    # Add clear chat button at the bottom of the sidebar
    with st.sidebar:
        if st.button("Clear Chat History", use_container_width=True):
            app_state.clear_chat_history(st)
            st.rerun()
            
def render_chat_history(st):
    """
    Render the chat history.
    
    Args:
        st: Streamlit module
    """
    for user_query, ai_response in st.session_state.chat_history:
        # User message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Assistant message
        with st.chat_message("assistant"):
            if isinstance(ai_response, dict):
                # Display the text answer with improved formatting
                if "text_answer" in ai_response and ai_response["text_answer"]:
                    st.markdown(ai_response["text_answer"])
                elif "summary" in ai_response and ai_response["summary"]:
                    st.markdown(ai_response["summary"])
                else:
                    st.markdown("No response available")

                # Show SQL query in an expander if available, with better styling
                if "sql_query" in ai_response and ai_response["sql_query"]:
                    with st.expander("🔍 View SQL Query", expanded=False):
                        st.code(ai_response["sql_query"], language="sql")
            else:
                # Handle legacy string responses
                st.markdown(ai_response)

def render_database_status(st, db_status):
    """
    Render the database connection status.
    
    Args:
        st: Streamlit module
        db_status: Database connection status dictionary
    """
    if db_status.get("connected", False):
        st.success("✅ Connected to database")
    else:
        st.warning(f"⚠️ {db_status.get('message', 'Database connection failed.')} Running in demo mode with mock data.")

def render_chat_interface(st, app_state, db_status, process_query_func):
    """
    Render the main chat interface.
    
    Args:
        st: Streamlit module
        app_state: AppState class
        db_status: Database connection status
        process_query_func: Function to process queries
    """
    # Set up the title with Swoop branding
    st.markdown(
        """
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <h1 style="color: white; margin: 0; font-family: 'Montserrat', sans-serif; font-weight: 700;">Swoop AI</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Show database status in a small placeholder
    db_status_placeholder = st.empty()
    with db_status_placeholder:
        render_database_status(st, db_status)
    
    # Display avatars for chat
    avatars = {"user": "user", "assistant": "assistant"}
    
    # Display chat history or welcome message
    if not st.session_state.chat_history and not st.session_state.clear_input:
        render_welcome_message(st)
    else:
        render_chat_history(st)
    
    # Create an output container for streaming responses
    output_container = st.empty()
    
    # Check if there's text from speech recognition ready to be processed
    if st.session_state.get("speech_ready", False):
        query = st.session_state.speech_text
        st.session_state.speech_ready = False
        st.session_state.speech_text = ""
        
        # Display user query in a chat message
        with st.chat_message("user"):
            st.write(query)
            
        # Process query with the assistant
        with st.chat_message("assistant"):
            # Create a container for the streaming output
            stream_container = st.empty()
            
            # Process the query
            result = process_query_func(query, stream_container)
            
            # Clear the container after processing
            stream_container.empty()
            
            # Only display the text answer after voice has started
            if "text_answer" in result and result["text_answer"]:
                # Display text even if voice is active
                st.markdown(result["text_answer"])
            else:
                st.markdown(result.get("summary", "No result available"))
                
            # Show SQL query in an expander if available
            if "sql_query" in result and result["sql_query"]:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(result["sql_query"], language="sql")
                    
        # Clear input after processing
        if "clear_input" not in st.session_state:
            st.session_state.clear_input = True
            st.rerun()
    
    # Use chat_input for text queries
    query = st.chat_input(
        "Ask about orders, menu items, revenue, or other restaurant data..."
    )
    
    # Process regular text input
    if query:
        # Display user query in a chat message
        with st.chat_message("user"):
            st.write(query)
            
        # Process query with the assistant
        with st.chat_message("assistant"):
            # Create a container for the streaming output
            stream_container = st.empty()
            
            # Process the query
            result = process_query_func(query, stream_container)
            
            # Clear the container after processing
            stream_container.empty()
            
            # Only display the text answer after voice has started
            if "text_answer" in result and result["text_answer"]:
                # Display text even if voice is active
                st.markdown(result["text_answer"])
            else:
                st.markdown(result.get("summary", "No result available"))
                
            # Show SQL query in an expander if available
            if "sql_query" in result and result["sql_query"]:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(result["sql_query"], language="sql")
                    
        # Clear input after processing
        if "clear_input" not in st.session_state:
            st.session_state.clear_input = True
            st.rerun()
            
    # Clear the flag after rerun
    if "clear_input" in st.session_state and st.session_state.clear_input:
        st.session_state.clear_input = False 