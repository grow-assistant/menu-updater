"""
Fixtures for unit tests.

This module contains fixtures that are specifically designed for unit tests,
focusing on isolated component testing with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from typing import Dict, Any, List
import pandas as pd

# Import the components that need to be mocked
from services.classification.classifier import ClassificationService
from services.response.response_generator import ResponseGenerator
from services.rules.rules_service import RulesService
from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
from services.execution.sql_executor import SQLExecutor
import services.execution.result_formatter as result_formatter
from config.settings_compat import Settings
from services.orchestrator.orchestrator import OrchestratorService


@pytest.fixture
def unit_test_config() -> Dict[str, Any]:
    """
    Provide a standardized configuration dictionary for unit tests.
    
    This fixture creates a complete configuration dictionary with all necessary
    sections for testing components in isolation.
    
    Returns:
        Dict[str, Any]: Configuration dictionary with test values
    """
    return {
        "default_location_id": 62,
        "default_location_name": "Test Restaurant",
        "max_tokens": 100,
        "temperature": 0.7,
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
def mock_openai_response():
    """
    Provide a standard mocked OpenAI API response.
    
    This fixture creates a mock that simulates an OpenAI API response
    with customizable content.
    
    Returns:
        MagicMock: A mock OpenAI response with a configurable choices attribute
    """
    class MockMessage:
        def __init__(self, content="Test response"):
            self.content = content
            
    class MockChoice:
        def __init__(self, content="Test response"):
            self.message = MockMessage(content)
            
    class MockCompletion:
        def __init__(self, content="Test response"):
            self.choices = [MockChoice(content)]
            
    return MockCompletion


@pytest.fixture
def mock_db_connection():
    """
    Provide a mocked database connection for unit tests.
    
    This fixture creates a mock that simulates database connection methods
    like execute, fetchall, etc.
    
    Returns:
        MagicMock: A configured database connection mock
    """
    connection = MagicMock()
    cursor = MagicMock()
    
    # Configure the cursor mock
    cursor.execute = MagicMock()
    cursor.fetchall.return_value = [{"id": 1, "name": "Test Item", "price": 9.99}]
    cursor.fetchone.return_value = {"count": 5}
    
    # Configure the connection mock
    connection.cursor.return_value = cursor
    connection.commit = MagicMock()
    connection.rollback = MagicMock()
    connection.close = MagicMock()
    
    # Add async versions
    connection.execute = AsyncMock()
    connection.fetch_all = AsyncMock(return_value=[{"id": 1, "name": "Test Item", "price": 9.99}])
    connection.fetch_one = AsyncMock(return_value={"count": 5})
    
    return connection


@pytest.fixture
def mock_rules_service():
    """
    Provide a mocked RulesService for unit tests.
    
    This fixture creates a mock that simulates RulesService methods,
    particularly for SQL validation and rule retrieval.
    
    Returns:
        MagicMock: A configured RulesService mock
    """
    service = MagicMock(spec=RulesService)
    
    # Mock rules data
    test_rules = {
        "sql_examples": [
            "SELECT * FROM menu_items WHERE category = 'Appetizers'",
            "SELECT * FROM orders WHERE date > '2023-01-01'"
        ],
        "response_rules": {
            "format": "table",
            "max_items": 10
        }
    }
    
    test_patterns = {
        "rules": {"max_rows": 100},
        "schema": {
            "menu_items": {
                "columns": ["id", "name", "price", "category"]
            },
            "orders": {
                "columns": ["id", "customer_id", "date", "total"]
            }
        },
        "patterns": {
            "get_menu_items": "SELECT * FROM menu_items",
            "get_item_by_id": "SELECT * FROM menu_items WHERE id = {id}"
        }
    }
    
    # Configure methods
    service.get_rules_and_examples.return_value = test_rules
    service.get_sql_patterns.return_value = test_patterns
    service.get_schema_for_type.return_value = test_patterns["schema"]
    service.get_sql_pattern.return_value = "SELECT * FROM menu_items WHERE id = {id}"
    service.check_table_operation_allowed.return_value = True
    service.check_query_allowed.return_value = True
    service.format_rules_for_prompt.return_value = "RULES:\n1. Use proper SQL formatting\n2. Capitalize SQL keywords"
    service.health_check.return_value = True
    
    return service


@pytest.fixture
def mock_classifier():
    """
    Provide a mocked ClassificationService for unit tests.
    
    This fixture creates a mock that simulates ClassificationService methods
    for query classification.
    
    Returns:
        MagicMock: A configured ClassificationService mock
    """
    classifier = MagicMock(spec=ClassificationService)
    
    # Configure methods
    menu_result = {
        "category": "menu_inquiry",
        "confidence": 0.9,
        "query_type": "menu_inquiry",
        "skip_database": False
    }
    
    general_result = {
        "category": "general_question",
        "confidence": 0.8,
        "query_type": "general_question",
        "skip_database": True
    }
    
    classifier.classify.return_value = menu_result
    classifier.classify_query.return_value = menu_result
    classifier.classify_query_async = AsyncMock(return_value=menu_result)
    
    # Make classify method handle different inputs
    def classify_side_effect(query):
        if "menu" in query.lower():
            return menu_result
        else:
            return general_result
            
    classifier.classify.side_effect = classify_side_effect
    
    return classifier


@pytest.fixture
def mock_sql_generator():
    """
    Provide a mocked GeminiSQLGenerator for unit tests.
    
    This fixture creates a mock that simulates GeminiSQLGenerator methods
    for generating SQL from natural language queries.
    
    Returns:
        MagicMock: A configured GeminiSQLGenerator mock
    """
    generator = MagicMock(spec=GeminiSQLGenerator)
    
    # Sample SQL responses
    menu_sql = "SELECT * FROM menu_items WHERE category = 'Entrees'"
    order_sql = "SELECT * FROM orders WHERE customer_id = 123 ORDER BY date DESC LIMIT 5"
    
    # Configure methods to match the actual GeminiSQLGenerator API
    generator.generate.return_value = {
        "success": True,
        "query": menu_sql,
        "query_time": 0.5,
        "model": "gemini-2.0-flash",
        "attempts": 1,
        "query_type": "SELECT"
    }
    
    generator.generate_sql.return_value = {
        "success": True,
        "query": menu_sql,
        "query_time": 0.5,
        "model": "gemini-2.0-flash",
        "attempts": 1,
        "query_type": "SELECT"
    }
    
    generator.health_check.return_value = True
    
    # Make generate method handle different inputs with the correct parameter structure
    def generate_side_effect(query, category, rules_and_examples, additional_context=None):
        if "menu" in query.lower():
            return {
                "success": True,
                "query": menu_sql,
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
        elif "order" in query.lower():
            return {
                "success": True,
                "query": order_sql,
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
        else:
            return {
                "success": True,
                "query": "SELECT 'No relevant SQL for this query'",
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
            
    generator.generate.side_effect = generate_side_effect
    
    # Make generate_sql method handle different inputs with the correct parameter structure
    def generate_sql_side_effect(query, examples, context):
        if "menu" in query.lower():
            return {
                "success": True,
                "query": menu_sql,
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
        elif "order" in query.lower():
            return {
                "success": True,
                "query": order_sql,
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
        else:
            return {
                "success": True,
                "query": "SELECT 'No relevant SQL for this query'",
                "query_time": 0.5,
                "model": "gemini-2.0-flash",
                "attempts": 1,
                "query_type": "SELECT"
            }
            
    generator.generate_sql.side_effect = generate_sql_side_effect
    
    return generator


@pytest.fixture
def mock_sql_executor():
    """
    Provide a mocked SQLExecutor for unit tests.
    
    This fixture creates a mock that simulates SQLExecutor methods
    for executing SQL queries against a database.
    
    Returns:
        MagicMock: A configured SQLExecutor mock
    """
    executor = MagicMock(spec=SQLExecutor)
    
    # Sample query results
    menu_results = [
        {"id": 1, "name": "Burger", "price": 12.99, "category": "Entrees"},
        {"id": 2, "name": "Pizza", "price": 14.99, "category": "Entrees"},
        {"id": 3, "name": "Salad", "price": 8.99, "category": "Starters"}
    ]
    
    order_results = [
        {"id": 101, "customer_id": 123, "date": "2023-05-15", "total": 45.67},
        {"id": 102, "customer_id": 123, "date": "2023-06-20", "total": 32.50}
    ]
    
    empty_results = []
    
    # Configure methods
    executor.execute_query = AsyncMock(return_value={
        "results": menu_results,
        "query_time": 0.1,
        "row_count": len(menu_results)
    })
    
    executor.execute_update = AsyncMock(return_value={
        "success": True,
        "message": "Updated 1 row",
        "query_time": 0.1,
        "row_count": 1
    })
    
    executor.health_check.return_value = True
    
    # Make execute_query method handle different inputs
    async def execute_query_side_effect(query, *args, **kwargs):
        if "menu_items" in query.lower():
            return {
                "results": menu_results,
                "query_time": 0.1,
                "row_count": len(menu_results)
            }
        elif "orders" in query.lower():
            return {
                "results": order_results,
                "query_time": 0.1,
                "row_count": len(order_results)
            }
        else:
            return {
                "results": empty_results,
                "query_time": 0.1,
                "row_count": 0
            }
            
    executor.execute_query.side_effect = execute_query_side_effect
    
    return executor


@pytest.fixture
def mock_result_formatter():
    """
    Provide a mocked result_formatter module for unit tests.
    
    This fixture creates a mock that simulates result_formatter functions
    for formatting query results into different formats (JSON, CSV, etc.).
    
    Returns:
        MagicMock: A configured mock object with result formatter functions
    """
    formatter = MagicMock()
    
    # Sample formatted results
    json_result = '{"results":[{"id":1,"name":"Burger","price":12.99}]}'
    csv_result = "id,name,price\n1,Burger,12.99"
    text_table_result = "+----+--------+-------+\n| id | name   | price |\n+----+--------+-------+\n| 1  | Burger | 12.99 |\n+----+--------+-------+"
    
    # Mock the module functions
    formatter.format_to_json = MagicMock(return_value=json_result)
    formatter.format_to_csv = MagicMock(return_value=csv_result)
    formatter.format_to_text_table = MagicMock(return_value=text_table_result)
    formatter.format_result = MagicMock(return_value={
        "formatted": text_table_result,
        "format": "text_table"
    })
    
    return formatter


@pytest.fixture
def mock_response_generator():
    """
    Provide a mocked ResponseGenerator for unit tests.
    
    This fixture creates a mock that simulates ResponseGenerator methods
    for generating natural language responses from query results.
    
    Returns:
        MagicMock: A configured ResponseGenerator mock
    """
    generator = MagicMock(spec=ResponseGenerator)
    
    # Sample responses
    menu_response = "The menu includes Burger ($12.99), Pizza ($14.99), and Salad ($8.99)."
    order_response = "You have 2 recent orders: one on May 15, 2023 for $45.67 and another on June 20, 2023 for $32.50."
    empty_response = "I couldn't find any information matching your query."
    
    # Configure methods
    generator.generate.return_value = {
        "response": menu_response,
        "time_elapsed": 0.5,
        "metadata": {"query_type": "menu_inquiry"},
        "query": "What's on the menu?"
    }
    
    generator.generate_async = AsyncMock(return_value={
        "response": menu_response,
        "time_elapsed": 0.5,
        "metadata": {"query_type": "menu_inquiry"},
        "query": "What's on the menu?"
    })
    
    generator.health_check.return_value = True
    
    # Make generate method handle different inputs
    def generate_side_effect(query, results=None, **kwargs):
        if not results or len(results) == 0:
            return {
                "response": empty_response,
                "time_elapsed": 0.5,
                "metadata": {"query_type": "unknown"},
                "query": query
            }
        
        if "menu" in query.lower():
            return {
                "response": menu_response,
                "time_elapsed": 0.5,
                "metadata": {"query_type": "menu_inquiry"},
                "query": query
            }
        elif "order" in query.lower():
            return {
                "response": order_response,
                "time_elapsed": 0.5,
                "metadata": {"query_type": "order_history"},
                "query": query
            }
        else:
            return {
                "response": f"Here's what I found: {len(results)} results.",
                "time_elapsed": 0.5,
                "metadata": {"query_type": "general"},
                "query": query
            }
            
    generator.generate.side_effect = generate_side_effect
    
    return generator 