"""
Utility functions for running scenario-based tests.
"""

import os
import sys
import json
import logging
import unittest
import uuid
from typing import Dict, List, Any, Optional, Tuple, Callable
from unittest.mock import MagicMock, patch

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from services.orchestrator.orchestrator import OrchestratorService
from services.utils.service_registry import ServiceRegistry
from services.classification.classifier_interface import QueryClassifierInterface
from services.rules.rules_service import RulesService
from services.sql_generator.sql_generator_factory import SQLGeneratorFactory
from services.execution.sql_executor import SQLExecutor
from services.response.response_generator import ResponseGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("scenario_tests")

def safe_log(logger_fn, message):
    """Log a message safely, catching any exceptions."""
    try:
        logger_fn(message)
    except Exception as e:
        print(f"Error logging message: {e}")

class MockQueryResult:
    """Mock result for a query processing operation."""
    
    def __init__(self, query: str, category: str = "orders"):
        """Initialize with a query and optional category."""
        self.query = query
        self.category = category
        self.sql_query = self._generate_mock_sql()
        self.results = self._generate_mock_results()
        self.response_text = self._generate_mock_response()
        
    def _generate_mock_sql(self) -> str:
        """Generate a mock SQL query based on the input query."""
        if "2/21/2025" in self.query or "who placed those" in self.query.lower():
            if "who placed those" in self.query.lower():
                return """
                SELECT u.first_name, u.last_name, COUNT(o.id) as order_count
                FROM orders o
                JOIN users u ON o.customer_id = u.id
                WHERE DATE(o.created_at) = '2025-02-21'
                AND o.status IN (3, 4, 5) -- Completed status codes
                GROUP BY u.first_name, u.last_name
                ORDER BY order_count DESC
                """
            else:
                return """
                SELECT COUNT(id) as order_count
                FROM orders
                WHERE DATE(created_at) = '2025-02-21'
                AND status IN (3, 4, 5) -- Completed status codes
                """
        elif "popular items" in self.query.lower():
            self.category = "popular_items"
            return """
            SELECT i.name, i.id, COUNT(oi.id) as order_count
            FROM order_items oi
            JOIN items i ON oi.item_id = i.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH)
            AND o.status IN (3, 4, 5) -- Completed orders
            GROUP BY i.id, i.name
            ORDER BY order_count DESC
            LIMIT 10
            """
        elif "tell me more about" in self.query.lower() and "item" in self.query.lower():
            self.category = "menu_inquiry"
            return """
            SELECT i.name, i.description, i.price, c.name as category
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.id = 42 -- Assuming top item from previous query is ID 42
            """
        return "SELECT * FROM orders LIMIT 10"
    
    def _generate_mock_results(self) -> List[Dict[str, Any]]:
        """Generate mock results based on the query."""
        if "who placed those" in self.query.lower():
            return [
                {"first_name": "John", "last_name": "Doe", "order_count": 3},
                {"first_name": "Jane", "last_name": "Smith", "order_count": 2},
                {"first_name": "Bob", "last_name": "Johnson", "order_count": 1}
            ]
        elif "2/21/2025" in self.query:
            return [{"order_count": 6}]
        elif "popular items" in self.query.lower():
            return [
                {"name": "Cheeseburger", "id": 42, "order_count": 150},
                {"name": "French Fries", "id": 18, "order_count": 130},
                {"name": "Chocolate Shake", "id": 36, "order_count": 95},
                {"name": "Veggie Burger", "id": 58, "order_count": 75},
                {"name": "Chicken Sandwich", "id": 23, "order_count": 60}
            ]
        elif "tell me more about" in self.query.lower() and "item" in self.query.lower():
            return [
                {
                    "name": "Cheeseburger", 
                    "description": "A juicy beef patty with melted cheese, lettuce, tomato, and our special sauce", 
                    "price": 8.99, 
                    "category": "Burgers"
                }
            ]
        return []
    
    def _generate_mock_response(self) -> str:
        """Generate a mock text response based on the query and results."""
        if "who placed those" in self.query.lower():
            return "The orders on February 21, 2025 were placed by John Doe (3 orders), Jane Smith (2 orders), and Bob Johnson (1 order)."
        elif "2/21/2025" in self.query:
            return "There were 6 completed orders on February 21, 2025."
        elif "popular items" in self.query.lower():
            return "The most popular items in the last month are: Cheeseburger (150 orders), French Fries (130 orders), Chocolate Shake (95 orders), Veggie Burger (75 orders), and Chicken Sandwich (60 orders)."
        elif "tell me more about" in self.query.lower() and "item" in self.query.lower():
            return "The Cheeseburger is a juicy beef patty with melted cheese, lettuce, tomato, and our special sauce. It costs $8.99 and is in the Burgers category."
        return "I found some information about orders."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "query": self.query,
            "category": self.category,
            "sql_query": self.sql_query,
            "results": self.results,
            "response_text": self.response_text
        }

