"""
Frontend module for the AI Restaurant Assistant application.
"""
import streamlit as st
import yaml
import os
import logging
from typing import Dict, Any

from services.orchestrator.orchestrator import OrchestratorService
from frontend.session_manager import SessionManager
from .components.sidebar import render_sidebar

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load application configuration."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Replace environment variables
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = replace_env_vars(value)
            return obj
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            # Handle default values with colon syntax
            if ":-" in env_var:
                env_var, default_value = env_var.split(":-", 1)
            else:
                default_value = ""
            env_value = os.environ.get(env_var, default_value)
            if env_value is None:
                logger.warning(f"Environment variable {env_var} not found")
                return default_value
            return env_value
        else:
            return obj
    
    # Apply recursive replacement
    config = replace_env_vars(config)
    
    return config

def run_app():
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="Swoop AI",
        page_icon="",
        layout="wide"
    )
    
    # Load configuration
    config = load_config()
    
    # Initialize session state
    SessionManager.initialize_session()
    
    # Initialize the orchestrator if not already in session state
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = OrchestratorService(config)
    
    # Render the sidebar
    render_sidebar(st)
    
    st.title("Swoop AI")
    
    # Display chat history
    for entry in st.session_state.history:
        with st.chat_message("user"):
            st.markdown(entry["query"])
        with st.chat_message("assistant"):
            st.markdown(entry["response"])
    
    # Get user input
    query = st.chat_input("Ask me anything about the restaurant...")
    
    if query:
        # Display user message
        with st.chat_message("user"):
            st.markdown(query)
        
        # Create a placeholder for the assistant's response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Get context from session manager
            context = SessionManager.get_context()
            
            # The enable_verbal setting is now included in the context from SessionManager
            # based on the voice_enabled checkbox in the sidebar
            
            # Process the query
            result = st.session_state.orchestrator.process_query(query, context)
            
            # Display the response
            message_placeholder.markdown(result["response"])
            
            # Play verbal response if available
            if result.get("verbal_audio"):
                import base64
                audio_base64 = base64.b64encode(result["verbal_audio"]).decode()
                audio_html = f"""
                    <audio autoplay="true" style="display:block; margin-top:10px;">
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                        Your browser does not support the audio element.
                    </audio>
                """
                st.markdown(audio_html, unsafe_allow_html=True)
                logger.info(f"Playing verbal response audio: {len(result['verbal_audio'])} bytes")
            
            # Optionally show SQL and results in an expandable section
            if result.get("sql_query"):
                with st.expander("View SQL and Results", expanded=False):
                    st.code(result["sql_query"], language="sql")
                    if result.get("query_results"):
                        st.json(result["query_results"])
            
            # Show debugging information when needed
            with st.expander("Debug Info", expanded=False):
                st.write("**Voice Response Status:**")
                if result.get("has_verbal", False):
                    st.success("✅ Verbal response was generated")
                else:
                    st.warning("⚠️ No verbal response was generated")
                    reasons = []
                    if not context.get("enable_verbal", False):
                        reasons.append("Voice responses are disabled in settings")
                    if result.get("fast_mode", False):
                        reasons.append("Fast mode is enabled (verbal responses skipped)")
                    
                    if reasons:
                        st.write("**Reasons:**")
                        for reason in reasons:
                            st.write(f"- {reason}")
                        st.write("*To enable voice responses, check 'Enable voice responses' in Voice Settings in the sidebar.*")
        
        # Update history using session manager
        SessionManager.update_history(query, result)

# Ensure components are accessible through the frontend module
__all__ = ["run_app", "render_sidebar"]
