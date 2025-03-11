"""
Sidebar components for the Restaurant AI Assistant application.
This module provides the sidebar interface for the Streamlit UI.
"""

# Standard library imports
from typing import Any, Dict, Optional
import os

# Application imports
from resources.ui.personas import list_personas

# Constants - using the restaurant locations from your app
LOCATIONS = {
    "Idle Hour Country Club": 62,
    "Pinetree Country Club (Main)": 61,
    "Pinetree Country Club (Grill)": 66,
    "East Lake Golf Club": 16
}

def render_sidebar(st_obj: Any, session: Optional[Any] = None) -> None:
    """
    Render the sidebar components for restaurant assistant.

    Args:
        st_obj: The Streamlit module instance
        session: Optional session manager instance
    """
    # Add logo at the top (centered)
    logo_path = os.path.join("resources", "ui", "swoop-logo.png")
    if os.path.exists(logo_path):
        # Use a column to center the image
        col1, col2, col3 = st_obj.sidebar.columns([1, 2, 1])
        with col2:
            st_obj.image(logo_path, width=150)
    
    # Add a divider
    st_obj.sidebar.markdown("---")

    # Restaurant location selection
    selected_restaurant = st_obj.sidebar.selectbox(
        "Select Restaurant",
        options=list(LOCATIONS.keys()),
        index=(
            list(LOCATIONS.keys()).index(st_obj.session_state.location)
            if hasattr(st_obj.session_state, "location") and 
               st_obj.session_state.location in LOCATIONS
            else 0
        ),
        key="restaurant_selector",
    )

    # Update selected restaurant if changed
    if hasattr(st_obj.session_state, "location") and selected_restaurant != st_obj.session_state.location:
        st_obj.session_state.location = selected_restaurant
        st_obj.session_state.location_id = LOCATIONS[selected_restaurant]
        if hasattr(st_obj.session_state, "orchestrator"):
            st_obj.session_state.orchestrator.set_location(
                st_obj.session_state.location_id, 
                selected_restaurant
            )

        # Clear chat history when changing restaurants
        st_obj.session_state.messages = []

        # Show a notification
        st_obj.sidebar.success(f"Switched to {selected_restaurant}. Chat history cleared.")

    # Voice settings expander
    with st_obj.sidebar.expander("🔊 Voice Settings", expanded=False):
        voice_enabled = st_obj.checkbox(
            "Enable voice responses",
            value=st_obj.session_state.voice_enabled if hasattr(st_obj.session_state, "voice_enabled") else True,
            help="Turn on/off voice responses",
            key="voice_enabled_checkbox",
        )

        # Update voice enabled status if changed
        if hasattr(st_obj.session_state, "voice_enabled") and voice_enabled != st_obj.session_state.voice_enabled:
            st_obj.session_state.voice_enabled = voice_enabled
            if voice_enabled:
                st_obj.success("Voice responses enabled")
            else:
                st_obj.info("Voice responses disabled")

        # Add persona selector
        available_personas = list_personas()
        
        # Get current persona or use default
        current_persona = "casual"
        if hasattr(st_obj.session_state, "persona") and st_obj.session_state.persona in available_personas:
            current_persona = st_obj.session_state.persona

        # Display current persona info
        st_obj.markdown("**Current Persona:**")
        st_obj.info(f"{current_persona.title()} - {available_personas[current_persona]}")

        # Persona selection
        selected_persona = st_obj.selectbox(
            "Voice Persona",
            options=list(available_personas.keys()),
            format_func=lambda x: f"{x.title()} - {available_personas[x]}",
            index=list(available_personas.keys()).index(current_persona),
            help="Select voice persona style for responses",
            key="voice_persona_selector",
        )

        # Update persona if changed
        if hasattr(st_obj.session_state, "persona") and selected_persona != st_obj.session_state.persona:
            st_obj.session_state.persona = selected_persona
            if hasattr(st_obj.session_state, "orchestrator"):
                st_obj.session_state.orchestrator.set_persona(selected_persona)
            st_obj.success(f"Changed to {selected_persona} voice persona")

    # Voice input settings
    with st_obj.sidebar.expander("🎤 Voice Input Settings", expanded=False):
        st_obj.write("Speech recognition settings:")

        # Initialize auto-listen if not present
        if not hasattr(st_obj.session_state, "auto_listen_enabled"):
            st_obj.session_state.auto_listen_enabled = False
        
        if not hasattr(st_obj.session_state, "auto_listen_timeout"):
            st_obj.session_state.auto_listen_timeout = 3

        # Add auto-listen option
        auto_listen = st_obj.checkbox(
            "Auto-listen after AI responds",
            value=st_obj.session_state.auto_listen_enabled,
            help="Automatically listen for your next question after the AI finishes speaking",
            key="auto_listen_checkbox",
        )

        # Update auto-listen status if changed
        if auto_listen != st_obj.session_state.auto_listen_enabled:
            st_obj.session_state.auto_listen_enabled = auto_listen
            if auto_listen:
                st_obj.success("Auto-listen enabled")
            else:
                st_obj.info("Auto-listen disabled")

        # Set timeout settings for auto-listen
        if st_obj.session_state.auto_listen_enabled:
            st_obj.session_state.auto_listen_timeout = st_obj.slider(
                "Silence timeout (seconds)",
                min_value=1,
                max_value=10,
                value=st_obj.session_state.auto_listen_timeout,
                help="Stop listening if no speech is detected after this many seconds",
                key="auto_listen_timeout_slider",
            )

        # Add button to test voice input
        if st_obj.button("Test Voice Input", key="test_voice_input_button"):
            try:
                # Attempt to import speech recognition library
                import speech_recognition as sr  # noqa: F401
                st_obj.success("✅ Speech recognition library is available!")

                # Check if PyAudio is available
                try:
                    import pyaudio  # noqa: F401
                    st_obj.success("✅ PyAudio is available!")
                except ImportError:
                    st_obj.error("❌ PyAudio is not available. Install with: pip install PyAudio")
            except ImportError:
                st_obj.error(
                    "❌ Speech recognition library is not available. "
                    "Install with: pip install SpeechRecognition"
                )

    # Add clear chat history button at the bottom
    if st_obj.sidebar.button(
        "Clear Chat History",
        use_container_width=True,
        key="clear_history_button",
    ):
        st_obj.session_state.messages = []
        st_obj.rerun() 