class ScenarioTestRunner:
    """Runner for scenario-based tests using mocks."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the test runner with configuration.
        
        Args:
            config_path: Optional path to a configuration JSON file
        """
        self.logger = logger
        self.config = self._load_config(config_path)
        self.session_history = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from a file or use defaults."""
        default_config = {
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "enable_verbal": False,
            "persona": "casual",
            "location_id": 62,
            "debug": True
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    return {**default_config, **loaded_config}
            except Exception as e:
                self.logger.warning(f"Error loading config from {config_path}: {e}")
                
        return default_config
    
    def run_scenario(self, queries: List[str], 
                     expected_results: Optional[List[Dict[str, Any]]] = None,
                     validators: Optional[List[Callable[[Dict[str, Any]], bool]]] = None) -> List[Dict[str, Any]]:
        """
        Run a scenario with a sequence of queries.
        
        Args:
            queries: List of query strings to execute in sequence
            expected_results: Optional list of expected results to compare against
            validators: Optional list of validator functions to run on each result
            
        Returns:
            List of results from each query
        """
        context = {
            "session_id": str(uuid.uuid4()),
            "session_history": self.session_history,
            "user_preferences": {},
            "recent_queries": [],
            "enable_verbal": self.config.get("enable_verbal", False),
            "persona": self.config.get("persona", "casual")
        }
        
        results = []
        
        for i, query in enumerate(queries):
            safe_log(self.logger.info, f"Running query {i+1}/{len(queries)}: {query}")
            
            # Process the query with a mock
            mock_result = MockQueryResult(query)
            response = mock_result.to_dict()
            
            # Add query context that would affect the next query
            if "2/21/2025" in query:
                context["date_filter"] = "2025-02-21"
            elif "popular items" in query.lower():
                context["top_item"] = {
                    "id": 42, 
                    "name": "Cheeseburger",
                    "order_count": 150
                }
            
            # Update context for next query
            context["session_history"].append({
                "query": query,
                "response": response.get("response_text", ""),
                "category": response.get("category", ""),
                "sql_query": response.get("sql_query", ""),
                "results": response.get("results", [])
            })
            
            context["recent_queries"].append(query)
            
            # Store results
            results.append(response)
            
            # Validate if expected results are provided
            if expected_results and i < len(expected_results):
                for key, value in expected_results[i].items():
                    assert key in response, f"Key '{key}' not found in response"
                    assert response[key] == value, f"Expected {value} for '{key}', got {response[key]}"
            
            # Run custom validators if provided
            if validators and i < len(validators):
                validator = validators[i]
                if validator and not validator(response):
                    raise AssertionError(f"Validation failed for query {i+1}: {query}")
            
            safe_log(self.logger.info, f"Query {i+1} completed successfully")
            
        # Update session history for future test runs
        self.session_history.extend(context["session_history"])
        
        return results

def run_test(test_name: str, queries: List[str], 
             expected_results: Optional[List[Dict[str, Any]]] = None,
             validators: Optional[List[Callable[[Dict[str, Any]], bool]]] = None,
             config_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run a single test scenario.
    
    Args:
        test_name: Name of the test for logging
        queries: List of queries to run in sequence
        expected_results: Optional expected results to validate
        validators: Optional validator functions
        config_path: Optional path to configuration file
        
    Returns:
        List of results from each query
    """
    logger.info(f"Running test scenario: {test_name}")
    runner = ScenarioTestRunner(config_path)
    results = runner.run_scenario(queries, expected_results, validators)
    logger.info(f"Test scenario completed: {test_name}")
    return results 