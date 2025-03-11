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
import yaml
from pathlib import Path

from config.settings import Config
from services.rules.rules_manager import RulesManager
from services.sql_generator.sql_generator import SQLGenerator
from services.execution.sql_execution_layer import SQLExecutionLayer
from services.classification.classifier import ClassificationService
from services.response.response_generator import ResponseGenerator
from services.orchestrator.orchestrator import Orchestrator


@pytest.fixture
def connection_string():
    """Fixture that provides a test database connection string for tests."""
    # Use a test connection string - ideally an in-memory database for tests
    return "sqlite:///:memory:"


@pytest.fixture
def text():
    """Fixture that provides test text for voice generation tests."""
    return "This is a test text for voice generation."


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Fixture that provides a test configuration with all required sections."""
    return {
        "api": {
            "openai": {"api_key": "test-key", "model": "gpt-4o"},
            "gemini": {"api_key": "test-key", "model": "gemini-pro"},
            "elevenlabs": {"api_key": "test-key"}
        },
        "database": {
            "connection_string": "sqlite:///:memory:",
            "max_rows": 1000,
            "timeout": 30
        },
        "services": {
            "classification": {
                "confidence_threshold": 0.7
            },
            "rules": {
                "rules_path": "tests/test_data/rules",
                "resources_dir": "tests/test_data",
                "sql_files_path": "tests/test_data/sql_patterns",
                "cache_ttl": 60
            },
            "sql_generator": {
                "template_path": "tests/test_data/templates"
            }
        },
        "logging": {
            "level": "INFO"
        }
    }


@pytest.fixture
def mock_settings(test_config) -> Config:
    """Fixture providing a mocked Settings instance."""
    mock_settings = MagicMock(spec=Config)
    
    # Set up the get_config method
    mock_settings.get_config.return_value = test_config
    
    # Set up the get method to handle both direct config access and get_config calls
    def mock_get(key, default=None):
        # Check if key is in the test_config
        if key in test_config:
            return test_config[key]
        # Check if key has dots (e.g., "api.openai.api_key")
        elif "." in key:
            parts = key.split(".")
            current = test_config
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return default
            return current
        return default
    
    mock_settings.get = mock_get
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
    # Prepare a config with the expected structure
    test_config = {
        **test_config,
        "services": {
            "sql_generator": {
                "examples_path": "./services/sql_generator/sql_files"
            }
        }
    }
    
    with patch("services.rules.rules_manager.os.path.exists") as mock_exists:
        mock_exists.return_value = True
        
        # Create a mock for file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"test_rule": "test value"}'
            
            # Create a mock for os.listdir to return empty list and avoid trying to read real files
            with patch("os.listdir", return_value=[]):
                rules_manager = RulesManager(config=test_config)
                
                # Mock the load_rules method
                rules_manager._load_rules = MagicMock(return_value={"test_rule": "test value"})
                rules_manager.get_rules_and_examples = MagicMock(return_value={"test_rule": "test value"})
                
                return rules_manager


@pytest.fixture
def mock_sql_generator(mock_rules_manager, mock_gemini_client, test_config) -> SQLGenerator:
    """Fixture providing a SQLGenerator with mocked dependencies."""
    sql_generator = SQLGenerator(
        max_tokens=test_config.get("max_tokens", 2000),
        temperature=test_config.get("temperature", 0.7)
    )
    
    # Set the gemini client
    sql_generator.gemini_client = mock_gemini_client
    
    # Mock methods
    sql_generator.generate_sql = MagicMock(return_value="SELECT * FROM menu_items WHERE location_id = 62")
    
    return sql_generator


@pytest.fixture
def mock_execution_service(test_config) -> SQLExecutionLayer:
    """Fixture providing an SQLExecutionLayer with mocked database connection."""
    # Mock the execute_query function in db_utils, which is imported by sql_execution_layer
    with patch("services.execution.db_utils.execute_query") as mock_execute_query:
        # Set the return value for the mock
        async def mock_execute_query_async(*args, **kwargs):
            return [
                {"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}
            ]
        
        # Set the mock to return our async function results
        mock_execute_query.side_effect = mock_execute_query_async
        
        # Create the execution layer instance
        execution_layer = SQLExecutionLayer()
        
        # Mock the execute_sql and execute_sql_sync methods
        async def mock_execute_sql(*args, **kwargs):
            return {
                "success": True,
                "data": [{"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}],
                "execution_time": 0.1,
                "row_count": 1,
                "truncated": False,
                "query": args[0] if args else kwargs.get("query", "")
            }
        
        execution_layer.execute_sql = MagicMock(side_effect=mock_execute_sql)
        execution_layer.execute_sql_sync = MagicMock(return_value={
            "success": True,
            "data": [{"id": 1, "name": "Test Item", "price": 10.99, "location_id": 62}],
            "execution_time": 0.1,
            "row_count": 1,
            "truncated": False,
            "query": "SELECT * FROM menu_items"
        })
        
        return execution_layer


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
    # Add OpenAI client to test_config
    test_config = {
        **test_config,
        "openai_client": mock_openai_client
    }
    
    with patch("services.response.response_generator.OpenAI", return_value=mock_openai_client):
        response_generator = ResponseGenerator(config=test_config)
        
        # Mock methods
        response_generator.generate = MagicMock(
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