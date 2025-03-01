"""
Application state management for the Streamlit app.
Provides utilities for managing session state and app state.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class AppState:
    """Class to manage the application state in Streamlit."""
    
    @staticmethod
    def initialize_session_state(st):
        """
        Initialize all required session state variables.
        
        Args:
            st: Streamlit module
        """
        # For LangChain components
        if "langchain_agent" not in st.session_state:
            st.session_state.langchain_agent = None

        if "agent_memory" not in st.session_state:
            st.session_state.agent_memory = None

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # For voice components
        if "voice_enabled" not in st.session_state:
            st.session_state.voice_enabled = True  # Default to enabled

        if "voice_instance" not in st.session_state:
            st.session_state.voice_instance = None

        if "voice_persona" not in st.session_state:
            st.session_state.voice_persona = "casual"  # Default persona

        # For UI control
        if "clear_input" not in st.session_state:
            st.session_state.clear_input = False

        # For location settings
        if "selected_location_id" not in st.session_state:
            st.session_state.selected_location_id = 62  # Default location ID

        if "selected_location_ids" not in st.session_state:
            st.session_state.selected_location_ids = [62]  # Default location ID list

        if "selected_club" not in st.session_state:
            st.session_state.selected_club = "Idle Hour Country Club"  # Default club

        # For context and query processing
        if "context" not in st.session_state:
            st.session_state.context = {}

        # For speech recognition
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

        logger.info("Session state initialized")

    @staticmethod
    def get_club_locations():
        """
        Get the available club locations.
        
        Returns:
            dict: Dictionary of club locations
        """
        return {
            "Idle Hour Country Club": {"locations": [62], "default": 62},
            "Pinetree Country Club": {"locations": [61, 66], "default": 61},
            "East Lake Golf Club": {"locations": [16], "default": 16},
        }
    
    @staticmethod
    def get_club_name(location_id: int) -> str:
        """
        Get the club name for a location ID.
        
        Args:
            location_id: Location ID to get club name for
            
        Returns:
            str: Club name
        """
        location_names = {
            62: "Idle Hour Country Club",
            61: "Pinetree Country Club (Location 61)",
            66: "Pinetree Country Club (Location 66)",
            16: "East Lake Golf Club",
        }
        return location_names.get(location_id, f"Unknown Location ({location_id})")
    
    @staticmethod
    def process_club_selection(st, selected_club: str) -> None:
        """
        Process the selection of a club in the UI.
        
        Args:
            st: Streamlit module
            selected_club: Name of the selected club
        """
        club_locations = AppState.get_club_locations()
        
        # Update selected club
        if selected_club != st.session_state.selected_club:
            st.session_state.selected_club = selected_club
            st.session_state.selected_location_id = club_locations[selected_club]["default"]
            st.session_state.selected_location_ids = club_locations[selected_club]["locations"]

            # Clear chat history and context when switching clubs
            st.session_state.chat_history = []
            st.session_state.context = {}

            # Show a notification that history was cleared
            st.sidebar.success(f"Switched to {selected_club}. Chat history cleared.")

            # Reset the LangChain agent to start fresh
            st.session_state.langchain_agent = None
            st.session_state.agent_memory = None
    
    @staticmethod
    def add_to_chat_history(st, query: str, response: Any) -> None:
        """
        Add an exchange to the chat history.
        
        Args:
            st: Streamlit module
            query: User query
            response: Assistant response
        """
        st.session_state.chat_history.append((query, response))
    
    @staticmethod
    def clear_chat_history(st) -> None:
        """
        Clear the chat history.
        
        Args:
            st: Streamlit module
        """
        st.session_state.chat_history = []
        st.session_state.context = {}
        logger.info("Chat history cleared")
        
    @staticmethod
    def update_context(st, new_context: Dict[str, Any]) -> None:
        """
        Update the context with new values.
        
        Args:
            st: Streamlit module
            new_context: New context values
        """
        if "context" not in st.session_state:
            st.session_state.context = {}
            
        st.session_state.context.update(new_context)
        
    @staticmethod
    def set_voice_enabled(st, enabled: bool) -> None:
        """
        Set whether voice is enabled.
        
        Args:
            st: Streamlit module
            enabled: Whether voice is enabled
        """
        st.session_state.voice_enabled = enabled
        
    @staticmethod
    def set_voice_persona(st, persona: str) -> None:
        """
        Set the voice persona.
        
        Args:
            st: Streamlit module
            persona: Voice persona to use
        """
        st.session_state.voice_persona = persona
        
        # Update the voice instance if it exists
        if st.session_state.voice_instance:
            st.session_state.voice_instance.change_persona(persona)
        
    @staticmethod
    def mock_session_state() -> Dict[str, Any]:
        """
        Create a mock session state dictionary for testing.
        
        Returns:
            dict: Mock session state
        """
        return {
            "selected_location_id": 62,
            "selected_location_ids": [62],
            "selected_club": "Idle Hour Country Club",
            "club_locations": {
                "Idle Hour Country Club": {"locations": [62], "default": 62},
                "Pinetree Country Club": {"locations": [61, 66], "default": 61},
                "East Lake Golf Club": {"locations": [16], "default": 16},
            },
            "location_names": {
                62: "Idle Hour Country Club",
                61: "Pinetree Country Club (Location 61)",
                66: "Pinetree Country Club (Location 66)",
                16: "East Lake Golf Club",
            },
            "last_sql_query": None,
            "api_chat_history": [{"role": "system", "content": "Test system prompt"}],
            "full_chat_history": [],
            "date_filter_cache": {
                "start_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            },
        } 