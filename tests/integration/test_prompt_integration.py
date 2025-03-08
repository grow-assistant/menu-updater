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


class TestPromptIntegration:
    """Test the integration of all services with the template-based prompt system."""
    
    @pytest.fixture
    def mock_prompt_loader(self):
        """Create a mock PromptLoader that returns test templates."""
        mock_loader = MagicMock(spec=PromptLoader)
        
        # Mock template loading
        mock_loader.load_template.return_value = "Test template for {query_type}"
        mock_loader.format_template.return_value = "Formatted template for testing"
        
        return mock_loader
    
    @pytest.fixture
    def mock_classification_service(self, mock_prompt_loader):
        """Create a mock ClassificationService with the template-based prompt builder."""
        with patch('services.classification.prompt_builder.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = ClassificationService(config={"test_mode": True})
            
            # Mock the classify_query method to return test data
            service.classify_query = MagicMock(return_value={
                "request_type": "query_menu",
                "query": "Show me all menu items"
            })
            
            return service
    
    @pytest.fixture
    def mock_sql_generator(self, mock_prompt_loader):
        """Create a mock SQLGenerator with the template-based prompt builder."""
        with patch('services.sql_generator.prompt_builder.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = SQLGenerator()
            
            # Mock the generate_sql method to return test data
            service.generate_sql = MagicMock(return_value={
                "sql": "SELECT * FROM menu_items",
                "success": True,
                "query_type": "query_menu"
            })
            
            return service
    
    @pytest.fixture
    def mock_response_generator(self, mock_prompt_loader):
        """Create a mock ResponseGenerator with the template-based prompt builder."""
        with patch('services.response.prompt_builder.get_prompt_loader', 
                   return_value=mock_prompt_loader):
            service = ResponseGenerator(config={"test_mode": True})
            
            # Mock the generate_response method to return test data
            service.generate_response = MagicMock(return_value={
                "response": "Here are the menu items you requested.",
                "success": True
            })
            
            return service
    
    @pytest.fixture
    def mock_execution_service(self):
        """Create a mock execution service."""
        mock_service = MagicMock()
        mock_service.execute_query.return_value = [
            {"id": 1, "name": "Burger", "price": 10.99},
            {"id": 2, "name": "Pizza", "price": 12.99}
        ]
        mock_service.get_columns.return_value = ["id", "name", "price"]
        return mock_service
    
    @pytest.fixture
    def mock_orchestrator(self, mock_classification_service, mock_sql_generator, 
                         mock_response_generator, mock_execution_service):
        """Create a mock Orchestrator with all template-based services."""
        orchestrator = Orchestrator()
        orchestrator.classifier = mock_classification_service
        orchestrator.sql_generator = mock_sql_generator
        orchestrator.response_generator = mock_response_generator
        orchestrator.execution_service = mock_execution_service
        
        # Mock the OpenAI and Gemini clients
        orchestrator.openai_client = MagicMock()
        orchestrator.gemini_client = MagicMock()
        
        return orchestrator
    
    def test_integration_query_menu(self, mock_orchestrator):
        """Test processing a menu query with the template-based system."""
        # Test with a menu query
        result = mock_orchestrator.process_query("Show me all menu items")
        
        # Verify that all services were called with the right parameters
        mock_orchestrator.classifier.classify_query.assert_called_once()
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        mock_orchestrator.execution_service.execute_query.assert_called_once()
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Verify the response structure
        assert "response" in result
        assert result["query_type"] == "query_menu"
        assert "sql_query" in result
        assert "sql_result" in result
    
    def test_integration_menu_update(self, mock_orchestrator):
        """Test processing a menu update query with the template-based system."""
        # Configure mocks for menu update
        mock_orchestrator.classifier.classify_query.return_value = {
            "request_type": "update_price",
            "item_name": "Burger",
            "new_price": 11.99
        }
        
        # Test with a price update query
        result = mock_orchestrator.process_query("Change the price of Burger to $11.99")
        
        # Verify that all services were called with the right parameters
        mock_orchestrator.classifier.classify_query.assert_called_once()
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        mock_orchestrator.execution_service.execute_query.assert_called_once()
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Verify the response structure
        assert "response" in result
        assert result["query_type"] == "update_price"
        assert "sql_query" in result
        assert "sql_result" in result
    
    def test_integration_general_question(self, mock_orchestrator):
        """Test processing a general question with the template-based system."""
        # Configure mocks for general question
        mock_orchestrator.classifier.classify_query.return_value = {
            "request_type": "general_question",
            "query": "What are the busiest times for restaurants?"
        }
        
        # Test with a general question
        result = mock_orchestrator.process_query("What are the busiest times for restaurants?")
        
        # Verify the response structure
        assert "response" in result
        assert result["query_type"] == "general_question"
        assert result["sql_query"] is None
        assert result["sql_result"] is None
        
        # Verify the response generator was called with the right parameters
        mock_orchestrator.response_generator.generate_response.assert_called_once_with(
            query="What are the busiest times for restaurants?",
            query_type="general_question",
            sql_result={"sql": "", "result": {"rows": [], "columns": []}},
            additional_context={
                "location_name": mock_orchestrator.current_location_name,
                "conversation_history": []
            }
        )
    
    def test_prompt_builder_unit_integration(self):
        """Test the integration between prompt builders and loaders."""
        # Create real instances for this test
        with patch('services.utils.prompt_loader.Path.exists', return_value=True), \
             patch('services.utils.prompt_loader.Path.is_file', return_value=True), \
             patch('builtins.open', create=True), \
             patch('services.utils.prompt_loader.open', create=True) as mock_open:
            
            # Mock the file reading
            mock_open().__enter__().read.return_value = "Template for {query_type} with {example}"
            
            # Create the prompt loader
            prompt_loader = PromptLoader()
            
            # Test classification prompt builder
            classification_builder = ClassificationPromptBuilder()
            classification_builder.prompt_loader = prompt_loader
            
            # Test SQL prompt builder
            sql_builder = SQLPromptBuilder()
            sql_builder.prompt_loader = prompt_loader
            
            # Test response prompt builder
            response_builder = ResponsePromptBuilder()
            response_builder.prompt_loader = prompt_loader
            
            # These won't execute the real logic since we've mocked the file operations,
            # but they'll test the integration between the components
            classification_prompt = classification_builder.build_classification_prompt("Test query")
            sql_prompt = sql_builder.build_sql_prompt("query_menu", {"query": "Test query"})
            response_prompt = response_builder.build_response_prompt(
                "Test query", 
                "query_menu", 
                {"sql": "SELECT * FROM menu_items", "result": {"rows": [], "columns": []}}
            )
            
            # Verify the structure of the returned prompts
            assert "system" in classification_prompt
            assert "user" in classification_prompt
            
            assert "system" in sql_prompt
            assert "user" in sql_prompt
            
            assert "system" in response_prompt
            assert "user" in response_prompt 