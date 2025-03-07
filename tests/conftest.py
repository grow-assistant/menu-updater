"""
Test configuration and fixtures for pytest.

This module provides fixtures for testing the various services
and components of the restaurant management AI assistant.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from config.settings import Settings
from services.rules_service import RulesManager
from services.sql_generator import SQLGenerator
from services.execution import SQLExecutionLayer
from services.classification import ClassificationService
from services.response_service import ResponseGenerator
from orchestrator import Orchestrator


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Fixture providing test configuration values."""
    return {
        "default_location_id": 62,
        "default_location_name": "Test Restaurant",
        "max_tokens": 100,
        "temperature": 0.7,
        "response_temperature": 0.5,
        "response_max_tokens": 300,
        "max_history_length": 5,
        "max_tts_length": 200,
        "log_level": "INFO",
        "log_file": "test_logs.log"
    }


@pytest.fixture
def mock_settings(test_config) -> Settings:
    """Fixture providing a mocked Settings instance."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.get_config.return_value = test_config
    mock_settings.get_api_key.return_value = "test_api_key"
    return mock_settings


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Fixture providing a mocked OpenAI client."""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    # Set up the response structure
    mock_message.content = "This is a test response"
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    
    return mock_client


@pytest.fixture
def mock_gemini_client() -> MagicMock:
    """Fixture providing a mocked Google Gemini client."""
    mock_client = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    
    # Set up the response structure
    mock_response.text = "SELECT * FROM menu_items WHERE location_id = 62"
    mock_model.generate_content.return_value = mock_response
    mock_client.GenerativeModel.return_value = mock_model
    
    return mock_client


@pytest.fixture
def mock_rules_manager(test_config) -> RulesManager:
    """Fixture providing a RulesManager with test rules."""
    with patch("services.rules.rules_manager.os.path.exists") as mock_exists:
        mock_exists.return_value = True
        
        # Create a mock for file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"test_rule": "test value"}'
            
            rules_manager = RulesManager(config=test_config)
            
            # Mock the load_rules method
            rules_manager.load_rules = MagicMock(return_value={"test_rule": "test value"})
            rules_manager.get_rules_for_query_type = MagicMock(return_value={"test_rule": "test value"})
            
            return rules_manager


@pytest.fixture
def mock_sql_generator(mock_rules_manager, mock_gemini_client, test_config) -> SQLGenerator:
    """Fixture providing a SQLGenerator with mocked dependencies."""
    sql_generator = SQLGenerator(
        ai_client=mock_gemini_client,
        rules_manager=mock_rules_manager,
        config=test_config
    )
    
    # Mock methods
    sql_generator.generate_sql = MagicMock(return_value="SELECT * FROM menu_items WHERE location_id = 62")
    
    return sql_generator


@pytest.fixture
def mock_execution_service(test_config) -> SQLExecutionLayer:
    """Fixture providing an SQLExecutionService with mocked database connection."""
    # Mock the database connection
    with patch("services.execution.sql_execution_layer.psycopg2.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_connection
        
        # Set up mock query results
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}
        ]
        mock_cursor.description = [
            ("id", None, None, None, None, None, None),
            ("name", None, None, None, None, None, None),
            ("price", None, None, None, None, None, None),
            ("location_id", None, None, None, None, None, None)
        ]
        
        execution_service = SQLExecutionLayer(config=test_config)
        
        # Mock methods
        execution_service.execute_query = MagicMock(return_value=[
            {"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}
        ])
        
        return execution_service


@pytest.fixture
def mock_classifier(mock_openai_client, test_config) -> ClassificationService:
    """Fixture providing a ClassificationService with mocked AI client."""
    classifier = ClassificationService(
        ai_client=mock_openai_client,
        config=test_config
    )
    
    # Mock methods
    classifier.classify_query = MagicMock(return_value=(
        "sql_query",
        {"query_type": "menu_query", "date_range": "last week"}
    ))
    
    return classifier


@pytest.fixture
def mock_response_generator(mock_openai_client, test_config) -> ResponseGenerator:
    """Fixture providing a ResponseGenerator with mocked AI client."""
    response_generator = ResponseGenerator(
        ai_client=mock_openai_client,
        config=test_config
    )
    
    # Mock methods
    response_generator.generate_response = MagicMock(
        return_value="Here are the results for your query."
    )
    response_generator.generate_summary = MagicMock(
        return_value="Summary of results."
    )
    
    return response_generator


@pytest.fixture
def mock_orchestrator(
    mock_settings,
    mock_openai_client,
    mock_gemini_client,
    mock_rules_manager,
    mock_sql_generator,
    mock_execution_service,
    mock_classifier,
    mock_response_generator
) -> Orchestrator:
    """Fixture providing an Orchestrator with all mocked dependencies."""
    orchestrator = Orchestrator(settings=mock_settings)
    
    # Replace clients and services with mocks
    orchestrator.openai_client = mock_openai_client
    orchestrator.gemini_client = mock_gemini_client
    orchestrator.rules_manager = mock_rules_manager
    orchestrator.sql_generator = mock_sql_generator
    orchestrator.execution_service = mock_execution_service
    orchestrator.classifier = mock_classifier
    orchestrator.response_generator = mock_response_generator
    
    return orchestrator 