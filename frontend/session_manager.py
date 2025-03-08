import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    @staticmethod
    def initialize_session():
        logger.debug("Initializing session state.")
        """Initialize all required session state variables."""
        if "history" not in st.session_state:
            st.session_state.history = []
        
        if "context" not in st.session_state:
            st.session_state.context = {
                "user_preferences": {},
                "recent_queries": [],
                "active_conversation": True
            }
        
        if "ui_state" not in st.session_state:
            st.session_state.ui_state = {
                "show_sql": False,
                "show_results": False,
                "current_view": "chat"
            }
            
        # Initialize voice settings
        if "voice_enabled" not in st.session_state:
            st.session_state.voice_enabled = True
            
        # Initialize persona if not set
        if "persona" not in st.session_state:
            st.session_state.persona = "casual"
        
        logger.debug(f"Session state initialized: {st.session_state}")
    
    @staticmethod
    def get_context() -> Dict[str, Any]:
        context = {
            "session_history": st.session_state.history,
            "user_preferences": st.session_state.context.get("user_preferences", {}),
            "recent_queries": st.session_state.context.get("recent_queries", []),
            "enable_verbal": st.session_state.voice_enabled if hasattr(st.session_state, "voice_enabled") else True,
            "persona": st.session_state.persona if hasattr(st.session_state, "persona") else "casual"
        }
        logger.debug(f"Context retrieved: {context}")
        return context
    
    @staticmethod
    def update_history(query: str, result: Dict[str, Any]):
        logger.debug(f"Updating history with query: {query}, result: {result}")
        """Update chat history with latest interaction."""
        try:
            # Safely get category with default
            category = result.get("category", "general")
            
            st.session_state.history.append({
                "timestamp": datetime.now(),
                "query": query,
                "response": result.get("response", ""),
                "category": category,  # Use safely retrieved category
                "sql_query": result.get("sql_query"),
                "results": result.get("query_results")
            })
            
            # Keep history bounded
            if len(st.session_state.history) > 100:
                st.session_state.history.pop(0)
            
        except Exception as e:
            logger.error(f"Error updating history: {str(e)}")
            logger.debug(f"Failed result data: {result}")
        
        # Keep only the last 10 queries in recent_queries
        recent = st.session_state.context.get("recent_queries", [])
        recent.append(query)
        st.session_state.context["recent_queries"] = recent[-10:] 
        
        logger.debug(f"Updated session history: {st.session_state.history}")
        logger.debug(f"Updated recent queries: {st.session_state.context['recent_queries']}") 