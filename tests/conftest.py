import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db_connection():
    """
    Create a mock database connection for testing
    """
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value = mock_cursor

    return mock_connection


@pytest.fixture
def mock_openai_client():
    """
    Create a mock OpenAI client for testing
    """
    client = MagicMock()

    # Mock common OpenAI methods
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="This is a mock response from OpenAI", role="assistant"
            )
        )
    ]

    # Support both new and old OpenAI client styles
    client.chat.completions.create.return_value = mock_response
    client.ChatCompletion.create.return_value = {
        "choices": [
            {
                "message": {
                    "content": "This is a mock response from OpenAI",
                    "role": "assistant",
                }
            }
        ]
    }

    return client


@pytest.fixture
def mock_grok_client():
    """
    Create a mock Grok/Gemini client for testing
    """
    client = MagicMock()

    mock_response = MagicMock()
    mock_response.text = "This is a mock response from Grok/Gemini"

    client.generate_content.return_value = mock_response

    return client


@pytest.fixture
def sample_menu_item():
    """
    Return a sample menu item for testing
    """
    return {
        "id": 1,
        "name": "Cheeseburger",
        "price": 9.99,
        "description": "A delicious burger with cheese",
        "category_id": 2,
        "is_available": True,
    }


@pytest.fixture
def sample_menu_items():
    """
    Return a list of sample menu items for testing
    """
    return [
        {
            "id": 1,
            "name": "Cheeseburger",
            "price": 9.99,
            "description": "A delicious burger with cheese",
            "category_id": 2,
            "is_available": True,
        },
        {
            "id": 2,
            "name": "Veggie Burger",
            "price": 8.99,
            "description": "A plant-based burger",
            "category_id": 2,
            "is_available": True,
        },
        {
            "id": 3,
            "name": "French Fries",
            "price": 3.99,
            "description": "Crispy golden fries",
            "category_id": 3,
            "is_available": True,
        },
    ]


@pytest.fixture
def mock_streamlit():
    """
    Mock Streamlit for testing
    """
    with patch("streamlit.session_state", {"messages": [], "history": []}):
        yield
