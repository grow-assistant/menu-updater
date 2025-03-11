# Placeholder for test_classification_service.py

import pytest
import json
from unittest.mock import MagicMock, patch, Mock

from services.classification.classifier import ClassificationService
from services.classification.classifier_interface import QueryClassifierInterface

class MockResponse:
    """Mock response object to simulate OpenAI responses"""
    def __init__(self, content):
        self.choices = [MockChoice(content)]

class MockChoice:
    """Mock choice object for the response"""
    def __init__(self, content):
        self.message = MockMessage(content)

class MockMessage:
    """Mock message object for the choice"""
    def __init__(self, content):
        self.content = content

class TestClassificationService:
    @pytest.fixture
    def mock_openai_response(self):
        """Mock response from OpenAI"""
        content = json.dumps({
            "query_type": "order_history",
            "confidence": 0.95,
            "parameters": {
                "time_period": "last month",
                "filters": [{"field": "total", "operator": ">", "value": 100}],
                "entities": ["burger", "pizza"]
            }
        })
        return MockResponse(content)
    
    @pytest.fixture
    def classification_service(self):
        """Create a ClassificationService with mocked OpenAI client"""
        config = {
            "api": {
                "openai": {
                    "api_key": "test_key",
                    "model": "gpt-4o-mini"
                }
            }
        }
        with patch("services.classification.classifier.log_openai_request") as mock_log_request:
            with patch("services.classification.classifier.log_openai_response") as mock_log_response:
                service = ClassificationService(config=config)
                service.client = MagicMock()
                yield service
    
    def test_classify_order_history_query(self, classification_service, mock_openai_response):
        """Test classification of order history query"""
        classification_service.client.chat.completions.create.return_value = mock_openai_response
        
        result = classification_service.classify_query("How many orders did we have last month?")
        
        assert result["query_type"] == "order_history"
        assert result["confidence"] >= 0.9
        assert "parameters" in result
        assert "time_period" in result["parameters"]
        assert result["parameters"]["time_period"] == "last month"
    
    def test_classify_menu_query(self, classification_service):
        """Test classification of menu query"""
        content = json.dumps({
            "query_type": "menu",
            "confidence": 0.92,
            "parameters": {
                "entities": ["burger", "sides"]
            }
        })
        mock_response = MockResponse(content)
        classification_service.client.chat.completions.create.return_value = mock_response
        
        result = classification_service.classify_query("What's on our burger menu?")
        
        assert result["query_type"] == "menu"
        assert result["confidence"] >= 0.9
        assert "parameters" in result
        assert "entities" in result["parameters"]
        assert "burger" in result["parameters"]["entities"]
    
    def test_classify_action_request(self, classification_service):
        """Test classification of action request"""
        content = json.dumps({
            "query_type": "action",
            "confidence": 0.94,
            "parameters": {
                "action": "update_price",
                "entities": ["cheese burger"],
                "values": {"price": 9.99}
            }
        })
        mock_response = MockResponse(content)
        classification_service.client.chat.completions.create.return_value = mock_response
        
        result = classification_service.classify_query("Change the price of the cheese burger to $9.99")
        
        assert result["query_type"] == "action"
        assert result["confidence"] >= 0.9
        assert "parameters" in result
        assert "action" in result["parameters"]
        assert result["parameters"]["action"] == "update_price"
        assert "entities" in result["parameters"]
        assert "cheese burger" in result["parameters"]["entities"]
    
    def test_confidence_below_threshold(self, classification_service):
        """Test handling when confidence is below threshold"""
        content = json.dumps({
            "query_type": "general",
            "confidence": 0.6,
            "parameters": {}
        })
        mock_response = MockResponse(content)
        classification_service.client.chat.completions.create.return_value = mock_response
        
        result = classification_service.classify_query("What's the weather like today?")
        
        assert result["query_type"] == "general"
        assert result["confidence"] < 0.9
        assert "needs_clarification" in result
        assert result["needs_clarification"] is True
    
    def test_parameter_extraction(self, classification_service):
        """Test extraction of various parameters"""
        content = json.dumps({
            "query_type": "order_history",
            "confidence": 0.93,
            "parameters": {
                "time_period": "between January and March",
                "filters": [
                    {"field": "total", "operator": ">", "value": 50},
                    {"field": "customer_type", "operator": "=", "value": "VIP"}
                ],
                "entities": ["pizza"],
                "sort": {"field": "total", "order": "desc"},
                "limit": 10
            }
        })
        mock_response = MockResponse(content)
        classification_service.client.chat.completions.create.return_value = mock_response
        
        result = classification_service.classify_query(
            "Show me the top 10 highest value pizza orders from VIP customers between January and March"
        )
        
        assert result["query_type"] == "order_history"
        assert "parameters" in result
        assert "time_period" in result["parameters"]
        assert "filters" in result["parameters"], "Filters key missing from parameters"
        assert len(result["parameters"]["filters"]) == 2
        assert "sort" in result["parameters"]
        assert result["parameters"]["sort"]["field"] == "total"
        assert result["parameters"]["limit"] == 10

class TestQueryClassifierInterface:
    @pytest.fixture
    def interface(self):
        # Mock the classifier and prompt builder directly
        mock_classifier = MagicMock()
        mock_prompt_builder = MagicMock()
        
        # Create the interface
        interface = QueryClassifierInterface()
        
        # Replace the internal components with mocks
        interface._classifier = mock_classifier
        interface._prompt_builder = mock_prompt_builder
        
        return interface
    
    def test_interface_classify_query(self, interface):
        """Test that the interface properly delegates to the classifier"""
        interface._classifier.classify_query.return_value = {
            "query_type": "order_history",
            "confidence": 0.95,
            "parameters": {"time_period": "last month"}
        }
        
        result = interface.classify_query("How many orders did we have last month?")
        
        interface._classifier.classify_query.assert_called_once()
        assert result["query_type"] == "order_history"
        assert result["confidence"] == 0.95
    
    def test_interface_error_handling(self, interface):
        """Test that the interface handles errors gracefully"""
        interface._classifier.classify_query.side_effect = Exception("Test error")
        
        result = interface.classify_query("How many orders did we have last month?")
        
        assert result["query_type"] == "general"
        assert result["confidence"] == 0.1
        assert "error" in result
        assert "Test error" in result["error"]
    
    def test_get_supported_query_types(self, interface):
        """Test getting supported query types"""
        interface._prompt_builder.get_available_query_types.return_value = [
            "order_history", "menu", "action", "general"
        ]
        
        query_types = interface.get_supported_query_types()
        
        interface._prompt_builder.get_available_query_types.assert_called_once()
        assert len(query_types) == 4
        assert "order_history" in query_types
        assert "menu" in query_types
        assert "action" in query_types
