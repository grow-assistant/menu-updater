"""Mock objects and functions for testing"""
from unittest.mock import MagicMock

def mock_streamlit():
    """Mock streamlit session state and functions"""
    import sys
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.chat_message.return_value.write = MagicMock()
    sys.modules["streamlit"] = mock_st
    return mock_st

def mock_database():
    """Mock database connection and cursor"""
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_connection, mock_cursor

def mock_openai():
    """Mock OpenAI API calls"""
    import sys
    mock_openai = MagicMock()
    mock_openai.ChatCompletion.create.return_value = {
        "choices": [{
            "message": {
                "content": "Test response",
                "role": "assistant"
            }
        }]
    }
    sys.modules["openai"] = mock_openai
    return mock_openai
