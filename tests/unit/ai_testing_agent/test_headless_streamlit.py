"""
Unit tests for the HeadlessStreamlit class.
"""

import pytest
import time
from unittest.mock import patch
from ai_testing_agent.headless_streamlit import HeadlessStreamlit, MessageContainer

class TestHeadlessStreamlit:
    """Tests for the HeadlessStreamlit class."""
    
    def test_initialization(self):
        """Test that the HeadlessStreamlit initializes with the correct attributes."""
        st = HeadlessStreamlit()
        
        assert hasattr(st, 'session_state')
        assert isinstance(st.session_state, dict)
        assert hasattr(st, 'messages')
        assert isinstance(st.messages, list)
        assert hasattr(st, 'terminal_output')
        assert isinstance(st.terminal_output, list)
        assert hasattr(st, 'session_id')
        assert isinstance(st.session_id, str)
        assert hasattr(st, 'start_time')
        assert isinstance(st.start_time, float)
        
    def test_chat_input(self):
        """Test the chat_input method returns the current input."""
        st = HeadlessStreamlit()
        
        # Initially, current_input is None
        assert st.chat_input() is None
        
        # Set current_input and verify chat_input returns it
        st.current_input = "Hello, world!"
        assert st.chat_input() == "Hello, world!"
        
        # Test with a placeholder
        assert st.chat_input("Type something...") == "Hello, world!"
        
    def test_chat_message(self):
        """Test the chat_message context manager."""
        st = HeadlessStreamlit()
        
        with st.chat_message("user") as container:
            assert isinstance(container, MessageContainer)
            assert container.role == "user"
            assert container.parent == st
            
            # Test writing to the container
            container.write("Hello, world!")
            
        # Verify the message was captured
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "Hello, world!"
        assert st.terminal_output[0]["role"] == "user"
        
    def test_capture_response(self):
        """Test the capture_response method."""
        st = HeadlessStreamlit()
        st.last_input_time = time.time() - 1  # Set last_input_time to 1 second ago
        
        st.capture_response("Test response", "assistant")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "Test response"
        assert st.terminal_output[0]["role"] == "assistant"
        assert st.terminal_output[0]["session_id"] == st.session_id
        assert "response_time" in st.terminal_output[0]
        assert st.terminal_output[0]["response_time"] > 0
        
        # Check that the message was added to messages list
        assert len(st.messages) == 1
        assert st.messages[0]["role"] == "assistant"
        assert st.messages[0]["content"] == "Test response"
        
    def test_set_input(self):
        """Test the set_input method."""
        st = HeadlessStreamlit()
        
        # Record the current time to check last_input_time
        before = time.time()
        st.set_input("Test input")
        after = time.time()
        
        assert st.current_input == "Test input"
        assert st.last_input_time >= before
        assert st.last_input_time <= after
        
        # Check that the message was added to messages list
        assert len(st.messages) == 1
        assert st.messages[0]["role"] == "user"
        assert st.messages[0]["content"] == "Test input"
        
    def test_reset(self):
        """Test the reset method."""
        st = HeadlessStreamlit()
        
        # Add some data to session_state and messages
        st.session_state["key"] = "value"
        st.messages.append({"role": "user", "content": "Hello"})
        
        # Reset the session
        st.reset()
        
        # Verify session_state and messages are reset
        assert st.session_state == {}
        assert st.messages == []
        
        # Session ID and start_time should be preserved
        assert hasattr(st, 'session_id')
        assert hasattr(st, 'start_time')
        
    def test_create_concurrent_session(self):
        """Test creating a concurrent session."""
        st = HeadlessStreamlit()
        
        concurrent_session = st.create_concurrent_session()
        
        assert isinstance(concurrent_session, HeadlessStreamlit)
        assert concurrent_session.session_id != st.session_id
        
    def test_text_input(self):
        """Test the text_input method."""
        st = HeadlessStreamlit()
        
        # Without a key in session_state
        assert st.text_input("Label", "default") == "default"
        
        # With a key in session_state
        st.session_state["my_key"] = "session_value"
        assert st.text_input("Label", "default", key="my_key") == "session_value"
        
    def test_button(self):
        """Test the button method."""
        st = HeadlessStreamlit()
        
        # In headless mode, buttons always return False
        assert st.button("Click me") is False
        assert st.button("Click me", key="button1") is False
        
    def test_select_box(self):
        """Test the select_box method."""
        st = HeadlessStreamlit()
        
        options = ["Option 1", "Option 2", "Option 3"]
        
        # Without a key in session_state
        assert st.select_box("Select", options) == "Option 1"
        assert st.select_box("Select", options, index=2) == "Option 3"
        
        # With a key in session_state
        st.session_state["select_key"] = "Option 2"
        assert st.select_box("Select", options, key="select_key") == "Option 2"
        
        # Empty options list
        assert st.select_box("Select", []) is None
        
    def test_write(self):
        """Test the write method."""
        st = HeadlessStreamlit()
        
        st.write("Test message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "Test message"
        assert st.terminal_output[0]["role"] == "info"
        
    def test_error(self):
        """Test the error method."""
        st = HeadlessStreamlit()
        
        st.error("Error message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "ERROR: Error message"
        assert st.terminal_output[0]["role"] == "error"
        
    def test_warning(self):
        """Test the warning method."""
        st = HeadlessStreamlit()
        
        st.warning("Warning message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "WARNING: Warning message"
        assert st.terminal_output[0]["role"] == "warning"
        
    def test_success(self):
        """Test the success method."""
        st = HeadlessStreamlit()
        
        st.success("Success message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "SUCCESS: Success message"
        assert st.terminal_output[0]["role"] == "success"
        
    def test_info(self):
        """Test the info method."""
        st = HeadlessStreamlit()
        
        st.info("Info message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "INFO: Info message"
        assert st.terminal_output[0]["role"] == "info"


class TestMessageContainer:
    """Tests for the MessageContainer class."""
    
    def test_initialization(self):
        """Test that the MessageContainer initializes with the correct attributes."""
        st = HeadlessStreamlit()
        container = MessageContainer("user", st)
        
        assert container.role == "user"
        assert container.parent == st
        
    def test_context_manager(self):
        """Test the context manager protocol."""
        st = HeadlessStreamlit()
        
        with MessageContainer("user", st) as container:
            assert container.role == "user"
            assert container.parent == st
            
    def test_write(self):
        """Test writing to the container."""
        st = HeadlessStreamlit()
        container = MessageContainer("user", st)
        
        container.write("Test message")
        
        assert len(st.terminal_output) == 1
        assert st.terminal_output[0]["text"] == "Test message"
        assert st.terminal_output[0]["role"] == "user" 