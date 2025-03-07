"""
Unit tests for the updated OrchestratorService with ServiceRegistry.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import time

from services.orchestrator.orchestrator import OrchestratorService
from services.utils.service_registry import ServiceRegistry


class TestUpdatedOrchestratorService:
    """Test class for the updated OrchestratorService."""
    
    def setup_method(self):
        """Setup method that runs before each test."""
        # Reset the ServiceRegistry
        ServiceRegistry._services = {}
        ServiceRegistry._config = None
    
    def test_init(self):
        """Test initializing the OrchestratorService."""
        # Create mock config
        config = {"test": "config"}
        
        # Mock the services and ServiceRegistry
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch.object(OrchestratorService, 'health_check') as mock_health_check:
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Verify ServiceRegistry was initialized and services registered
            mock_registry.initialize.assert_called_once_with(config)
            assert mock_registry.register.call_count == 5  # 5 services should be registered
            mock_health_check.assert_called_once()
    
    def test_health_check(self):
        """Test the health check method."""
        # Create mock config
        config = {"test": "config"}
        
        # Mock ServiceRegistry
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry:
            # Setup mock for check_health
            mock_registry.check_health.return_value = {
                "classification": True,
                "rules": True,
                "sql_generator": False,
                "execution": True,
                "response": True
            }
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call health check
            result = service.health_check()
            
            # Verify result
            assert result == {
                "classification": True,
                "rules": True,
                "sql_generator": False,
                "execution": True,
                "response": True
            }
            mock_registry.check_health.assert_called_once()
    
    def test_process_query_data_query(self):
        """Test processing a data query."""
        # Create mock config and services
        config = {"test": "config"}
        
        # Create mock services
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = "data_query"
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "sql_examples": ["SELECT * FROM menu"],
            "response_rules": {"format": "table"}
        }
        
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate_sql.return_value = "SELECT * FROM menu WHERE price < 10"
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = [{"id": 1, "name": "Burger", "price": 8.99}]
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Here are the menu items under $10"
        
        # Mock ServiceRegistry to return our mock services
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time:
            
            # Setup mock time.time to return consistent values
            mock_time.time.side_effect = [1000, 1005]  # Start time, end time (5 seconds elapsed)
            
            # Setup get_service to return the appropriate mock
            def mock_get_service(service_name):
                if service_name == "classification":
                    return mock_classifier
                elif service_name == "rules":
                    return mock_rules
                elif service_name == "sql_generator":
                    return mock_sql_generator
                elif service_name == "execution":
                    return mock_executor
                elif service_name == "response":
                    return mock_response
            
            mock_registry.get_service.side_effect = mock_get_service
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call process_query
            context = {"session_history": []}
            result = service.process_query("Show me menu items under $10", context)
            
            # Verify service calls
            mock_classifier.classify.assert_called_once_with("Show me menu items under $10", context)
            mock_rules.get_rules_and_examples.assert_called_once_with("data_query")
            mock_sql_generator.generate_sql.assert_called_once_with(
                "Show me menu items under $10", 
                ["SELECT * FROM menu"],
                context
            )
            mock_executor.execute.assert_called_once_with("SELECT * FROM menu WHERE price < 10")
            mock_response.generate.assert_called_once_with(
                "Show me menu items under $10",
                "data_query",
                {"format": "table"},
                [{"id": 1, "name": "Burger", "price": 8.99}],
                context
            )
            
            # Verify result structure
            assert result["response"] == "Here are the menu items under $10"
            assert result["category"] == "data_query"
            assert result["sql_query"] == "SELECT * FROM menu WHERE price < 10"
            assert result["query_results"] == [{"id": 1, "name": "Burger", "price": 8.99}]
            assert result["processing_time"] == 5
            assert result["timestamp"] == 1005
    
    def test_process_query_general_question(self):
        """Test processing a general question that doesn't need SQL."""
        # Create mock config and services
        config = {"test": "config"}
        
        # Create mock services
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = "general"
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "response_rules": {"tone": "friendly"}
        }
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Our restaurant opens at 11 AM daily."
        
        # Mock ServiceRegistry to return our mock services
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time:
            
            # Setup mock time.time to return consistent values
            mock_time.time.side_effect = [1000, 1002]  # Start time, end time (2 seconds elapsed)
            
            # Setup get_service to return the appropriate mock
            def mock_get_service(service_name):
                if service_name == "classification":
                    return mock_classifier
                elif service_name == "rules":
                    return mock_rules
                elif service_name == "response":
                    return mock_response
            
            mock_registry.get_service.side_effect = mock_get_service
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call process_query
            context = {"session_history": []}
            result = service.process_query("What time do you open?", context)
            
            # Verify service calls
            mock_classifier.classify.assert_called_once_with("What time do you open?", context)
            mock_rules.get_rules_and_examples.assert_called_once_with("general")
            mock_response.generate.assert_called_once_with(
                "What time do you open?",
                "general",
                {"tone": "friendly"},
                None,
                context
            )
            
            # Verify result structure
            assert result["response"] == "Our restaurant opens at 11 AM daily."
            assert result["category"] == "general"
            assert result["sql_query"] is None
            assert result["query_results"] is None
            assert result["processing_time"] == 2
            assert result["timestamp"] == 1002
    
    def test_process_query_error_handling(self):
        """Test error handling in process_query."""
        # Create mock config and services
        config = {"test": "config"}
        
        # Create mock classifier that raises an exception
        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = Exception("Classification failed")
        
        # Mock ServiceRegistry to return our mock classifier
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time:
            
            # Setup mock time.time to return consistent values
            mock_time.time.side_effect = [1000, 1001]  # Start time, end time
            
            # Setup get_service to return the mock classifier
            mock_registry.get_service.return_value = mock_classifier
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call process_query
            context = {"session_history": []}
            result = service.process_query("This will fail", context)
            
            # Verify error response
            assert result["response"].startswith("I'm sorry, I encountered an error")
            assert "Classification failed" in result["response"]
            assert result["category"] == "error"
            assert "error" in result
            assert result["timestamp"] == 1001 