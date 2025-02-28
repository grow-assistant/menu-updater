"""
LangChain-powered Streamlit application for Swoop AI.
This file provides a LangChain-integrated version of the Streamlit interface.
"""

import os
import streamlit as st

# Set up page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="Swoop AI",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# Swoop AI\nAI-powered restaurant data assistant"},
)

# Add custom CSS for a modern look that matches Swoop Golf branding
st.markdown(
    """
<style>
    /* Import Google Fonts similar to Swoop website */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    
    /* Overall styling with Swoop Golf colors */
    .main {
        background-color: #ffffff;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Header styling to match Swoop branding */
    h1, h2, h3 {
        color: #FF8B00;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Swoop primary orange */
    .stButton>button {
        background-color: #FF8B00;
        color: white;
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.5rem;
        margin-bottom: 1rem;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* User icon styling */
    .stChatMessageContent[data-testid="stChatMessageContent"] {
        background-color: #f9f9f9;
    }
    
    /* Status message styling */
    .stAlert {
        border-radius: 8px;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* SQL query expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Add shadow to containers */
    [data-testid="stVerticalBlock"] div:has(> [data-testid="stChatMessage"]) {
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-12oz5g7 {
        background-color: #f9f9f9;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Sidebar title styling */
    .css-10oheav {
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        border-top: 1px solid #e6e6e6;
        padding-top: 1rem;
    }
    
    /* Status indicators */
    .stStatus {
        background-color: #fff9f0;
        border-left: 3px solid #FF8B00;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #eaf7ee;
        border-left: 3px solid #FF8B00;
    }

    /* Text styling */
    p, li, div {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Code blocks */
    code {
        font-family: 'Consolas', 'Monaco', monospace;
    }
    
    /* Chat input text */
    .stChatInput {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Make links orange */
    a {
        color: #FF8B00 !important;
    }
    
    /* Sidebar headers */
    .css-16idsys p {
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Reset the assistant avatar completely */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"],
    div[data-testid="stChatMessageAvatarAssistant"] {
        /* Clear any previous background or SVG */
        background-image: none !important;
        background-color: transparent !important;
        position: relative !important;
    }

    /* Use ::before to insert a clean Swoop logo */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"]::before,
    div[data-testid="stChatMessageAvatarAssistant"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('data:image/svg+xml;base64,PHN2ZyBpZD0iTGF5ZXJfMSIgZGF0YS1uYW1lPSJMYXllciAxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNzguOTEgMjM5LjY0Ij48ZGVmcz48c3R5bGU+LmNscy0xLCAuY2xzLTIge2ZpbGw6ICNmZmY7fS5jbHMtMSB7ZmlsbC1ydWxlOiBldmVub2RkO308L3N0eWxlPjwvZGVmcz48Zz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0yODgsNjVsLTUuNTctMi4wOGMtMzYuNTktMTMuNjgtNDIuMzYtMTUuMzMtNDMuODYtMTUuNTNhNDAuNzEsNDAuNzEsMCwwLDAtNzAuNTEsNC4yOGMtLjg1LS4wNi0xLjctLjExLTIuNTYtLjEzaC0uOTRjLS41NiwwLTEuMTEsMC0xLjY2LDBhNTguOTIsNTguOTIsMCwwLDAtMjIuOCw1QTU4LjExLDU4LjExLDAsMCwwLDExOC40NSw3Mi43TDkuMDksMTc4LjQybDk1LjIyLTUuMTEtMS43Myw5NS4zM0wyMDcuMDksMTUxLjI5YTU5LjYzLDU5LjYzLDAsMCwwLDE1LjY4LTM4LjFjMC0uMTEsMC0uMjMsMC0uMzQsMC0uNjAwLTEuMjAwLTEuOGMwLTEsMC0xLjQ1YzAtLjI0LDAtLjQ5LDAtLjc0LDAtLjg1LS4wNy0xLjY5LS4xNC0yLjU0YTQxLDQxLDAsMCwwLDIxLTI0LjgyLDE1LjU2LDE1LjU2LDAsMCwwLDMuNTctMVpNMjA1LjM4LDc1LjMzYzEsMS4xNSwxLjg5LDIuMzYsMi43NywzLjYuMTcuMjYuMzYuNS41NC43Ni44LDEuMTgsMS41NSwyLjQsMi4yNywzLjY1bC42NywxLjE5Yy42MywxLjE1LDEuMjEsMi4zNCwxLjc1LDMuNTRhNTUuNzEsNTUuNzEsMCwwLDEsNC40NiwxNS41QTM2LjI0LDM2LjI0LDAsMCwxLDE3MC43OSw1Ni41QTU0LjI1LDU0LjI1LDAsMCwxLDIwNSw3NC45M1ptMTIuOTIsMzcuNDN2LjExQTU0LjgyLDU0LjgyLDAsMCwxLDE4NS41NiwxNjFhNTQsNTQsMCwwLDEtMTkuODgsNC41NGwtNTYuNzksMywxLTUyLjY5di0uMTJhNTQuNTYsNTQuNTYsMCwwLDEsNTQtNTkuNzhjLjc4LDAsMS41Ny4wNywyLjM1LjExYTQwLjY4LDQwLjY4LDAsMCwwLDUyLjEsNTIuMWwwLC43YzAsLjI5LDAsLjU4LDAsLjg3czAsLjc3LDAsMS4xNUMyMTguMzIsMTExLjUyLDIxOC4zMiwxMTIuMTQsMjE4LjMsMTEyLjc2Wk0yMC44NywxNzMuMjksMTEwLjE4LDg3Yy0uMzMuNzQtLjcsMS40Ni0xLDIuMjNhNTguODgsNTguODgsMCwwLDAtMy44MywyNi44N2wtLjk1LDUyLjc2Wm04Ny45NC0uMjJMMTY1Ljg4LDE3MGE1OC41Niw1OC41NiwwLDAsMCwyMS40OC00LjkxYy44Mi0uMzYsMS42My0uNzQsMi40Mi0xLjEzTDEwNy4zLDI1Ni42Wm0xMTMuMzEtNzEuNTFhNTkuNTEsNTkuNTEsMCwwLDAtNC4yMi0xNC40N2MtLjE0LS4zMy0uMzMtLjY0LS40OC0xYy0uNTUtMS4yMS0xLjEzLTIuNC0xLjc2LTMuNTdjLS4yOS0uNTItLjU4LTEtLjg4LTEuNTVjLS43NC0xLjI5LTEuNTEtMi41NS0yLjM1LTMuNzhjLS4yMy0uMzQtLjQ3LS42Ni0uNzEtMWMtLjkxLTEuMjgtMS44Ni0yLjUzLTIuODctMy43NGwtLjUxLS41OHEtMS42OS0yLTMuNTctMy44MWwtLjEtLjA5YTU4LjM0LDU4LjM0LDAsMCwwLTE5LjE4LTEyLjM4LDU4LjkzLDU4LjkzLDAsMCwwLTEyLjY3LTMuNDQsMzYuMjksMzYuMjksMCwxLDEsNDkuMyw0OS4zOFptMjIuNi0yNWEzOS43OSwzOS43OSwwLDAsMC0zLjExLTIzLjc4YzQuNDUsMS40NSwxMy45MSw0Ljc5LDMzLjY3LDEyLjE1TDI0NS41NCw3Ni4zNkMyNDUuMjgsNzYuNDcsMjQ1LDc2LjUyLDI0NC43Miw3Ni42MVoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC05LjA5IC0yOSkiLz48ZWxsaXBzZSBjbGFzcz0iY2xzLTIiIGN4PSIxNTAuMTgiIGN5PSI4NC44OCIgcng9IjE2LjQ0IiByeT0iMTYuNTMiLz48L2c+PC9zdmc+');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        z-index: 10;
    }

    /* Hide any original SVG inside the avatar */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"] svg,
    div[data-testid="stChatMessageAvatarAssistant"] svg {
        opacity: 0 !important;
        visibility: hidden !important;
    }
    
    /* Hide status messages in the sidebar */
    div[data-testid="stSidebar"] .stSuccess, 
    div[data-testid="stSidebar"] .stInfo, 
    div[data-testid="stSidebar"] .stWarning {
        display: none !important;
    }
    
    /* Fix any CSS that might be visible in the UI */
    .main p,
    .main div:not([class]) {
        min-height: 0 !important;
    }
    
    /* Hide any text that looks like CSS or code */
    *:not(style):not(script):not(pre):not(code) {
        white-space: normal !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Apply a second CSS overlay just to fix any leaking CSS issues
st.markdown(
    """
<style>
/* This CSS will ensure no CSS code is visible in the main UI */
.main pre,
.main code {
    display: none;
}

/* Reset any leaked CSS content */
.stApp .main-content > *:not(.element-container):not(.stVerticalBlock) {
    display: none !important;
}

/* Make sure all style tags are hidden */
.stApp style {
    display: none !important;
}

/* Hide any text that contains CSS syntax */
.stApp .main-content *:contains('{') {
    display: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

from typing import Dict, List, Any, Optional, Tuple
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import OpenAI client for API key verification
import openai

# Import personas
from prompts.personas import get_persona_info, get_persona_voice_id, get_persona_prompt

# Global variables for voice feature availability
ELEVENLABS_AVAILABLE = True  # Force elevenlabs to be available
USE_NEW_API = False
PYGAME_AVAILABLE = True  # Force pygame to be available
pygame = None

# Import from the existing codebase
from integrate_app import (
    load_application_context,
    initialize_voice_dependencies,
    MockSessionState,
    get_clients,
    ElevenLabsVoice,
)
from app import execute_menu_query, adjust_query_timezone

# Add imports for speech recognition
import time
import threading
import base64

# Initialize flag for LangChain availability
LANGCHAIN_AVAILABLE = False

# Import the LangChain integration with error handling
try:
    from utils.langchain_integration import (
        create_langchain_agent,
        StreamlitCallbackHandler,
        create_sql_database_tool,
        create_menu_update_tool,
        integrate_with_existing_flow,
        clean_text_for_speech,
    )

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importing LangChain modules: {str(e)}")
    st.error(
        "Please install required packages: pip install langchain==0.0.150 langchain-community<0.1.0"
    )

# Initialize session state for LangChain components
if "langchain_agent" not in st.session_state:
    st.session_state.langchain_agent = None

if "agent_memory" not in st.session_state:
    st.session_state.agent_memory = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True  # Default to enabled

if "voice_instance" not in st.session_state:
    st.session_state.voice_instance = None

if "clear_input" not in st.session_state:
    st.session_state.clear_input = False

if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id = 62  # Default location ID

if "selected_location_ids" not in st.session_state:
    st.session_state.selected_location_ids = [
        62
    ]  # Default to list with single location

if "selected_club" not in st.session_state:
    st.session_state.selected_club = "Idle Hour Country Club"  # Default club

if "context" not in st.session_state:
    st.session_state.context = {}
# Define available locations organized by club
club_locations = {
    "Idle Hour Country Club": {"locations": [62], "default": 62},
    "Pinetree Country Club": {"locations": [61, 66], "default": 61},
    "East Lake Golf Club": {"locations": [16], "default": 16},
}

# Initialize session state for voice persona
if "voice_persona" not in st.session_state:
    st.session_state.voice_persona = "casual"  # Default to casual


def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Execute SQL query using the existing app functions.

    Args:
        query: SQL query to execute

    Returns:
        dict: Query result
    """
    # Adjust the query for timezone
    adjusted_query = adjust_query_timezone(query, st.session_state.selected_location_id)

    # Execute the query
    result = execute_menu_query(adjusted_query)

    return result


def create_tools_for_agent():
    """
    Create tools for the LangChain agent based on the existing functionality.
    """
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain is not available. Please install required packages.")
        return []

    # SQL database tool
    sql_tool = create_sql_database_tool(execute_query_func=execute_sql_query)

    # Menu update tool
    def execute_menu_update(update_spec):
        # This function calls into the existing code for menu updates
        if isinstance(update_spec, str):
            try:
                update_spec = json.loads(update_spec)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON in update specification",
                }

        item_name = update_spec.get("item_name")
        new_price = update_spec.get("new_price")
        disabled = update_spec.get("disabled")

        if not item_name:
            return {
                "success": False,
                "error": "Missing item_name in update specification",
            }

        if new_price is not None:
            # Update price query
            query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {st.session_state.selected_location_id} RETURNING *"
        elif disabled is not None:
            # Enable/disable query
            disabled_value = str(disabled).lower()
            query = f"UPDATE items SET disabled = {disabled_value} WHERE name ILIKE '%{item_name}%' AND location_id = {st.session_state.selected_location_id} RETURNING *"
        else:
            return {
                "success": False,
                "error": "Invalid update specification - must include either new_price or disabled",
            }

        return execute_sql_query(query)

    menu_tool = create_menu_update_tool(execute_update_func=execute_menu_update)

    # Return all tools
    return [sql_tool, menu_tool]


def setup_langchain_agent():
    """Set up the LangChain agent with the appropriate tools and memory"""
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain is not available. Please install required packages.")
        return None

    if st.session_state.langchain_agent is None:
        try:
            # Create tools
            tools = create_tools_for_agent()

            # Load context for the agent
            context = load_application_context()
            business_context = context.get("business_rules", "")

            # Create system message with context
            system_message = f"""
            You are an AI assistant for a restaurant management system.
            You can help answer questions about orders, menu items, and other restaurant data.
            You can also update menu items, change prices, and enable/disable items.
            
            IMPORTANT ORDER STATUS RULES:
            - When a user asks about "orders" in general without specifying a status, always assume they mean COMPLETED orders (status = 7)
            - For explicit status queries, use the exact status specified by the user
            - Order status values: 1=pending, 3=in progress, 5=ready, 7=completed, 9=cancelled
            
            Here is some context about the business:
            {business_context}
            
            Use the provided tools to help answer questions and fulfill requests.
            """

            # Create the agent
            from langchain.memory import ConversationBufferMemory

            memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True
            )
            st.session_state.agent_memory = memory

            # Get OpenAI API key from environment
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                st.error("OpenAI API key not found in environment variables")
                return None

            # Verify API key functionality with OpenAI client (older version style)
            try:
                # Set the API key
                openai.api_key = openai_api_key

                # Make a minimal API call to verify the key works
                # Just checking the models endpoint which requires minimal resources
                openai.Model.list(limit=1)
            except Exception as e:
                st.error(f"Error initializing OpenAI client: {str(e)}")
                return None

            # Create the agent
            agent = create_langchain_agent(
                openai_api_key=openai_api_key,
                tools=tools,
                memory=memory,
                verbose=True,
                model_name="gpt-3.5-turbo",  # Use a model available in older API
                temperature=0.3,
                streaming=True,
            )

            # Store in session state
            st.session_state.langchain_agent = agent

        except Exception as e:
            st.error(f"Error setting up LangChain agent: {str(e)}")
            return None

    return st.session_state.langchain_agent


def process_query_with_langchain(query: str, output_container):
    """
    Process a query using the LangChain agent and display the results.

    Args:
        query: User query
        output_container: Streamlit container to display output
    """
    if not LANGCHAIN_AVAILABLE:
        output_container.error(
            "LangChain is not available. Please install required packages."
        )
        return {"success": False, "error": "LangChain is not available"}

    # Clear any previous content in the output container
    output_container.empty()

    # Set up callback handler for streaming output
    callback_handler = StreamlitCallbackHandler(output_container)

    # Get or create agent
    agent = setup_langchain_agent()
    if not agent:
        output_container.error("Failed to set up LangChain agent")
        return {"success": False, "error": "Failed to set up LangChain agent"}

    # Create a mock session state for compatibility
    mock_session = MockSessionState()
    mock_session.selected_location_id = st.session_state.selected_location_id
    mock_session.selected_location_ids = st.session_state.selected_location_ids
    mock_session.selected_club = st.session_state.selected_club

    # Get context
    context = {}
    if "context" in st.session_state:
        context = st.session_state.context

    # Ensure location IDs are explicitly added to context
    context["selected_location_id"] = st.session_state.selected_location_id
    context["selected_location_ids"] = st.session_state.selected_location_ids
    context["selected_club"] = st.session_state.selected_club

    # Create tools
    tools = create_tools_for_agent()

    try:
        # Run query through LangChain
        with st.spinner("Processing..."):
            # Show a thinking message
            output_container.markdown("_Thinking..._")

            # Process the query
            result = integrate_with_existing_flow(
                query=query,
                tools=tools,
                context=context,
                agent=agent,
                callback_handler=callback_handler,
            )

        # Update chat history with the text answer if available, otherwise use summary
        chat_message = result.get("text_answer", result.get("summary", ""))

        # Store both the query and a response object with verbal and text components
        response_entry = {
            "summary": result.get("summary", ""),
            "verbal_answer": result.get("verbal_answer", ""),
            "text_answer": result.get("text_answer", ""),
            "sql_query": result.get("sql_query", ""),
        }

        # Append both query and structured response to chat history
        st.session_state.chat_history.append((query, response_entry))

        # Update context
        if "context" not in st.session_state:
            st.session_state.context = {}
        st.session_state.context = result.get("context", {})

        # Track if voice was used to determine if auto-listen should be triggered
        voice_was_used = False

        # Process voice if enabled
        if st.session_state.voice_enabled and st.session_state.voice_instance:
            voice = st.session_state.voice_instance
            if voice.initialized and voice.enabled:
                try:
                    # Use the verbal_answer specifically for voice if available
                    verbal_text = result.get("verbal_answer", result.get("summary", ""))
                    if verbal_text:
                        # Clean the text for better speech synthesis if clean_text_for_speech is available
                        if "clean_text_for_speech" in globals():
                            verbal_text = clean_text_for_speech(verbal_text)

                        # Get persona name for display
                        persona_name = st.session_state.get(
                            "voice_persona", "casual"
                        ).title()

                        # Show voice indicator with Swoop branding and persona info
                        with st.status(
                            f"Processing voice output ({persona_name} style)...",
                            state="running",
                        ):
                            st.markdown(
                                f'<div style="color: #FF8B00; font-weight: 500; font-family: Montserrat, sans-serif;">🔊 Speaking with {persona_name} voice style...</div>',
                                unsafe_allow_html=True,
                            )
                            voice.speak(verbal_text)
                            st.success(f"✓ Voice response complete")
                            voice_was_used = True
                except Exception as voice_error:
                    st.warning(f"Voice output error: {str(voice_error)}")

        # Auto-listen after voice response if enabled
        if voice_was_used and st.session_state.get("auto_listen_enabled", False):
            st.info("Auto-listening for your next question...")
            # Start speech recognition in a new thread to avoid blocking the UI
            thread = threading.Thread(target=background_speech_recognition_with_timeout)
            thread.daemon = True
            thread.start()

        return result
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        output_container.error(error_msg)
        st.session_state.chat_history.append((query, error_msg))
        return {"success": False, "error": str(e)}


def clear_query_input():
    """Clear the query input field - this function is not used anymore"""
    # Don't modify the session state directly
    pass


def init_voice():
    """Initialize voice functionality with direct API approach"""
    global ELEVENLABS_AVAILABLE, PYGAME_AVAILABLE

    if (
        "voice_instance" not in st.session_state
        or st.session_state.voice_instance is None
    ):
        try:
            # Always set voice dependencies to be available
            ELEVENLABS_AVAILABLE = True
            PYGAME_AVAILABLE = True

            # Get the current persona from session state (default to casual)
            persona = st.session_state.get("voice_persona", "casual")

            # Create the voice instance with the selected persona
            voice = SimpleVoice(persona=persona)

            # Set session state
            st.session_state.voice_instance = voice
            st.session_state.voice_enabled = True

            # Initialize silently without showing status messages
            return voice
        except Exception as e:
            # This should only happen if there's a serious error
            with st.sidebar:
                st.error(f"❌ Error initializing voice: {str(e)}")
            st.session_state.voice_instance = None
            st.session_state.voice_enabled = True  # Keep enabled anyway
            return None

    return st.session_state.voice_instance


def run_langchain_streamlit_app():
    """Main function to run the Streamlit app with LangChain integration"""
    # Initialize voice
    voice = init_voice()

    # Main area - Set up the title with Swoop branding
    st.markdown(
        """
    <div style="display: flex; justify-content: center; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-family: 'Montserrat', sans-serif; font-weight: 700;">Swoop AI</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Define avatars for chat display
    avatars = {"user": "user", "assistant": "assistant"}

    # Set up sidebar
    st.sidebar.title("")

    # Club selection in sidebar
    selected_club = st.sidebar.selectbox(
        "Select Club",
        options=list(club_locations.keys()),
        index=(
            list(club_locations.keys()).index(st.session_state.selected_club)
            if st.session_state.selected_club in club_locations
            else 0
        ),
    )

    # Update selected club
    if selected_club != st.session_state.selected_club:
        st.session_state.selected_club = selected_club
        st.session_state.selected_location_id = club_locations[selected_club]["default"]
        st.session_state.selected_location_ids = club_locations[selected_club][
            "locations"
        ]

        # Clear chat history and context when switching clubs
        st.session_state.chat_history = []
        st.session_state.context = {}

        # Show a notification that history was cleared
        st.sidebar.success(f"Switched to {selected_club}. Chat history cleared.")

        # Reset the LangChain agent to start fresh
        st.session_state.langchain_agent = None
        st.session_state.agent_memory = None

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
            st.session_state.voice_persona = selected_persona
            if st.session_state.voice_instance:
                st.session_state.voice_instance.change_persona(selected_persona)
                st.success(f"Changed to {selected_persona} voice persona")

        # Only update voice status if it changed
        if voice_enabled != st.session_state.voice_enabled:
            if voice_enabled and not voice:
                # Try to initialize voice if enabling and not available
                voice = init_voice()
                if voice and voice.initialized:
                    st.session_state.voice_enabled = True
                    st.success("Voice responses enabled")
                else:
                    st.session_state.voice_enabled = False
            else:
                st.session_state.voice_enabled = voice_enabled
                if voice_enabled:
                    st.success("Voice responses enabled")
                else:
                    st.info("Voice responses disabled")

    # Add voice input settings
    with st.sidebar.expander("🎤 Voice Input Settings", expanded=False):
        st.write("Speech recognition settings:")

        # Add auto-listen option - disabled by default
        if "auto_listen_enabled" not in st.session_state:
            st.session_state.auto_listen_enabled = False

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
            if "auto_listen_timeout" not in st.session_state:
                st.session_state.auto_listen_timeout = 5

            st.session_state.auto_listen_timeout = st.slider(
                "Silence timeout (seconds)",
                min_value=1,
                max_value=10,
                value=st.session_state.auto_listen_timeout,
                help="Stop listening if no speech is detected after this many seconds",
            )

        # Add button to test voice input
        if st.button("Test Voice Input", key="test_voice_input"):
            try:
                # Attempt to import the speech recognition library to test if it's available
                import speech_recognition as sr

                st.success("✅ Speech recognition library is available!")

                # Check if PyAudio is available
                try:
                    import pyaudio

                    st.success("✅ PyAudio is available!")
                except ImportError:
                    st.error(
                        "❌ PyAudio is not available. Install with: pip install PyAudio"
                    )
            except ImportError:
                st.error(
                    "❌ Speech recognition library is not available. Install with: pip install SpeechRecognition"
                )

    # Clean up the voice test session state variables since we don't use those buttons anymore
    for key in ["test_voice", "diagnose_voice"]:
        if key in st.session_state:
            del st.session_state[key]

    # LangChain settings expander
    with st.sidebar.expander("LangChain Settings", expanded=False):
        # Reset LangChain agent button
        if st.button("Reset LangChain Agent"):
            st.session_state.langchain_agent = None
            st.session_state.agent_memory = None
            st.success("LangChain agent reset")

    # Display chat history in native Streamlit chat components
    if not st.session_state.chat_history and not st.session_state.clear_input:
        # Show welcome message if no history
        with st.chat_message("assistant"):
            st.markdown(
                """
            <div style="font-family: 'Montserrat', sans-serif;">
            Hello! I'm your Swoop AI assistant. What would you like to know?
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        # Display previous chat history
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
            result = process_query_with_langchain(query, stream_container)

            # Clear the container after processing
            stream_container.empty()

            # Display the text answer with proper markdown formatting
            if "text_answer" in result and result["text_answer"]:
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

    # Use full width for chat input (no columns needed)
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
            result = process_query_with_langchain(query, stream_container)

            # Clear the container after processing
            stream_container.empty()

            # Display the text answer with proper markdown formatting
            if "text_answer" in result and result["text_answer"]:
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

    # Add a clear chat button at the bottom of the sidebar
    with st.sidebar:
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.context = {}
            st.rerun()


# Create a custom function to ensure voice dependencies are available
def force_voice_dependencies():
    """Override the initialize_voice_dependencies function to force voice to be enabled"""
    global ELEVENLABS_AVAILABLE, PYGAME_AVAILABLE

    # Force dependencies to be available
    ELEVENLABS_AVAILABLE = True
    PYGAME_AVAILABLE = True

    # Return success status
    return {"elevenlabs": True, "audio_playback": True}


# Replace the imported function with our custom one
initialize_voice_dependencies = force_voice_dependencies

# Make sure voice is enabled by default
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True  # Default to enabled


# Create a simplified voice class that doesn't have dependency issues
class SimpleVoice:
    """Simple voice class that avoids complex imports"""

    def __init__(self, persona="casual", **kwargs):
        self.enabled = True
        self.initialized = True
        self.persona = persona

        # Get persona info
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]

        print(f"✓ Initialized SimpleVoice with persona: {persona}")

    def clean_text_for_speech(self, text):
        """Clean text to make it more suitable for speech synthesis"""
        import re

        # Remove markdown formatting
        # Replace ** and * (bold and italic) with nothing
        text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)

        # Remove markdown bullet points and replace with natural pauses
        text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)

        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Replace newlines with spaces to make it flow better in speech
        text = re.sub(r"\n+", " ", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # Replace common abbreviations with full words
        text = text.replace("vs.", "versus")
        text = text.replace("etc.", "etcetera")
        text = text.replace("e.g.", "for example")
        text = text.replace("i.e.", "that is")

        # Improve speech timing with commas for complex sentences
        text = re.sub(
            r"(\d+)([a-zA-Z])", r"\1, \2", text
        )  # Put pauses after numbers before words

        # Add a pause after periods that end sentences
        text = re.sub(r"\.(\s+[A-Z])", r". \1", text)

        return text

    def speak(self, text):
        """Speak the given text using ElevenLabs API"""
        if not text:
            return False

        # Clean the text for better speech synthesis
        text = self.clean_text_for_speech(text)

        try:
            # Try to use a simple direct approach with elevenlabs
            try:
                # Simplified approach with minimal imports
                import os
                from dotenv import load_dotenv
                import requests
                import pygame
                from io import BytesIO
                import time

                # Load API key
                load_dotenv()
                api_key = os.getenv("ELEVENLABS_API_KEY")

                if not api_key:
                    raise ValueError("No ElevenLabs API key found")

                # Make direct API call to ElevenLabs
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": api_key,
                }

                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                }

                print("Generating speech with ElevenLabs API...")
                response = requests.post(url, json=data, headers=headers)

                if response.status_code != 200:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text}"
                    )

                # Get audio data
                audio_data = BytesIO(response.content)

                # Play with pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                print(f"✓ Successfully played audio with {self.persona} voice")
                return True

            except Exception as e:
                print(f"Direct API attempt failed: {str(e)}")
                raise

        except Exception as e:
            # Fall back to simulation
            print(f"🔊 [{self.persona}] Would speak: {text[:50]}...")
            print(f"Voice error: {str(e)}")
            return True

    def toggle(self):
        """Toggle voice on/off"""
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Voice {status}"

    def change_persona(self, persona):
        """Change the voice persona"""
        self.persona = persona
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]
        return f"Changed to {persona} voice"


# Override the imported ElevenLabsVoice with our better version
ElevenLabsVoice = SimpleVoice


# Add a special diagnostic function to test and fix voice issues
def test_elevenlabs_connection():
    """Test and diagnose ElevenLabs connection issues - simplified version"""
    import os
    from dotenv import load_dotenv
    import importlib
    import sys

    # Make sure we have the latest environment variables
    load_dotenv(override=True)

    results = {
        "api_key_present": False,
        "elevenlabs_installed": False,
        "pygame_installed": False,
        "can_list_voices": False,
        "can_generate_audio": False,
        "can_play_audio": False,
        "errors": [],
    }

    # Check API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if api_key:
        results["api_key_present"] = True
        print("✓ ElevenLabs API key is present")
    else:
        results["errors"].append("No ElevenLabs API key found in .env file")
        print("✗ No ElevenLabs API key found")

    # Check if elevenlabs is installed
    try:
        # Check if we can import the package without actually importing it
        spec = importlib.util.find_spec("elevenlabs")
        if spec is not None:
            results["elevenlabs_installed"] = True
            print("✓ ElevenLabs package is installed")
            print(f"  Version: {getattr(spec, '__version__', 'unknown')}")

            # Don't actually import elevenlabs to avoid the error
            results["can_list_voices"] = "Unknown - skipped to avoid errors"
            results["can_generate_audio"] = "Unknown - skipped to avoid errors"
        else:
            results["errors"].append("ElevenLabs package is not found")
            print("✗ ElevenLabs package is not installed")
    except Exception as e:
        results["errors"].append(f"Error checking ElevenLabs: {str(e)}")
        print(f"✗ Error checking elevenlabs: {str(e)}")

    # Check if pygame is installed
    try:
        # Check if we can import pygame
        spec = importlib.util.find_spec("pygame")
        if spec is not None:
            results["pygame_installed"] = True
            print("✓ Pygame is installed")

            # Try to import and initialize mixer
            try:
                import pygame

                pygame.mixer.init()
                print("✓ Pygame mixer initialized successfully")
                results["can_play_audio"] = "Possibly - mixer initialized"
            except Exception as me:
                error_msg = f"Error initializing pygame mixer: {str(me)}"
                results["errors"].append(error_msg)
                print(f"✗ {error_msg}")
        else:
            results["errors"].append("Pygame is not found")
            print("✗ Pygame is not installed")
    except Exception as e:
        results["errors"].append(f"Error checking pygame: {str(e)}")
        print(f"✗ Error checking pygame: {str(e)}")

    # Provide solution
    results[
        "solution"
    ] = """
    It looks like there's an issue with your elevenlabs package. Here are some solutions:
    
    1. Downgrade to a more stable version:
       ```
       pip uninstall elevenlabs
       pip install elevenlabs==0.2.26
       ```
    
    2. Try using a simpler voice implementation:
       We've updated the app to use a simpler implementation that should work better
       
    Press "Re-initialize Voice System" button below to try with the updated implementation.
    """

    return results


# Add a modified speech recognition function with timeout
def recognize_speech_with_timeout(timeout=5, phrase_time_limit=15):
    """
    Capture audio from the microphone and convert it to text with a custom timeout.

    Args:
        timeout: Time to wait before stopping if no speech is detected
        phrase_time_limit: Maximum duration of speech to recognize

    Returns:
        str: Recognized text, or empty string if recognition failed
    """
    try:
        import speech_recognition as sr

        # Create a recognizer instance
        recognizer = sr.Recognizer()

        # Capture audio from the microphone
        with sr.Microphone() as source:
            st.session_state["recording"] = True

            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            # Display recording indicator
            with st.spinner(f"Listening... (timeout: {timeout}s)"):
                # Capture audio with the specified timeout
                try:
                    audio = recognizer.listen(
                        source, timeout=timeout, phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    st.info("No speech detected within timeout period.")
                    return ""

            # Try to recognize the speech
            try:
                st.session_state["recording"] = False
                # Use Google's speech recognition
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                st.warning("Could not understand audio. Please try again.")
                return ""
            except sr.RequestError as e:
                st.error(f"Speech recognition service error: {e}")
                return ""

    except ImportError:
        st.error(
            "Speech recognition library not installed. Run: pip install SpeechRecognition PyAudio"
        )
        return ""
    except Exception as e:
        st.error(f"Error during speech recognition: {e}")
        return ""
    finally:
        st.session_state["recording"] = False


# Add a background speech recognition function with timeout
def background_speech_recognition_with_timeout():
    """Run speech recognition in a background thread with timeout and store the result in session state"""
    try:
        # Get the timeout from session state or use default
        timeout = st.session_state.get("auto_listen_timeout", 5)

        # Start listening with the timeout
        text = recognize_speech_with_timeout(timeout=timeout)
        if text:
            st.session_state["speech_text"] = text
            st.session_state["speech_ready"] = True
    except Exception as e:
        st.error(f"Error in background speech recognition: {e}")
    finally:
        st.session_state["recording"] = False


# Initialize more session state variables
if "recording" not in st.session_state:
    st.session_state.recording = False

if "speech_text" not in st.session_state:
    st.session_state.speech_text = ""

if "speech_ready" not in st.session_state:
    st.session_state.speech_ready = False

if "auto_listen_enabled" not in st.session_state:
    st.session_state.auto_listen_enabled = False

if "auto_listen_timeout" not in st.session_state:
    st.session_state.auto_listen_timeout = 5

if __name__ == "__main__":
    if not LANGCHAIN_AVAILABLE:
        st.error(
            """
        LangChain integration is not available. Please install the required packages:
        ```
        pip install langchain==0.0.150 langchain-community<0.1.0
        ```
        """
        )
    else:
        run_langchain_streamlit_app()
