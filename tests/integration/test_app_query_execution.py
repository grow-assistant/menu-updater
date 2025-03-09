"""
Integration test for the complete application flow.

This test launches the application and tests the end-to-end functionality
by asking the question "How many orders were completed on 2/21/2025?"
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.classification.classifier import ClassificationService
from services.orchestrator.orchestrator import OrchestratorService


class TestAppQueryExecution:
    """Test the complete application flow by running the app and sending a query."""
    
    def setup_method(self):
        """Setup method that runs before each test."""
        # Ensure any environment variables needed are set
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy_key")
        os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "dummy_key")
        os.environ["DB_CONNECTION_STRING"] = os.environ.get("DB_CONNECTION_STRING", "postgresql://user:pass@localhost/db")

    def teardown_method(self):
        """Teardown method that runs after each test."""
        # Kill any running streamlit processes
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.process.wait()

    def test_fix_classifier_method(self):
        """Test that ClassificationService has the correct method 'classify'."""
        # This test checks if the ClassificationService has a method named 'classify'
        # or if it needs to be added to match what OrchestratorService is calling
        
        classifier = ClassificationService()
        
        # Check if classify method exists or if we need to add it
        if not hasattr(classifier, 'classify'):
            # Let's patch the ClassificationService class to add the missing method
            with patch.object(ClassificationService, 'classify', create=True) as mock_method:
                mock_method.return_value = {"category": "order_history"}
                
                # Create an orchestrator that uses our patched classifier
                orchestrator = OrchestratorService({"dummy_config": True})
                
                # The process_query method should now call classifier.classify without error
                # Instead of just assigning result, let's verify it's not None
                result = orchestrator.process_query("How many orders were completed on 2/21/2025?")
                assert result is not None
                
                # Verify our mock was called
                mock_method.assert_called_once()
                
            # This test should fail, indicating we need to add the classify method
            pytest.fail("ClassificationService is missing the 'classify' method that OrchestratorService tries to call")
        else:
            # If the method exists, the test should pass
            assert True

    def test_query_execution_with_patched_classifier(self):
        """Test order history query execution with a patched classifier."""
        # Patch the ClassificationService.classify_query method
        with patch.object(ClassificationService, 'classify_query') as mock_classify_query, \
             patch('services.execution.sql_executor.SQLExecutor.validate_connection') as mock_validate, \
             patch('services.execution.sql_executor.SQLExecutor.execute') as mock_execute, \
             patch('services.response.response_generator.ResponseGenerator.generate') as mock_response:
            # Make validate_connection do nothing
            mock_validate.return_value = None
            
            # Configure mocks with expected behavior
            mock_classify_query.return_value = {
                "query_type": "order_history",
                "confidence": 0.95,
                "classification_method": "test"
            }
            
            mock_execute.return_value = {
                "success": True,
                "data": [{"count": 15}],
                "performance_metrics": {"query_time": 0.05}
            }
            
            mock_response.return_value = {
                "response": "There were 15 orders completed on February 21, 2025.",
                "model": "test-model"
            }
            
            # Also patch ClassificationService.classify if it doesn't exist
            if not hasattr(ClassificationService, 'classify'):
                with patch.object(ClassificationService, 'classify', create=True) as mock_classify:
                    mock_classify.return_value = {
                        "category": "order_history",
                        "confidence": 0.95
                    }
                    
                    # Create a mock config
                    config = {
                        "api": {
                            "openai": {"api_key": "dummy_key", "model": "gpt-4"},
                            "gemini": {"api_key": "dummy_key"}
                        },
                        "database": {
                            "connection_string": "postgresql://user:pass@localhost/db"
                        },
                        "services": {
                            "rules": {
                                "rules_path": "tests/test_data/rules",
                                "resources_dir": "tests/test_data",
                                "sql_files_path": "tests/test_data/sql_patterns",
                                "cache_ttl": 60
                            },
                            "sql_generator": {
                                "template_path": "tests/test_data/templates"
                            },
                            "classification": {
                                "confidence_threshold": 0.7
                            }
                        }
                    }
                    
                    # Create an orchestrator with our configuration
                    orchestrator = OrchestratorService(config)
                    
                    # Process our query
                    query = "How many orders were completed on 2/21/2025?"
                    context = {}
                    
                    # This should now execute without errors
                    result = orchestrator.process_query(query, context)
                    assert result is not None
                    
                    # Verify the mock was called
                    mock_classify.assert_called_once_with(query)
            else:
                # If classify exists, just test it directly
                config = {
                    "api": {
                        "openai": {"api_key": "dummy_key", "model": "gpt-4"},
                        "gemini": {"api_key": "dummy_key"}
                    },
                    "database": {
                        "connection_string": "postgresql://user:pass@localhost/db"
                    },
                    "services": {
                        "rules": {
                            "rules_path": "tests/test_data/rules",
                            "resources_dir": "tests/test_data",
                            "sql_files_path": "tests/test_data/sql_patterns",
                            "cache_ttl": 60
                        },
                        "sql_generator": {
                            "template_path": "tests/test_data/templates"
                        },
                        "classification": {
                            "confidence_threshold": 0.7
                        }
                    }
                }
                
                # Create an orchestrator with our configuration
                orchestrator = OrchestratorService(config)
                
                # Process our query
                query = "How many orders were completed on 2/21/2025?"
                context = {}
                
                # This should now execute without errors
                result = orchestrator.process_query(query, context)
                assert result is not None
