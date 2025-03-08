"""
Test to verify that the application can run and process a query correctly.

This test directly initializes the OrchestratorService and runs a query through it
to check that the full pipeline works correctly.
"""

import os
import sys
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure minimal logging
logging.basicConfig(level=logging.INFO)

from services.orchestrator.orchestrator import OrchestratorService


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "api": {
            "openai": {"api_key": "test-key", "model": "gpt-4"},
            "gemini": {"api_key": "test-key", "model": "gemini-pro"}
        },
        "database": {
            "connection_string": "sqlite:///:memory:",
            "max_rows": 1000,
            "timeout": 30
        },
        "logging": {
            "level": "INFO"
        }
    }


def test_process_order_history_query(mock_config):
    """Test that the orchestrator can process an order history query."""
    # Create patches for all external services
    with patch("services.classification.classifier.ClassificationService.classify_query") as mock_classify:
        # Set up the classification result
        mock_classify.return_value = {
            "query_type": "order_history",
            "confidence": 0.95,
            "classification_method": "test"
        }
        
        # Patch the SQL generation
        with patch("services.sql_generator.gemini_sql_generator.GeminiSQLGenerator.generate") as mock_generate:
            mock_generate.return_value = {
                "success": True,
                "query": "SELECT COUNT(*) FROM orders WHERE updated_at = '2025-02-21'",
                "query_type": "SELECT"
            }
            
            # Patch the SQL execution
            with patch("services.execution.sql_executor.SQLExecutor.execute") as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "results": [{"count": 15}],
                    "performance_metrics": {"query_time": 0.05}
                }
                
                # Patch the response generation
                with patch("services.response.response_generator.ResponseGenerator.generate") as mock_response:
                    mock_response.return_value = {
                        "text": "There were 15 orders completed on February 21, 2025.",
                        "model": "test-model"
                    }
                    
                    # Initialize the orchestrator with mocked services
                    orchestrator = OrchestratorService(mock_config)
                    
                    # Process the query
                    query = "How many orders were completed on 2/21/2025?"
                    result = orchestrator.process_query(query)
                    
                    # Verify the result
                    assert "response" in result
                    assert result["response"] == "There were 15 orders completed on February 21, 2025."
                    assert "category" in result
                    assert result["category"] == "order_history"
                    
                    # Verify all services were called
                    mock_classify.assert_called_once()
                    mock_generate.assert_called_once()
                    mock_execute.assert_called_once()
                    mock_response.assert_called_once()


def test_end_to_end_query():
    """
    Test the full application end-to-end without mocks.
    
    This is a real integration test that will attempt to process a query
    through the entire system. It requires all external services to be available.
    """
    # Skip this test if we're not explicitly running integration tests
    if "INTEGRATION_TESTS" not in os.environ:
        pytest.skip("Skipping end-to-end test. Set INTEGRATION_TESTS=1 to run.")
    
    # Load a real config and create an orchestrator
    try:
        # Initialize the orchestrator
        orchestrator = OrchestratorService({})
        
        # Process a test query
        query = "How many orders were completed on 2/21/2025?"
        result = orchestrator.process_query(query)
        
        # We don't assert specific values since external services are involved,
        # but we check the structure is correct
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        assert "category" in result
        assert "execution_time" in result
    except Exception as e:
        # In an integration test, we might encounter real-world errors
        # We log them but still fail the test
        logging.error(f"End-to-end test failed: {str(e)}")
        raise 