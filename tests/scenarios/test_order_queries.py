#!/usr/bin/env python
"""
Standalone test for order-related queries.

This test simulates a conversational interaction with the system,
where a user asks about completed orders on a specific date and then
follows up asking about who placed those orders.
"""

import os
import sys
import unittest
from typing import Dict, Any

# Add the parent directory to the path so we can import the test_utils module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tests.scenarios.test_utils import run_test, logger

class TestOrderQueries(unittest.TestCase):
    """Test class for order-related query scenarios."""
    
    def test_order_completion_date_and_customer(self):
        """
        Test a two-question sequence about orders:
        1. How many orders were completed on a specific date?
        2. Who placed those orders?
        """
        # Define the sequence of queries
        queries = [
            "How many orders were completed on 2/21/2025?",
            "Who placed those orders?"
        ]
        
        # Define validation functions
        def validate_first_response(response: Dict[str, Any]) -> bool:
            """Validate the response to the first query."""
            # Check if we got a response
            if not response.get("response_text"):
                logger.error("No response text received for first query")
                return False
                
            # Check if SQL was generated
            if not response.get("sql_query"):
                logger.error("No SQL query generated for first query")
                return False
                
            # Check if the SQL contains the date
            sql = response.get("sql_query", "").lower()
            if "2025-02-21" not in sql and "'2/21/2025'" not in sql:
                logger.error(f"SQL does not contain the expected date: {sql}")
                return False
                
            # Check if the response includes order count
            text = response.get("response_text", "").lower()
            if "order" not in text:
                logger.error(f"Response does not mention orders: {text}")
                return False
                
            # Look for the presence of a number, which should indicate the count
            if not any(char.isdigit() for char in text):
                logger.error(f"Response does not include a count number: {text}")
                return False
                
            # Check category
            if response.get("category") != "orders":
                logger.warning(f"Expected category 'orders', got '{response.get('category')}'")
                
            return True
            
        def validate_second_response(response: Dict[str, Any]) -> bool:
            """Validate the response to the second query."""
            # Check if we got a response
            if not response.get("response_text"):
                logger.error("No response text received for second query")
                return False
                
            # Check if SQL was generated
            if not response.get("sql_query"):
                logger.error("No SQL query generated for second query")
                return False
                
            # Check if the SQL contains customer or user information
            sql = response.get("sql_query", "").lower()
            if not any(term in sql for term in ["customer", "user", "person", "name"]):
                logger.error(f"SQL does not reference customer information: {sql}")
                return False
                
            # Check if the SQL reuses the date filter from the previous query
            if "2025-02-21" not in sql and "'2/21/2025'" not in sql:
                logger.error(f"SQL does not maintain context with date filter: {sql}")
                return False
                
            # Check if the response mentions customers or names
            text = response.get("response_text", "").lower()
            if not any(term in text for term in ["customer", "person", "name", "placed", "ordered"]):
                logger.error(f"Response does not mention customers: {text}")
                return False
                
            return True
            
        # Run the test with validators
        results = run_test(
            test_name="Order completion date and customer query",
            queries=queries, 
            validators=[validate_first_response, validate_second_response]
        )
        
        # Log results summary
        for i, result in enumerate(results):
            logger.info(f"Query {i+1} summary:")
            logger.info(f"  Category: {result.get('category', 'N/A')}")
            logger.info(f"  SQL: {result.get('sql_query', 'N/A')}")
            logger.info(f"  Response: {result.get('response_text', 'N/A')}")
    
    def test_popular_items_and_details(self):
        """
        Test a two-question sequence about popular menu items:
        1. What are the most popular items in the last month?
        2. Tell me more about the top item?
        """
        # Define the sequence of queries
        queries = [
            "What are the most popular items in the last month?",
            "Tell me more about the top item"
        ]
        
        # Define validation functions
        def validate_popular_items(response: Dict[str, Any]) -> bool:
            """Validate the response to the popular items query."""
            # Check if we got a response
            if not response.get("response_text"):
                logger.error("No response text received for popular items query")
                return False
                
            # Check if SQL was generated
            if not response.get("sql_query"):
                logger.error("No SQL query generated for popular items query")
                return False
                
            # Check if the SQL contains order items table and counts
            sql = response.get("sql_query", "").lower()
            if "order_items" not in sql or "count" not in sql:
                logger.error(f"SQL does not reference order_items or counts: {sql}")
                return False
                
            # Check if the SQL has time period filtering
            if "date" not in sql and "month" not in sql and "interval" not in sql:
                logger.error(f"SQL does not have time period filtering: {sql}")
                return False
                
            # Check if the response includes items
            text = response.get("response_text", "").lower()
            if "item" not in text and "popular" not in text:
                logger.error(f"Response does not mention items: {text}")
                return False
                
            return True
            
        def validate_item_details(response: Dict[str, Any]) -> bool:
            """Validate the response to the item details query."""
            # Check if we got a response
            if not response.get("response_text"):
                logger.error("No response text received for item details query")
                return False
                
            # Check if SQL was generated
            if not response.get("sql_query"):
                logger.error("No SQL query generated for item details query")
                return False
                
            # Check if the SQL references the items table
            sql = response.get("sql_query", "").lower()
            if "items" not in sql:
                logger.error(f"SQL does not reference items table: {sql}")
                return False
                
            # Check if the response includes item details
            text = response.get("response_text", "").lower()
            if not any(term in text for term in ["price", "description", "category"]):
                logger.error(f"Response does not include item details: {text}")
                return False
                
            return True
            
        # Run the test with validators
        results = run_test(
            test_name="Popular items and details query",
            queries=queries, 
            validators=[validate_popular_items, validate_item_details]
        )
        
        # Log results summary
        for i, result in enumerate(results):
            logger.info(f"Query {i+1} summary:")
            logger.info(f"  Category: {result.get('category', 'N/A')}")
            logger.info(f"  SQL: {result.get('sql_query', 'N/A')}")
            logger.info(f"  Response: {result.get('response_text', 'N/A')}")

def run_standalone():
    """Run the tests as a standalone script."""
    # Create a test suite with just this test case
    suite = unittest.TestSuite()
    suite.addTest(TestOrderQueries("test_order_completion_date_and_customer"))
    suite.addTest(TestOrderQueries("test_popular_items_and_details"))
    
    # Run the suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure for exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_standalone()) 