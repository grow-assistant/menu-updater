"""
Integration Tests for Template-Based Prompt System

This module tests the complete template-based prompt system, including:
- Template loading and caching
- Prompt building
- Integration with services
- End-to-end flows
"""

import pytest
import os
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from services.utils.prompt_loader import PromptLoader, get_prompt_loader
from services.classification.prompt_builder import ClassificationPromptBuilder
from services.classification.classifier import ClassificationService
from services.sql_generator.prompt_builder import SQLPromptBuilder
from services.response.prompt_builder import ResponsePromptBuilder
from services.response.response_generator import ResponseGenerator

from orchestrator.orchestrator import Orchestrator


class TestTemplateSystem:
    """Integration tests for the template-based prompt system."""
    
    @pytest.fixture
    def temp_templates_dir(self, tmp_path):
        """Create a temporary directory for test templates."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        # Create test templates
        (templates_dir / "test_template.txt").write_text("This is a ${test_var} template with ${another_var}.")
        
        # Create subdirectories
        classification_dir = templates_dir / "classification"
        classification_dir.mkdir()
        (classification_dir / "test_classification.txt").write_text("Classification template with ${query_type}.")
        
        sql_dir = templates_dir / "sql"
        sql_dir.mkdir()
        (sql_dir / "test_sql.txt").write_text("SQL template with ${schema}.")
        
        response_dir = templates_dir / "response"
        response_dir.mkdir()
        (response_dir / "test_response.txt").write_text("Response template with ${result_format}.")
        
        return templates_dir
    
    @pytest.fixture
    def prompt_loader(self, temp_templates_dir):
        """Create a PromptLoader with the test templates directory."""
        return PromptLoader(template_dir=str(temp_templates_dir))
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = MagicMock()
        
        # Mock chat completions
        chat_completions = MagicMock()
        completion = MagicMock()
        message = MagicMock()
        message.content = "This is a test response from OpenAI."
        completion.choices = [MagicMock(message=message)]
        chat_completions.create.return_value = completion
        client.chat.completions = chat_completions
        
        return client
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Create a mock Gemini client."""
        client = MagicMock()
        
        # Mock completions
        client.generate_content.return_value = MagicMock(
            text="This is a test response from Gemini."
        )
        
        return client
    
    def test_prompt_loader_initialization(self, prompt_loader, temp_templates_dir):
        """Test initialization of the PromptLoader with a custom directory."""
        assert prompt_loader.template_dir == str(temp_templates_dir)
        assert prompt_loader.templates == {}
        assert prompt_loader.cache_hits == 0
        assert prompt_loader.cache_misses == 0
    
    def test_load_template(self, prompt_loader):
        """Test loading a template from file."""
        template = prompt_loader.load_template("test_template")
        
        assert template == "This is a ${test_var} template with ${another_var}."
        assert prompt_loader.cache_misses == 1
        assert prompt_loader.cache_hits == 0
        
        # Load again - should be from cache
        template = prompt_loader.load_template("test_template")
        assert prompt_loader.cache_misses == 1
        assert prompt_loader.cache_hits == 1
    
    def test_format_template(self, prompt_loader):
        """Test formatting a template with variables."""
        formatted = prompt_loader.format_template("test_template", test_var="formatted", another_var="example")
        
        assert formatted == "This is a formatted template with example."
        
        # With missing variable
        formatted = prompt_loader.format_template("test_template", test_var="formatted")
        assert formatted == "This is a formatted template with ${another_var}."
    
    def test_load_template_from_subdirectory(self, prompt_loader):
        """Test loading a template from a subdirectory."""
        template = prompt_loader.load_template("classification/test_classification")
        
        assert template == "Classification template with ${query_type}."
        assert prompt_loader.cache_misses == 1
        assert prompt_loader.cache_hits == 0
    
    def test_get_cache_stats(self, prompt_loader):
        """Test getting cache statistics."""
        # Load a few templates
        prompt_loader.load_template("test_template")
        prompt_loader.load_template("classification/test_classification")
        prompt_loader.load_template("test_template")  # Cache hit
        
        stats = prompt_loader.get_cache_stats()
        
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["hit_ratio"] == 1/3
        assert stats["templates_cached"] == 2
        assert "load_times" in stats
    
    def test_classification_prompt_builder(self, prompt_loader):
        """Test the ClassificationPromptBuilder with the template system."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            with patch('services.classification.prompt_builder.get_prompt_loader', return_value=prompt_loader):
                builder = ClassificationPromptBuilder()
                builder.prompt_loader = prompt_loader
                
                # Mock the load_template method to use our test template
                original_load = prompt_loader.load_template
                prompt_loader.load_template = lambda name: "Classification template with ${query_type}." if "classification" in name else original_load(name)
                
                prompts = builder.build_classification_prompt("Show me the menu")
                
                assert "system" in prompts
                assert "user" in prompts
                assert "${query_type}" not in prompts["system"]  # Variables should be replaced
    
    def test_sql_prompt_builder(self, prompt_loader):
        """Test the SQLPromptBuilder with the template system."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            with patch('services.sql_generator.prompt_builder.get_prompt_loader', return_value=prompt_loader):
                builder = SQLPromptBuilder()
                builder.prompt_loader = prompt_loader
                
                # Mock the load_template method to use our test template
                original_load = prompt_loader.load_template
                prompt_loader.load_template = lambda name: "SQL template with ${schema}." if "sql" in name else original_load(name)
                
                prompts = builder.build_sql_prompt("query_menu", {"query": "Show me the menu"})
                
                assert "system" in prompts
                assert "user" in prompts
                assert "${schema}" not in prompts["system"]  # Variables should be replaced
    
    def test_response_prompt_builder(self, prompt_loader):
        """Test the ResponsePromptBuilder with the template system."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            with patch('services.response.prompt_builder.get_prompt_loader', return_value=prompt_loader):
                builder = ResponsePromptBuilder()
                builder.prompt_loader = prompt_loader
                
                # Mock the load_template method to use our test template
                original_load = prompt_loader.load_template
                prompt_loader.load_template = lambda name: "Response template with ${result_format}." if "response" in name else original_load(name)
                
                sql_result = {
                    "sql": "SELECT * FROM menu_items",
                    "result": {"rows": [], "columns": []}
                }
                
                prompts = builder.build_response_prompt("Show me the menu", "query_menu", sql_result)
                
                assert "system" in prompts
                assert "user" in prompts
                assert "${result_format}" not in prompts["system"]  # Variables should be replaced
    
    def test_classification_service_with_template(self, prompt_loader, mock_openai_client):
        """Test the ClassificationService using the template-based prompt builder."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            with patch('services.classification.prompt_builder.get_prompt_loader', return_value=prompt_loader):
                # Setup our test environment
                original_load = prompt_loader.load_template
                prompt_loader.load_template = lambda name: "Classification template with ${query_type}." if "classification" in name else original_load(name)
                
                # Mock the OpenAI response
                mock_response = {
                    "request_type": "query_menu",
                    "query": "Show me the menu"
                }
                mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)
                
                # Create the service
                service = ClassificationService(ai_client=mock_openai_client)
                
                # Replace the prompt builder with our mocked one
                service.prompt_builder.prompt_loader = prompt_loader
                
                # Test the classify_query method
                with patch('json.loads', return_value=mock_response):
                    result = service.classify_query("Show me the menu")
                
                assert result["request_type"] == "query_menu"
                
                # Verify that the OpenAI client was called with the formatted prompt
                mock_openai_client.chat.completions.create.assert_called_once()
                call_args = mock_openai_client.chat.completions.create.call_args[1]
                assert "messages" in call_args
                assert len(call_args["messages"]) == 2  # system and user messages
    
    def test_response_service_with_template(self, prompt_loader, mock_openai_client):
        """Test the ResponseGenerator using the template-based prompt builder."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            with patch('services.response.prompt_builder.get_prompt_loader', return_value=prompt_loader):
                # Setup our test environment
                original_load = prompt_loader.load_template
                prompt_loader.load_template = lambda name: "Response template for ${query_type}." if "response" in name else original_load(name)
                
                # Create the service
                service = ResponseGenerator(ai_client=mock_openai_client)
                
                # Replace the prompt builder with our mocked one
                service.prompt_builder = ResponsePromptBuilder()
                service.prompt_builder.prompt_loader = prompt_loader
                
                # Test the generate_response method
                sql_result = {
                    "sql": "SELECT * FROM menu_items",
                    "result": {"rows": [["Burger", 10.99], ["Pizza", 12.99]], "columns": ["name", "price"]}
                }
                
                result = service.generate_response(
                    query="Show me the menu",
                    query_type="query_menu",
                    sql_result=sql_result
                )
                
                assert "response" in result
                assert result["response"] == "This is a test response from OpenAI."
                
                # Verify that the OpenAI client was called with the formatted prompt
                mock_openai_client.chat.completions.create.assert_called_once()
                call_args = mock_openai_client.chat.completions.create.call_args[1]
                assert "messages" in call_args
                assert len(call_args["messages"]) == 2  # system and user messages
    
    def test_end_to_end_template_flow(self, prompt_loader, mock_openai_client, mock_gemini_client):
        """Test the end-to-end flow using the template system with the Orchestrator."""
        with patch('services.utils.prompt_loader.get_prompt_loader', return_value=prompt_loader):
            # Set up our mocked environment
            original_load = prompt_loader.load_template
            
            def mock_load_template(name):
                if "classification" in name:
                    return "Classification template with ${query_type}."
                elif "sql" in name:
                    return "SQL template with ${schema}."
                elif "response" in name:
                    return "Response template for ${query_type}."
                else:
                    return original_load(name)
            
            prompt_loader.load_template = mock_load_template
            
            # Create mocked services
            classification_service = ClassificationService(ai_client=mock_openai_client)
            classification_service.prompt_builder.prompt_loader = prompt_loader
            classification_service.classify_query = MagicMock(return_value={
                "request_type": "query_menu",
                "query": "Show me the menu"
            })
            
            sql_generator = MagicMock()
            sql_generator.generate_sql.return_value = {
                "sql": "SELECT * FROM menu_items",
                "success": True
            }
            
            execution_service = MagicMock()
            execution_service.execute_query.return_value = [
                {"id": 1, "name": "Burger", "price": 10.99},
                {"id": 2, "name": "Pizza", "price": 12.99}
            ]
            execution_service.get_columns.return_value = ["id", "name", "price"]
            
            response_generator = ResponseGenerator(ai_client=mock_openai_client)
            response_generator.prompt_builder = ResponsePromptBuilder()
            response_generator.prompt_builder.prompt_loader = prompt_loader
            
            # Create the orchestrator with our mocked services
            orchestrator = Orchestrator()
            orchestrator.classifier = classification_service
            orchestrator.sql_generator = sql_generator
            orchestrator.execution_service = execution_service
            orchestrator.response_generator = response_generator
            orchestrator.openai_client = mock_openai_client
            orchestrator.gemini_client = mock_gemini_client
            
            # Test the process_query method
            result = orchestrator.process_query("Show me the menu")
            
            # Verify the result
            assert "response" in result
            assert "query_type" in result
            assert result["query_type"] == "query_menu"
            
            # Verify that all services were called
            classification_service.classify_query.assert_called_once()
            sql_generator.generate_sql.assert_called_once()
            execution_service.execute_query.assert_called_once()
            
            # The final response should be generated using the template-based system
            assert len(orchestrator.conversation_history) == 2  # User query and assistant response 