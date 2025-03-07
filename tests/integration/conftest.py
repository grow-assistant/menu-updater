"""
Fixtures for integration tests.

This module contains fixtures that are specifically designed for integration tests,
focusing on testing component interactions with partially mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import asyncio
from typing import Dict, Any, List

# Import the components needed for integration testing
from services.orchestrator.orchestrator import OrchestratorService
from services.classification.classifier import ClassificationService
from services.response.response_generator import ResponseGenerator
from services.sql_generator.sql_generator import SQLGenerator
from services.execution.sql_executor import SQLExecutor
from services.utils.service_registry import ServiceRegistry


@pytest.fixture
def integration_test_config() -> Dict[str, Any]:
    """
    Provide a standardized configuration dictionary for integration tests.
    
    This fixture creates a complete configuration dictionary with all necessary
    sections for testing component interactions.
    
    Returns:
        Dict[str, Any]: Configuration dictionary with test values
    """
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
        "max_sql_retries": 3,
        "api": {
            "openai": {
                "api_key": "test-api-key",
                "model": "gpt-4o-mini"
            },
            "gemini": {
                "api_key": "test-gemini-key",
                "model": "gemini-pro"
            },
            "elevenlabs": {
                "api_key": "test-elevenlabs-key"
            }
        },
        "services": {
            "classification": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "cache_size": 100,
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 50
            },
            "rules": {
                "rules_path": "test_rules",
                "resources_dir": "test_resources",
                "cache_ttl": 300
            },
            "sql_generator": {
                "examples_path": "test_examples",
                "max_tokens": 500,
                "temperature": 0.2
            },
            "execution": {
                "connection_string": "postgresql://test:test@localhost/test_db",
                "timeout": 10,
                "max_connections": 5,
                "query_limit": 100
            },
            "response_generation": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "cache_size": 100,
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 500
            }
        },
        "database": {
            "connection_string": "postgresql://test:test@localhost/test_db",
            "max_connections": 5,
            "timeout": 10
        }
    }


@pytest.fixture
def mock_service_registry(
    integration_test_config,
    mock_classifier,
    mock_sql_generator,
    mock_sql_executor,
    mock_response_generator
):
    """
    Provide a mocked ServiceRegistry for integration tests.
    
    This fixture creates a configured ServiceRegistry with mocked service
    implementations for integration testing.
    
    Args:
        integration_test_config: Test configuration dictionary
        mock_classifier: Mocked classifier service
        mock_sql_generator: Mocked SQL generator service
        mock_sql_executor: Mocked SQL executor service
        mock_response_generator: Mocked response generator service
        
    Returns:
        MagicMock: A configured ServiceRegistry mock
    """
    registry = MagicMock(spec=ServiceRegistry)
    
    # Create a dictionary of services
    services = {
        "classification": mock_classifier,
        "sql_generator": mock_sql_generator,
        "execution": mock_sql_executor,
        "response": mock_response_generator
    }
    
    # Configure the get method to return appropriate services
    def get_service_side_effect(service_name):
        if service_name in services:
            return services[service_name]
        else:
            raise ValueError(f"Unknown service: {service_name}")
            
    registry.get.side_effect = get_service_side_effect
    
    # Add a register method
    def register_service(name, service_factory):
        services[name] = service_factory(integration_test_config)
        return True
        
    registry.register = MagicMock(side_effect=register_service)
    
    return registry


@pytest.fixture
def integration_orchestrator(integration_test_config, mock_service_registry):
    """
    Provide an OrchestratorService with mocked component services.
    
    This fixture creates an OrchestratorService instance that uses mocked
    services for integration testing, allowing control over component interactions.
    
    Args:
        integration_test_config: Test configuration dictionary
        mock_service_registry: Mocked service registry with test components
        
    Returns:
        OrchestratorService: Orchestrator with mocked component services
    """
    # Patch the ServiceRegistry to use our mock
    with patch("services.orchestrator.orchestrator.ServiceRegistry", return_value=mock_service_registry):
        # Create the orchestrator service
        orchestrator = OrchestratorService(config=integration_test_config)
        
        # Configure orchestrator properties
        orchestrator.conversation_history = []
        orchestrator.sql_history = []
        orchestrator.config = integration_test_config
        
        # Ensure the orchestrator is using mocked components
        orchestrator.classifier = mock_service_registry.get("classification")
        orchestrator.sql_generator = mock_service_registry.get("sql_generator")
        orchestrator.executor = mock_service_registry.get("execution")
        orchestrator.response_generator = mock_service_registry.get("response")
        
        return orchestrator


@pytest.fixture
def mock_external_api_client():
    """
    Provide a mock for external API clients (OpenAI, Gemini, etc.).
    
    This fixture creates a general-purpose mock for testing interactions
    with external APIs without making actual API calls.
    
    Returns:
        MagicMock: A configured external API client mock
    """
    client = MagicMock()
    
    # Configure client methods
    client.create = MagicMock()
    client.get = MagicMock()
    client.post = MagicMock()
    client.delete = MagicMock()
    
    # Add async versions
    client.acreate = AsyncMock()
    client.aget = AsyncMock()
    client.apost = AsyncMock()
    client.adelete = AsyncMock()
    
    return client


@pytest.fixture
def template_test_environment(tmp_path):
    """
    Provide a temporary template environment for testing template-based components.
    
    This fixture creates a temporary directory structure with template files
    for testing template loading and rendering functionality.
    
    Args:
        tmp_path: Pytest temporary path fixture
        
    Returns:
        Dict[str, Any]: Dictionary with template environment information
    """
    # Create template directories
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Create subdirectories
    sql_dir = templates_dir / "sql"
    sql_dir.mkdir()
    response_dir = templates_dir / "response"
    response_dir.mkdir()
    classifier_dir = templates_dir / "classification"
    classifier_dir.mkdir()
    
    # Create template files
    classification_template = classifier_dir / "classify.prompt"
    classification_template.write_text("""
    <system>
    You are a classifier that categorizes restaurant queries into these types:
    - menu_inquiry: Questions about the menu items, prices, or categories
    - order_history: Questions about past orders and order details
    - general_question: Any general questions not related to menu or orders
    </system>
    
    <user>
    Classify the following query:
    {{query}}
    </user>
    """)
    
    sql_template = sql_dir / "generate.prompt"
    sql_template.write_text("""
    <system>
    You are an SQL generator for a restaurant database with these tables:
    - menu_items (id, name, price, category)
    - orders (id, customer_id, date, total)
    </system>
    
    <user>
    Generate SQL for the following query:
    {{query}}
    </user>
    """)
    
    response_template = response_dir / "generate.prompt"
    response_template.write_text("""
    <system>
    You are a helpful assistant for a restaurant.
    </system>
    
    <user>
    Query: {{query}}
    
    SQL Results:
    {{results}}
    
    Generate a natural language response to the query based on the SQL results.
    </user>
    """)
    
    return {
        "templates_dir": templates_dir,
        "template_files": {
            "classification": classification_template,
            "sql": sql_template,
            "response": response_template
        }
    }


@pytest.fixture
def mock_db_pool():
    """
    Provide a mocked database connection pool for integration tests.
    
    This fixture creates a mock that simulates a database connection pool
    with methods for acquiring and releasing connections.
    
    Returns:
        MagicMock: A configured database connection pool mock
    """
    pool = MagicMock()
    connection = MagicMock()
    
    # Configure the connection
    connection.execute = AsyncMock()
    connection.fetch_all = AsyncMock(return_value=[{"id": 1, "name": "Test Item", "price": 9.99}])
    connection.fetch_one = AsyncMock(return_value={"count": 5})
    connection.close = AsyncMock()
    
    # Configure the pool
    pool.acquire = AsyncMock(return_value=connection)
    pool.release = AsyncMock()
    pool.close = AsyncMock()
    pool.wait_closed = AsyncMock()
    
    # Add performance metrics
    pool.size = 5
    pool.freesize = 3
    pool.minsize = 1
    pool.maxsize = 10
    
    return pool 