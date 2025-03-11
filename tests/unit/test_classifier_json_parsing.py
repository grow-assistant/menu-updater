import unittest
from unittest.mock import MagicMock
import json
import sys
from pathlib import Path

# Add the project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.classification.classifier import ClassificationService

class TestClassifierJsonParsing(unittest.TestCase):
    """Test the JSON parsing in ClassificationService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.classifier = ClassificationService()
        self.classifier.categories = ["menu_items", "order_history", "general_question", "action"]
    
    def test_parse_json_direct(self):
        """Test parsing a direct JSON response."""
        response_mock = MagicMock()
        response_mock.choices = [MagicMock()]
        response_mock.choices[0].message.content = '{"query_type": "menu_items", "confidence": 0.9, "parameters": {"item": "burger"}}'
        
        result = self.classifier.parse_classification_response(response_mock, "Show burger menu items")
        
        self.assertEqual(result["query_type"], "menu_items")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["parameters"]["item"], "burger")
    
    def test_parse_json_markdown(self):
        """Test parsing a JSON response wrapped in markdown code blocks."""
        response_mock = MagicMock()
        response_mock.choices = [MagicMock()]
        response_mock.choices[0].message.content = '```json\n{"query_type": "menu_items", "confidence": 0.9, "parameters": {"item": "burger"}}\n```'
        
        result = self.classifier.parse_classification_response(response_mock, "Show burger menu items")
        
        self.assertEqual(result["query_type"], "menu_items")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["parameters"]["item"], "burger")
    
    def test_parse_json_markdown_no_language(self):
        """Test parsing a JSON response wrapped in markdown code blocks without language specifier."""
        response_mock = MagicMock()
        response_mock.choices = [MagicMock()]
        response_mock.choices[0].message.content = '```\n{"query_type": "menu_items", "confidence": 0.9, "parameters": {"item": "burger"}}\n```'
        
        result = self.classifier.parse_classification_response(response_mock, "Show burger menu items")
        
        self.assertEqual(result["query_type"], "menu_items")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["parameters"]["item"], "burger")
    
    def test_parse_json_markdown_no_newlines(self):
        """Test parsing a JSON response wrapped in markdown code blocks without newlines after backticks."""
        response_mock = MagicMock()
        response_mock.choices = [MagicMock()]
        response_mock.choices[0].message.content = '```{"query_type": "menu_items", "confidence": 0.9, "parameters": {"item": "burger"}}```'
        
        result = self.classifier.parse_classification_response(response_mock, "Show burger menu items")
        
        self.assertEqual(result["query_type"], "menu_items")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["parameters"]["item"], "burger")
    
    def test_parse_json_with_whitespace(self):
        """Test parsing a JSON response with extra whitespace."""
        response_mock = MagicMock()
        response_mock.choices = [MagicMock()]
        response_mock.choices[0].message.content = """```json
        {
            "query_type": "menu_items", 
            "confidence": 0.9, 
            "parameters": {
                "item": "burger"
            }
        }
        ```"""
        
        result = self.classifier.parse_classification_response(response_mock, "Show burger menu items")
        
        self.assertEqual(result["query_type"], "menu_items")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["parameters"]["item"], "burger")


if __name__ == "__main__":
    unittest.main() 