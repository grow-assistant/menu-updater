"""
Headless Streamlit Adapter for AI Testing

This module provides a headless version of Streamlit that can be used for automated testing
without requiring a browser UI. It captures all interactions and simulates Streamlit's
session state management.
"""

import time
import uuid
import logging
from typing import Optional, Dict, List, Any, Callable, ContextManager
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class MessageContainer:
    """Simulates the st.chat_message context manager."""
    
    def __init__(self, role: str, parent_streamlit):
        self.role = role
        self.parent = parent_streamlit
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def write(self, text: str) -> None:
        """Simulate writing text to a chat message container."""
        self.parent.capture_response(text, self.role)


class HeadlessStreamlit:
    """A headless version of streamlit that captures all interactions."""
    
    def __init__(self):
        self.session_state = {}
        self.messages = []
        self.terminal_output = []
        self.session_id = self._generate_session_id()
        self.start_time = time.time()
        self.current_input = None
        self.last_input_time = self.start_time
        
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
        
    def chat_input(self, placeholder: str = "Type a message...") -> Optional[str]:
        """Simulate the st.chat_input function."""
        # This will be filled by the testing agent
        return self.current_input if hasattr(self, 'current_input') else None
        
    @contextmanager
    def chat_message(self, role: str):
        """Simulate the st.chat_message context manager."""
        container = MessageContainer(role, self)
        yield container
        
    def capture_response(self, text: str, role: str = "assistant") -> None:
        """Capture responses that would normally go to the UI."""
        timestamp = time.time()
        response = {
            "text": text,
            "role": role,
            "timestamp": timestamp,
            "response_time": timestamp - self.last_input_time if self.last_input_time else 0,
            "session_id": self.session_id
        }
        self.terminal_output.append(response)
        self.messages.append({"role": role, "content": text})
        logger.debug(f"Captured response: {text[:100]}...")
        
    def set_input(self, text: str) -> None:
        """Set the current input to be processed."""
        self.current_input = text
        self.last_input_time = time.time()
        self.messages.append({"role": "user", "content": text})
        logger.debug(f"Set input: {text}")
        
    def reset(self) -> None:
        """Reset the session state."""
        self.session_state = {}
        self.messages = []
        # Keep the session ID and start time for tracking
        
    def create_concurrent_session(self) -> 'HeadlessStreamlit':
        """Create a new session running concurrently."""
        new_session = HeadlessStreamlit()
        return new_session
    
    # Additional methods to simulate other Streamlit functions
    
    def text_input(self, label: str, value: str = "", key: Optional[str] = None) -> str:
        """Simulate st.text_input function."""
        if key and key in self.session_state:
            return self.session_state[key]
        return value
    
    def button(self, label: str, key: Optional[str] = None) -> bool:
        """Simulate st.button function."""
        # Always return False in headless mode unless explicitly set
        return False
    
    def select_box(self, label: str, options: List[Any], index: int = 0, key: Optional[str] = None) -> Any:
        """Simulate st.selectbox function."""
        if key and key in self.session_state:
            return self.session_state[key]
        return options[index] if options else None
    
    def write(self, obj: Any) -> None:
        """Simulate st.write function."""
        self.capture_response(str(obj), "info")
    
    def error(self, message: str) -> None:
        """Simulate st.error function."""
        self.capture_response(f"ERROR: {message}", "error")
    
    def warning(self, message: str) -> None:
        """Simulate st.warning function."""
        self.capture_response(f"WARNING: {message}", "warning")
    
    def success(self, message: str) -> None:
        """Simulate st.success function."""
        self.capture_response(f"SUCCESS: {message}", "success")
    
    def info(self, message: str) -> None:
        """Simulate st.info function."""
        self.capture_response(f"INFO: {message}", "info") 