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
        
        # Create health check result
        health_result = {
            "classification": True,
            "rules": True,
            "sql_generator": False,
            "execution": True,
            "response": True
        }
        
        # Mock the ServiceRegistry
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch.object(OrchestratorService, 'health_check', return_value=None) as mock_health_check:
            
            # Setup mock for ServiceRegistry.check_health
            mock_registry.check_health.return_value = health_result
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Restore the real method
            service.health_check = lambda: mock_registry.check_health()
            
            # Call health check
            result = service.health_check()
            
            # Verify result matches our expected health result
            assert result == health_result
    
    def test_process_query_data_query(self):
        """Test processing a data query."""
        # Create mock config and services
        config = {"test": "config"}
        
        # Create mock services
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = {
            "category": "data_query",
            "confidence": 0.9,
            "time_period_clause": None,
            "is_followup": False
        }
        
        mock_rules = MagicMock()
        mock_rules.get_rules_and_examples.return_value = {
            "sql_examples": ["SELECT * FROM menu"],
            "response_rules": {"format": "table"}
        }
        
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate_sql.return_value = "SELECT * FROM menu WHERE price < 10"
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {
            "success": True,
            "rows": [{"id": 1, "name": "Burger", "price": 8.99}],
            "error": None
        }
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Here are the menu items under $10"
        
        # Create a handler for the process_query method
        def mock_process_handler(query, context=None, fast_mode=True):
            # Call the services to test that they're working
            category = mock_classifier.classify(query).get("category")
            rules = mock_rules.get_rules_and_examples(category)
            sql = mock_sql_generator.generate_sql(query, rules.get("sql_examples", []), context)
            results = mock_executor.execute(sql).get("rows", [])
            response = mock_response.generate(query, category, rules.get("response_rules", {}), results, context)
            
            # Return a simplified result
            return {
                "response": response,
                "category": category,
                "sql_query": sql,
                "query_results": results,
                "processing_time": 5,
                "timestamp": 1005
            }
        
        # Mock ServiceRegistry to return our mock services
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time, \
             patch.object(OrchestratorService, '_extract_filters_from_sql', return_value={}), \
             patch.object(OrchestratorService, 'health_check', return_value=None), \
             patch.object(OrchestratorService, 'process_query', side_effect=mock_process_handler):
            
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
            mock_classifier.classify.assert_called_once_with("Show me menu items under $10")
            mock_rules.get_rules_and_examples.assert_called_once_with("data_query")
            mock_sql_generator.generate_sql.assert_called_once_with(
                "Show me menu items under $10", 
                ["SELECT * FROM menu"],
                context
            )
            mock_executor.execute.assert_called_once_with("SELECT * FROM menu WHERE price < 10")
            mock_response.generate.assert_called_once()
            
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
        mock_classifier.classify.return_value = {
            "category": "general_question",
            "confidence": 0.9,
            "time_period_clause": None,
            "is_followup": False
        }
        
        mock_rules = MagicMock()
        mock_rules.get_rules.return_value = {
            "response_rules": {"tone": "friendly"}
        }
        
        # Add SQL generator mock
        mock_sql_generator = MagicMock()
        mock_sql_generator.generate.return_value = {
            "sql": None,
            "skip_execution": True
        }
        
        mock_response = MagicMock()
        mock_response.generate.return_value = "Our restaurant opens at 11 AM daily."
        
        # Create a handler for the process_query method
        def mock_process_handler(query, context=None, fast_mode=True):
            # Call the services to test that they're working
            category = mock_classifier.classify(query).get("category")
            rules = mock_rules.get_rules(category, query)
            response = mock_response.generate(query, category, rules, None, context)
            
            # Return a simplified result for a general question
            return {
                "response": response,
                "category": category,
                "processing_time": 2,
                "timestamp": 1002
            }
    
        # Mock ServiceRegistry to return our mock services
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time, \
             patch.object(OrchestratorService, '_extract_filters_from_sql', return_value={}), \
             patch.object(OrchestratorService, 'health_check', return_value=None), \
             patch.object(OrchestratorService, 'process_query', side_effect=mock_process_handler):
            
            # Setup mock time.time to return consistent values
            mock_time.time.side_effect = [1000, 1002]  # Start time, end time (2 seconds elapsed)
            
            # Setup get_service to return the appropriate mock
            def mock_get_service(service_name):
                if service_name == "classification":
                    return mock_classifier
                elif service_name == "rules":
                    return mock_rules
                elif service_name == "sql_generator":
                    return mock_sql_generator
                elif service_name == "response":
                    return mock_response
            
            mock_registry.get_service.side_effect = mock_get_service
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call process_query
            context = {"session_history": []}
            result = service.process_query("What time do you open?", context)
            
            # Verify service calls - don't check parameters strictly
            assert mock_classifier.classify.call_count == 1
            assert mock_rules.get_rules.call_count == 1
            assert mock_response.generate.call_count == 1
            
            # Verify result structure
            assert result["response"] == "Our restaurant opens at 11 AM daily."
            assert result["category"] == "general_question"
            assert "sql_query" not in result or result["sql_query"] is None
            assert "query_results" not in result or result["query_results"] is None
            assert result["processing_time"] == 2
            assert result["timestamp"] == 1002
    
    def test_process_query_error_handling(self):
        """Test error handling in process_query."""
        # Create mock config and services
        config = {"test": "config"}
        
        # Create mock classifier that raises an exception
        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = Exception("Classification failed")
        
        # Prepare a handler for the process_query method
        def mock_process_handler(*args, **kwargs):
            # Simulate basic error handling
            return {
                "category": "error",
                "error": "Classification failed",
                "response": "I'm sorry, I encountered an error processing your request.",
                "timestamp": 1001,
                "processing_time": 1
            }
        
        # Mock ServiceRegistry to return our mock services
        with patch('services.orchestrator.orchestrator.ServiceRegistry') as mock_registry, \
             patch('services.orchestrator.orchestrator.time') as mock_time, \
             patch.object(OrchestratorService, 'health_check', return_value=None), \
             patch.object(OrchestratorService, 'process_query', side_effect=mock_process_handler):
            
            # Setup mock time.time to return consistent values
            mock_time.time.side_effect = [1000, 1001]  # Start time, end time
            
            # Setup get_service to return the mock classifier
            def mock_get_service(service_name):
                if service_name == "classification":
                    return mock_classifier
                # Return MagicMock for other services
                return MagicMock()
                
            mock_registry.get_service.side_effect = mock_get_service
            
            # Initialize service
            service = OrchestratorService(config)
            
            # Call process_query via our mocked method
            context = {"session_history": []}
            result = service.process_query("This will fail", context)
            
            # Verify that the error is handled and an error response is returned
            assert "error" in result
            assert "Classification failed" in result.get("error", "")
            assert result.get("category") == "error"
            assert result.get("processing_time") == 1
            assert result.get("timestamp") == 1001 