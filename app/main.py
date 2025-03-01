"""
LangChain-powered Streamlit application for Swoop AI.
This file provides a LangChain-integrated version of the Streamlit interface.
"""

import os
import logging
import streamlit as st
import threading
import traceback
from dotenv import load_dotenv

# Configure Streamlit page
st.set_page_config(
    page_title="Swoop AI",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# Swoop AI\nAI-powered restaurant data assistant"},
)

# Load environment variables
load_dotenv()

# Import app modules
try:
    # Import our app modules
    from app import logger
    from app.utils.app_state import AppState
    from app.utils.styling import apply_styling
    from app.utils.database import check_database_connection
    from app.services.voice_service import initialize_voice_service, background_speech_recognition
    from app.components.ui_components import render_chat_interface, render_sidebar
    
    # Try to import langchain services
    try:
        from app.services.langchain_service import (
            create_tools_for_agent, 
            create_langchain_agent, 
            process_query_with_langchain,
            StreamlitCallbackHandler,
            LANGCHAIN_AVAILABLE
        )
    except ImportError:
        logger.error("Error importing LangChain services, some features will be unavailable")
        LANGCHAIN_AVAILABLE = False
        
except Exception as e:
    st.error(f"Error importing app modules: {str(e)}")
    st.error(traceback.format_exc())
    LANGCHAIN_AVAILABLE = False
    

def check_db_in_background():
    """Check database connection in a background thread"""
    try:
        # Use a very short timeout for initial connection
        db_status = check_database_connection()
        return db_status
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return {"connected": False, "message": f"Error: {str(e)}"}


def init_voice():
    """Initialize voice functionality"""
    if "voice_instance" not in st.session_state or st.session_state.voice_instance is None:
        try:
            # Get the current persona from session state
            persona = st.session_state.get("voice_persona", "casual")

            # Create the voice instance with the selected persona
            voice = initialize_voice_service(persona=persona)

            # Set session state
            st.session_state.voice_instance = voice
            
            return voice
        except Exception as e:
            # This should only happen if there's a serious error
            with st.sidebar:
                st.error(f"❌ Error initializing voice: {str(e)}")
            st.session_state.voice_instance = None
            return None

    return st.session_state.voice_instance


def process_query(query, output_container):
    """
    Process a query using LangChain and return the results.
    
    Args:
        query: User query
        output_container: Streamlit container for output
        
    Returns:
        dict: Results from processing the query
    """
    if not LANGCHAIN_AVAILABLE:
        output_container.error(
            "LangChain is not available. Please install required packages."
        )
        return {
            "success": False, 
            "error": "LangChain is not available",
            "text_answer": "I'm sorry, but the LangChain integration is not available right now. Please check the installation."
        }

    # Clear any previous content in the output container
    output_container.empty()

    # Set up callback handler for streaming output
    callback_handler = StreamlitCallbackHandler(output_container)

    # Get or create agent
    agent = st.session_state.langchain_agent
    
    # Create tools for the agent
    tools = create_tools_for_agent(location_id=st.session_state.selected_location_id)
    
    if not agent:
        try:
            # Create a new agent
            agent = create_langchain_agent(
                tools=tools,
                memory=st.session_state.agent_memory,
                verbose=True,
                callback_handler=callback_handler
            )
            
            # Store in session state
            st.session_state.langchain_agent = agent
        except Exception as e:
            logger.error(f"Error creating LangChain agent: {str(e)}")
            output_container.error(f"Error creating LangChain agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text_answer": f"Error creating LangChain agent: {str(e)}"
            }

    # Get context from session state
    context = st.session_state.context

    # Ensure location IDs are explicitly added to context
    context["selected_location_id"] = st.session_state.selected_location_id
    context["selected_location_ids"] = st.session_state.selected_location_ids
    context["selected_club"] = st.session_state.selected_club

    try:
        # Process the query
        with st.spinner("Processing..."):
            # Process query with LangChain
            result = process_query_with_langchain(
                query=query,
                tools=tools,
                context=context,
                agent=agent,
                callback_handler=callback_handler,
            )

        # Update chat history
        AppState.add_to_chat_history(st, query, result)

        # Update context in session state
        if "context" in result:
            st.session_state.context = result["context"]

        # Process voice if enabled
        voice_active = False
        if st.session_state.voice_enabled and st.session_state.voice_instance:
            voice = st.session_state.voice_instance
            if voice.enabled:
                try:
                    # Use the verbal_answer specifically for voice if available
                    verbal_text = result.get("verbal_answer", result.get("summary", ""))
                    if verbal_text:
                        # Speak the text
                        voice.speak(verbal_text)
                        voice_active = True
                except Exception as voice_error:
                    # Log error but don't display in UI
                    logger.error(f"Voice output error: {str(voice_error)}")

        # Auto-listen after voice response if enabled
        if voice_active and st.session_state.get("auto_listen_enabled", False):
            # Start speech recognition in a new thread
            thread = background_speech_recognition(
                callback=lambda text: handle_speech_result(text),
                timeout=st.session_state.auto_listen_timeout
            )

        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        output_container.error(f"Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "text_answer": f"I encountered an error while processing your query: {str(e)}"
        }


def handle_speech_result(text):
    """
    Handle the result from speech recognition.
    
    Args:
        text: Recognized text
    """
    if text:
        # Store the speech text in session state
        st.session_state.speech_text = text
        st.session_state.speech_ready = True
        # Rerun the app to process the text
        st.rerun()


def run_app():
    """Main function to run the Streamlit app"""
    # Apply custom styling
    apply_styling(st)
    
    # Initialize session state
    AppState.initialize_session_state(st)
    
    # Initialize voice
    voice = init_voice()
    
    # Check database connection
    db_status = check_db_in_background()
    
    # Render sidebar
    render_sidebar(st, AppState)
    
    # Render main chat interface
    render_chat_interface(st, AppState, db_status, process_query)


if __name__ == "__main__":
    try:
        # Run the app
        run_app()
    except Exception as e:
        # Log any startup errors
        logger.error(f"Error during application startup: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error during application startup: {str(e)}")
        st.error(traceback.format_exc()) 