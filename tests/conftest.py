"""
Test configuration and fixtures for pytest.

This module provides fixtures for testing the various services
and components of the restaurant management AI assistant.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
from typing import Dict, Any, List

# Use the compatibility layer for Settings
from config.settings_compat import Settings
from services.rules.rules_manager import RulesManager
from services.sql_generator.sql_generator import SQLGenerator
from services.execution.sql_execution_layer import SQLExecutionLayer
from services.classification.classifier import ClassificationService
from services.response.response_generator import ResponseGenerator
from services.orchestrator.orchestrator import OrchestratorService


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
        "log_file": "test_logs.log",
        # Add services configuration structure expected by RulesManager
        "services": {
            "rules": {
                "rules_path": "resources/rules",
                "resources_dir": "resources",
                "cache_ttl": 60  # Short TTL for testing
            },
            "sql_generator": {
                "examples_path": "resources/sql_examples"
            },
            "execution": {
                "connection_string": "postgresql://test:test@localhost/test_db"
            },
            "classification": {
                "model": "gpt-4"
            },
            "response": {
                "model": "gpt-4"
            }
        }
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
    # First patch os.path.exists to return True for any path
    with patch("services.rules.rules_manager.os.path.exists") as mock_exists:
        mock_exists.return_value = True
        
        # Then patch os.listdir to return a mock directory structure
        with patch("os.listdir") as mock_listdir:
            mock_listdir.return_value = ["menu", "order_history"]
            
            # Then patch open to return mock file contents
            with patch("builtins.open", create=True) as mock_open_obj:
                mock_open_obj.return_value.__enter__.return_value.read.return_value = '{"test_rule": "test value"}'
                
                # Create the RulesManager
                rules_manager = RulesManager(config=test_config)
                
                # Mock the methods we'll use in tests
                rules_manager.load_rules = MagicMock(return_value={"test_rule": "test value"})
                rules_manager.get_rules_for_query_type = MagicMock(return_value={"test_rule": "test value"})
                rules_manager.get_system_rules = MagicMock(return_value={"system_rule": "system value"})
                rules_manager.get_business_rules = MagicMock(return_value={"business_rule": "business value"})
                rules_manager.get_sql_patterns = MagicMock(return_value=["SELECT * FROM items WHERE location_id = {location_id}"])
                rules_manager.format_rules_for_prompt = MagicMock(return_value="Formatted rules text")
                rules_manager.combine_rules = MagicMock(return_value={
                    "system_rule": "system value",
                    "business_rule": "business value",
                    "query_rule": "query value"
                })
                
                return rules_manager


@pytest.fixture
def mock_sql_generator(mock_rules_manager, mock_gemini_client, test_config) -> SQLGenerator:
    """Fixture providing a SQLGenerator with mocked dependencies."""
    max_tokens = test_config.get("max_tokens", 2000)
    temperature = test_config.get("temperature", 0.2)
    
    sql_generator = SQLGenerator(
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    # Set attributes that would normally be initialized elsewhere
    sql_generator.gemini_client = mock_gemini_client
    
    # Mock methods
    sql_generator.generate_sql = MagicMock(return_value={
        "sql": "SELECT * FROM menu_items WHERE location_id = 62",
        "query_type": "menu_query",
        "success": True
    })
    
    return sql_generator


@pytest.fixture
def mock_execution_service(test_config) -> SQLExecutionLayer:
    """Fixture providing an SQLExecutionLayer with mocked database connection."""
    # Mock the get_db_connection context manager directly
    mock_conn = AsyncMock()
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_conn
    mock_context_manager.__aexit__.return_value = None
    
    with patch("services.execution.db_utils.get_db_connection", return_value=mock_context_manager):
        # Mock the execute_query_with_connection function
        with patch("services.execution.db_utils._execute_query_with_connection") as mock_execute:
            # Configure the mock to return test data for SELECT queries
            async def mock_execute_query(*args, **kwargs):
                # First argument is connection, second is query
                if len(args) > 1 and isinstance(args[1], str):
                    query = args[1]
                    if "SELECT" in query.upper():
                        return [
                            {"id": 1, "name": "Test Item 1", "price": 9.99},
                            {"id": 2, "name": "Test Item 2", "price": 14.99}
                        ]
                return []
            
            mock_execute.side_effect = mock_execute_query
            
            # Mock the transaction execution function
            with patch("services.execution.db_utils._execute_transaction_with_connection") as mock_transaction:
                # Configure the mock to succeed
                async def mock_execute_trans(*args, **kwargs):
                    return None
                
                mock_transaction.side_effect = mock_execute_trans
                
                # Create and return the SQLExecutionLayer instance
                sql_execution_layer = SQLExecutionLayer()
                
                return sql_execution_layer


@pytest.fixture
def mock_classifier(mock_openai_client, test_config) -> ClassificationService:
    """Fixture providing a ClassificationService with mocked AI client."""
    # Patch the prompt builder singleton to avoid external dependencies
    with patch("services.classification.classifier.classification_prompt_builder") as mock_prompt_builder:
        # Configure the mock prompt builder
        mock_prompt_builder.get_available_query_types.return_value = [
            "menu_query", "order_history", "performance_query", "ratings_query", "general_question"
        ]
        mock_prompt_builder.build_query_classification_prompt.return_value = "Test classification prompt"
        
        # Create the classifier
        classifier = ClassificationService(
            ai_client=mock_openai_client,
            config=test_config
        )
        
        # Set up the category information
        classifier.categories = [
            "menu_query", "order_history", "performance_query", "ratings_query", "general_question"
        ]
        
        # Mock the methods
        classifier.classify = MagicMock(return_value={
            "category": "menu_query",
            "confidence": 0.95,
            "entities": {"menu_item": "burger", "location_id": 62}
        })
        
        classifier.classify_query = MagicMock(return_value={
            "query_type": "menu_query",
            "confidence": 0.95,
            "entities": {"menu_item": "burger", "location_id": 62},
            "classification_method": "ai_model",
            "intent": "get_menu_items",
            "date_range": "current"
        })
        
        # Mock async method with a coroutine
        async def mock_classify_async(*args, **kwargs):
            return {
                "query_type": "menu_query",
                "confidence": 0.95,
                "entities": {"menu_item": "burger", "location_id": 62},
                "classification_method": "ai_model",
                "intent": "get_menu_items",
                "date_range": "current"
            }
        
        classifier.classify_query_async = MagicMock(side_effect=mock_classify_async)
        
        # Utility methods
        classifier.health_check = MagicMock(return_value=True)
        classifier.clear_cache = MagicMock()
        
        return classifier


@pytest.fixture
def mock_response_generator(mock_openai_client, test_config) -> ResponseGenerator:
    """Fixture providing a ResponseGenerator with mocked AI client."""
    # Patch the template loading functionality
    with patch("services.response.response_generator.Path") as mock_path:
        # Configure the mock path
        mock_template_path = MagicMock()
        mock_template_path.exists.return_value = True
        mock_path.return_value = mock_template_path
        
        # Patch file reading
        with patch("builtins.open", mock_open(read_data="Test response template")) as mock_open_obj:
            # Configure the OpenAI client within the test_config
            # Update test_config to include necessary API keys
            if 'api' not in test_config:
                test_config['api'] = {}
            if 'openai' not in test_config['api']:
                test_config['api']['openai'] = {}
            if 'elevenlabs' not in test_config['api']:
                test_config['api']['elevenlabs'] = {}
                
            # Create the response generator with the updated config
            response_generator = ResponseGenerator(
                config=test_config
            )
            
            # Mock the client that would have been created internally
            response_generator.client = mock_openai_client
            
            # Configure properties
            response_generator.persona = "casual"
            response_generator.template_dir = "test_templates"
            
            # Mock core methods
            response_generator.generate = MagicMock(return_value={
                "response": "Here are the results for your query.",
                "thought_process": "Analyzed the query and generated a response.",
                "time_ms": 42
            })
            
            response_generator.generate_response = MagicMock(
                return_value="Here are the results for your query."
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
) -> OrchestratorService:
    """Fixture providing an OrchestratorService with mocked components."""
    # Create a mock config
    config = mock_settings.get_config()
    
    # Create the orchestrator with mock services
    with patch("services.utils.service_registry.ServiceRegistry.get_service") as mock_get_service:
        # Configure the get_service method to return the appropriate mock
        def mock_get_service_impl(service_name):
            if service_name == "classification":
                return mock_classifier
            elif service_name == "rules":
                return mock_rules_manager
            elif service_name == "sql_generator":
                return mock_sql_generator
            elif service_name == "execution":
                return mock_execution_service
            elif service_name == "response":
                return mock_response_generator
            else:
                return MagicMock()
        
        mock_get_service.side_effect = mock_get_service_impl
        
        # Create the orchestrator
        orchestrator = OrchestratorService(config=config)
        
        # Manually set the service references
        orchestrator.classifier = mock_classifier
        orchestrator.rules = mock_rules_manager
        orchestrator.sql_generator = mock_sql_generator
        orchestrator.sql_executor = mock_execution_service
        orchestrator.response_generator = mock_response_generator
        
        # Mock other attributes
        orchestrator.current_location_id = config.get("default_location_id", 62)
        orchestrator.current_location_name = config.get("default_location_name", "Test Restaurant")
        
        # Initialize conversation history
        orchestrator.conversation_history = []
        orchestrator.sql_history = []
        
        # Save the original process_query method
        original_process_query = orchestrator.process_query
        
        # Create a new async version that wraps the original
        async def async_process_query(query, context=None, fast_mode=True):
            # Call the original method and return its result as an awaitable
            result = original_process_query(query, context, fast_mode)
            return result
            
        # Replace the process_query method with our async version
        orchestrator.process_query = async_process_query
        
        # Return the modified orchestrator object
        return orchestrator 