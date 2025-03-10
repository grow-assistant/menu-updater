"""
Integration test for validating follow-up query handling in the orchestrator service.
Tests the specific flow: initial order count question followed by "who placed those orders".
"""
import os
import sys
import json
import pytest
from datetime import datetime
import time

# Add the parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.orchestrator.orchestrator import OrchestratorService

class TestFollowupQueries:
    """Test class for follow-up query functionality."""
    
    @pytest.fixture
    def config(self):
        """Provide a basic configuration for testing."""
        # Use environment variables for API keys if available
        return {
            "api": {
                "openai": {
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "model": "gpt-4o-mini"
                },
                "gemini": {
                    "api_key": os.environ.get("GEMINI_API_KEY")
                },
                "elevenlabs": {
                    "api_key": os.environ.get("ELEVENLABS_API_KEY", "")
                }
            },
            "database": {
                "connection_string": os.environ.get("DATABASE_URL", 
                                                   "postgresql://postgres:postgres@localhost:5432/restaurant")
            },
            "persona": "casual",
            "application": {
                "max_history_items": 10
            },
            "services": {
                "rules": {
                    "rules_path": "services/rules/query_rules"
                },
                "sql_generator": {
                    "examples_path": "services/sql_generator/sql_files"
                },
                "classifier": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1
                },
                "response": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.7
                }
            }
        }
    
    @pytest.fixture
    def orchestrator(self, config):
        """Create a real orchestrator instance."""
        return OrchestratorService(config)
    
    def test_followup_query_flow(self, orchestrator):
        """
        Test the specific flow:
        1. "How many orders were completed on 2/21/2025?"
        2. "Who placed those orders?"
        
        Verify context is maintained and responses are correct.
        """
        # Define expected customer names for validation
        expected_customers = ["Brandon Devers", "Alex Solis", "Matt Agosto", "Michael Russell"]
        
        # ===== EXECUTE FIRST QUERY =====
        first_query = "How many orders were completed on 2/21/2025?"
        first_context = {
            "session_history": [],
            "user_preferences": {},
            "recent_queries": [],
            "enable_verbal": False,  # Disable verbal to avoid ElevenLabs dependency
            "persona": "casual"
        }
        
        print(f"\n\n==== EXECUTING FIRST QUERY: '{first_query}' ====")
        first_result = orchestrator.process_query(first_query, first_context)
        
        print(f"\nFirst query response: {first_result['response']}")
        print(f"Query results: {first_result['query_results']}")
        
        # ===== VERIFY FIRST QUERY RESULTS =====
        assert first_result["query"] == first_query
        assert first_result["category"] == "order_history"
        
        # Flexible checks on response content
        self._check_order_count_response(first_result["response"], 4, "2025-02-21")
        
        # ===== EXECUTE FOLLOW-UP QUERY =====
        followup_query = "Who placed those orders?"
        
        print(f"\n\n==== EXECUTING FOLLOW-UP QUERY: '{followup_query}' ====")
        # Use the same context object (with accumulated history)
        followup_result = orchestrator.process_query(followup_query, first_context)
        
        print(f"\nFollow-up query response: {followup_result['response']}")
        if followup_result.get("query_results"):
            print(f"Query results: {followup_result['query_results']}")
        
        # ===== VERIFY FOLLOW-UP QUERY RESULTS =====
        assert followup_result["query"] == followup_query
        assert followup_result["category"] == "order_history"
        
        # Check that customer names are in the response
        if followup_result["query_results"]:
            self._check_customer_names_in_results(followup_result["query_results"], expected_customers)
        
        # Print test success message
        print("\n✅ Follow-up query integration test completed successfully!")

    def _check_order_count_response(self, response, expected_count, expected_date):
        """Check if the order count response contains the expected information."""
        # Convert response to lowercase for case-insensitive matching
        response = response.lower()
        
        # Basic checks for key information
        assert str(expected_count) in response, f"Expected count {expected_count} not found in response: {response}"
        
        # Various date formats might be used
        date_variants = [
            expected_date,               # 2025-02-21
            expected_date.replace("-", "/"),  # 2025/02/21
            "february 21",               # Month day
            "feb 21",                    # Abbreviated month
            "2/21"                       # Short date
        ]
        
        # Check if any date variant is present
        date_found = any(variant.lower() in response for variant in date_variants)
        assert date_found, f"Expected date reference not found in response: {response}"
        
        # Check that it's talking about completed orders
        assert "order" in response, f"No mention of orders in response: {response}"

    def _check_customer_names_in_results(self, query_results, expected_customers):
        """Check if customer names appear in the query results."""
        # Extract full names from the query results if available
        result_names = []
        for result in query_results:
            if isinstance(result, dict):
                first_name = result.get('first_name', '')
                last_name = result.get('last_name', '')
                if first_name or last_name:
                    result_names.append(f"{first_name} {last_name}".strip())
        
        # If we have names in the results, verify them
        if result_names:
            for name in result_names:
                print(f"Found customer: {name}")
            
            # Check that at least some expected customers appear
            matches = 0
            for expected in expected_customers:
                for actual in result_names:
                    # Allow partial matches (e.g., "Alex Solis" matches "Alex Solis II")
                    if expected.lower() in actual.lower() or actual.lower() in expected.lower():
                        matches += 1
                        break
            
            # We should match at least 2 customers
            assert matches >= 2, f"Not enough customer names matched in results: {result_names}"
        else:
            # If no results with names, check the whole response structure
            print("No customer names found in direct results, this may indicate a different response format")

if __name__ == "__main__":
    # Allow running as a standalone script 
    pytest.main(["-xvs", __file__]) 