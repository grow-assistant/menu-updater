"""
Unit tests for the Classification Service.

Tests the functionality of the ClassificationService class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.classification import ClassificationService


class TestClassificationService:
    """Test cases for the Classification Service."""

    def test_init_classification_service(self, mock_openai_client, test_config):
        """Test the initialization of the ClassificationService."""
        classification_service = ClassificationService(
            ai_client=mock_openai_client,
            config=test_config
        )
        assert classification_service is not None
        assert classification_service.ai_client == mock_openai_client
        assert classification_service.config == test_config

    def test_classify_query(self, mock_classifier):
        """Test classifying a query to determine its type."""
        # Test with mocked classify_query
        query_type, query_info = mock_classifier.classify_query(
            "Show me menu items at Idle Hour"
        )
        assert query_type == "sql_query"
        assert query_info["query_type"] == "menu_query"
        assert query_info["date_range"] == "last week"

    def test_classify_query_no_ai_client(self, test_config):
        """Test classifying a query without an AI client."""
        classifier = ClassificationService(
            ai_client=None,
            config=test_config
        )
        
        with patch.object(classifier, "analyze_query_pattern") as mock_analyze:
            mock_analyze.return_value = ("sql_query", {"query_type": "menu_query"})
            
            query_type, query_info = classifier.classify_query("Show me menu items at Idle Hour")
            assert query_type == "sql_query"
            assert query_info["query_type"] == "menu_query"

    def test_build_classification_prompt(self, mock_classifier):
        """Test building a prompt for query classification."""
        with patch.object(mock_classifier, "build_classification_prompt") as mock_build:
            mock_build.return_value = "Test classification prompt"
            
            prompt = mock_classifier.build_classification_prompt("Show me menu items at Idle Hour")
            assert prompt == "Test classification prompt"

    def test_parse_classification_response(self, mock_classifier):
        """Test parsing the classification response from AI."""
        with patch.object(mock_classifier, "parse_classification_response") as mock_parse:
            mock_parse.return_value = ("sql_query", {"query_type": "menu_query"})
            
            ai_response = """
            {
                "query_type": "sql_query",
                "query_info": {
                    "category": "menu_query"
                }
            }
            """
            
            query_type, query_info = mock_classifier.parse_classification_response(ai_response)
            assert query_type == "sql_query"
            assert query_info["query_type"] == "menu_query"

    def test_analyze_query_pattern_menu_query(self, mock_classifier):
        """Test analyzing a menu query pattern."""
        with patch.object(mock_classifier, "analyze_query_pattern") as mock_analyze:
            mock_analyze.return_value = ("sql_query", {"query_type": "menu_query"})
            
            query_type, query_info = mock_classifier.analyze_query_pattern("Show me menu items at Idle Hour")
            assert query_type == "sql_query"
            assert query_info["query_type"] == "menu_query"

    def test_analyze_query_pattern_menu_update(self, mock_classifier):
        """Test analyzing a menu update pattern."""
        with patch.object(mock_classifier, "analyze_query_pattern") as mock_analyze:
            mock_analyze.return_value = (
                "menu_update", 
                {"query_type": "menu_update", "update_type": "price_update", "item_name": "Caesar Salad", "new_price": 12.99}
            )
            
            query_type, query_info = mock_classifier.analyze_query_pattern("Change the price of Caesar Salad to $12.99")
            assert query_type == "menu_update"
            assert query_info["update_type"] == "price_update"
            assert query_info["item_name"] == "Caesar Salad"
            assert query_info["new_price"] == 12.99

    def test_analyze_query_pattern_general_query(self, mock_classifier):
        """Test analyzing a general query pattern."""
        with patch.object(mock_classifier, "analyze_query_pattern") as mock_analyze:
            mock_analyze.return_value = ("general", {"query_type": "general"})
            
            query_type, query_info = mock_classifier.analyze_query_pattern("What's the weather like today?")
            assert query_type == "general"
            assert query_info["query_type"] == "general"

    def test_extract_price_update_info(self, mock_classifier):
        """Test extracting price update information from a query."""
        with patch.object(mock_classifier, "extract_price_update_info") as mock_extract:
            mock_extract.return_value = {"item_name": "Caesar Salad", "new_price": 12.99}
            
            info = mock_classifier.extract_price_update_info("Change the price of Caesar Salad to $12.99")
            assert info["item_name"] == "Caesar Salad"
            assert info["new_price"] == 12.99

    def test_extract_availability_update_info(self, mock_classifier):
        """Test extracting availability update information from a query."""
        with patch.object(mock_classifier, "extract_availability_update_info") as mock_extract:
            mock_extract.return_value = {"item_name": "Caesar Salad", "is_disabled": True}
            
            info = mock_classifier.extract_availability_update_info("Disable the Caesar Salad")
            assert info["item_name"] == "Caesar Salad"
            assert info["is_disabled"] is True 