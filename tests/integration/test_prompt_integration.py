"""
Integration tests for the template-based prompt system.

This module tests the integration between all services using the
new template-based prompt system.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from services.classification.classifier import ClassificationService
from services.classification.prompt_builder import ClassificationPromptBuilder
from services.sql_generator.prompt_builder import SQLPromptBuilder
from services.sql_generator.sql_generator import SQLGenerator
from services.response.response_generator import ResponseGenerator
from services.response.prompt_builder import ResponsePromptBuilder
from services.rules.rules_manager import RulesManager
from services.utils.prompt_loader import PromptLoader
from services.orchestrator.orchestrator import Orchestrator
from services.execution.sql_execution_layer import SQLExecutionLayer


class TestPromptIntegration:
    """Test the integration of all services with the template-based prompt system."""
    
    @pytest.fixture
    def test_config(self):
        """Provide a test configuration."""
        return {
            "default_location_id": 62,
            "default_location_name": "Test Restaurant",
            "test_mode": True,
            "api": {
                "gemini": {
                    "api_key": "test_gemini_key",
                    "model": "gemini-pro"
                },
                "openai": {
                    "api_key": "test_openai_key",
                    "model": "gpt-4"
                }
            },
            "services": {
                "rules": {
                    "rules_path": "services/rules/query_rules",
                    "resources_dir": "resources",
                    "cache_ttl": 60
                },
                "sql_generator": {
                    "examples_path": "resources/sql_examples"
                },
                "execution": {
                    "max_rows": 1000,
                    "timeout": 10,
                    "retry_count": 1
                },
                "response": {
                    "max_tokens": 300,
                    "temperature": 0.5
                }
            }
        }
    
    @pytest.fixture
    def mock_prompt_loader(self):
        """Create a mock PromptLoader that returns test templates."""
        mock_loader = MagicMock(spec=PromptLoader)
        
        # Mock template loading
        mock_loader.load_template.return_value = "Test template for {query_type}"
        mock_loader.format_template.return_value = "Formatted template for testing"
        
        return mock_loader
    
    @pytest.fixture
    def mock_classification_service(self, mock_prompt_loader, test_config):
        """Create a mock ClassificationService with the template-based prompt builder."""
        with patch('services.utils.prompt_loader.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = ClassificationService(config=test_config)
            
            # Mock classification methods
            service.classify_query = MagicMock(return_value="menu_query")
            service.classify_query_async = MagicMock(return_value="menu_query")
            
            return service
    
    @pytest.fixture
    def mock_sql_generator(self, mock_prompt_loader):
        """Create a mock SQLGenerator with the template-based prompt builder."""
        with patch('services.utils.prompt_loader.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = SQLGenerator(max_tokens=100, temperature=0.5)
            
            # Mock the generate_sql method to return test data
            service.generate_sql = MagicMock(return_value={
                "sql": "SELECT * FROM menu_items",
                "success": True,
                "query_type": "query_menu"
            })
            
            return service
    
    @pytest.fixture
    def mock_response_generator(self, mock_prompt_loader, test_config):
        """Create a mock ResponseGenerator with the template-based prompt builder."""
        with patch('services.utils.prompt_loader.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = ResponseGenerator(config=test_config)
            
            # Mock response methods
            service.generate_response = MagicMock(return_value="Test response")
            service.generate_summary = MagicMock(return_value="Test summary")
            
            return service
    
    @pytest.fixture
    def mock_execution_service(self):
        """Create a mock SQLExecutionLayer."""
        service = MagicMock(spec=SQLExecutionLayer)
        
        # Mock the execute_sql method to return test data
        async def mock_execute_sql(*args, **kwargs):
            return {
                "success": True,
                "data": [
                    {"id": 1, "name": "Test Item 1", "price": 9.99},
                    {"id": 2, "name": "Test Item 2", "price": 14.99}
                ],
                "row_count": 2,
                "execution_time": 0.1
            }
        
        service.execute_sql = mock_execute_sql
        
        return service
    
    @pytest.fixture
    def mock_orchestrator(self, mock_classification_service, mock_sql_generator, 
                         mock_response_generator, mock_execution_service, test_config):
        """Create a mock Orchestrator with all template-based services."""
        # Patch the ServiceRegistry to avoid initializing real services
        with patch('services.utils.service_registry.ServiceRegistry.get_service') as mock_get_service:
            # Configure the mock to return our test services
            def get_service_side_effect(service_name):
                if service_name == "classification":
                    return mock_classification_service
                elif service_name == "sql_generator":
                    return mock_sql_generator
                elif service_name == "response":
                    return mock_response_generator
                elif service_name == "execution":
                    return mock_execution_service
                else:
                    return MagicMock()
            
            mock_get_service.side_effect = get_service_side_effect
            
            # Create the orchestrator with our test config
            orchestrator = Orchestrator(config=test_config)
            
            # Manually set our mocked services to ensure they're used
            orchestrator.classifier = mock_classification_service
            orchestrator.sql_generator = mock_sql_generator
            orchestrator.response_generator = mock_response_generator
            orchestrator.execution_layer = mock_execution_service
            
            return orchestrator
    
    def test_integration_query_menu(self, mock_orchestrator):
        """Test the integrated flow for a menu query."""
        # Configure mocks for the expected call chain
        mock_orchestrator.classifier.classify_query.return_value = "menu_query"
        mock_orchestrator.sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM menu_items",
            "success": True,
            "query_type": "menu_query"
        }
        
        # Mock execute_sql to return a list of menu items
        async def mock_execute_sql(*args, **kwargs):
            return {
                "success": True,
                "data": [
                    {"id": 1, "name": "Test Item 1", "price": 9.99},
                    {"id": 2, "name": "Test Item 2", "price": 14.99}
                ],
                "row_count": 2,
                "execution_time": 0.1
            }
        
        mock_orchestrator.execution_layer.execute_sql = mock_execute_sql
        mock_orchestrator.response_generator.generate_response.return_value = "Here are the menu items."
        
        # Run the integrated flow
        result = mock_orchestrator.process_query("Show me the menu")
        
        # Assert that all services were called in sequence
        mock_orchestrator.classifier.classify_query.assert_called_once()
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        # We don't assert on execute_sql since it's an async method and would need to be awaited
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Check the result
        assert "Here are the menu items." in result
    
    def test_integration_menu_update(self, mock_orchestrator):
        """Test the integrated flow for a menu update query."""
        # Configure mocks for the expected call chain
        mock_orchestrator.classifier.classify_query.return_value = "menu_update"
        mock_orchestrator.sql_generator.generate_sql.return_value = {
            "sql": "UPDATE menu_items SET price = 12.99 WHERE id = 1",
            "success": True,
            "query_type": "menu_update"
        }
        
        # Mock execute_sql to return a successful update result
        async def mock_execute_sql(*args, **kwargs):
            return {
                "success": True,
                "data": [],
                "row_count": 1,
                "execution_time": 0.1
            }
        
        mock_orchestrator.execution_layer.execute_sql = mock_execute_sql
        mock_orchestrator.response_generator.generate_response.return_value = "Menu item has been updated."
        
        # Run the integrated flow
        result = mock_orchestrator.process_query("Update the burger price to $12.99")
        
        # Assert that all services were called in sequence
        mock_orchestrator.classifier.classify_query.assert_called_once()
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        # We don't assert on execute_sql since it's an async method and would need to be awaited
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Check the result
        assert "Menu item has been updated." in result
    
    def test_integration_general_question(self, mock_orchestrator):
        """Test the integrated flow for a general question."""
        # Configure mocks for the expected call chain
        mock_orchestrator.classifier.classify_query.return_value = "general_question"
        
        # For general questions, SQL generation and execution are skipped
        mock_orchestrator.response_generator.generate_response.return_value = "Our restaurant opens at 9 AM."
        
        # Run the integrated flow
        result = mock_orchestrator.process_query("What time do you open?")
        
        # Assert that only relevant services were called
        mock_orchestrator.classifier.classify_query.assert_called_once()
        mock_orchestrator.sql_generator.generate_sql.assert_not_called()
        # We don't assert on execute_sql since it's an async method
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Check the result
        assert "Our restaurant opens at 9 AM." in result
    
    def test_prompt_builder_unit_integration(self):
        """Test the integration between prompt builders and the template system."""
        # Create a test PromptLoader that simulates template loading
        with patch('services.utils.prompt_loader.get_prompt_loader') as mock_get_loader:
            # Create a mock loader that returns predefined templates
            mock_loader = MagicMock(spec=PromptLoader)
            
            # Configure the mock loader to return different templates based on the name
            def mock_load_template(name):
                templates = {
                    "classification/query_classification.txt": "Classify this query: {query}",
                    "sql/menu_query.txt": "Generate SQL for menu query: {query}",
                    "response/menu_response.txt": "Generate response for menu data: {data}"
                }
                return templates.get(name, f"Template for {name}")
            
            mock_loader.load_template.side_effect = mock_load_template
            mock_loader.format_template.side_effect = lambda name, **kwargs: mock_load_template(name).format(**kwargs)
            mock_get_loader.return_value = mock_loader
            
            # Test Classification Prompt Builder
            classification_builder = ClassificationPromptBuilder()
            classification_prompt = classification_builder.build_query_classification_prompt("Show me the menu")
            assert "Classify this query: Show me the menu" in classification_prompt
            
            # Test SQL Prompt Builder
            sql_builder = SQLPromptBuilder()
            sql_prompt = sql_builder.build_sql_prompt("menu_query", {"query": "Show me the menu"})
            assert "Generate SQL for menu query: Show me the menu" in sql_prompt["prompt"]
            
            # Test Response Prompt Builder
            response_builder = ResponsePromptBuilder()
            response_prompt = response_builder.build_response_prompt(
                query="Show me the menu",
                query_type="menu_query",
                sql_result={"data": [{"name": "Burger", "price": 9.99}]},
                additional_context={}
            )
            assert "Generate response for menu data:" in response_prompt 