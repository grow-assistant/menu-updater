"""
Test script to verify time period extraction from user queries.
"""
import os
import json
import sys
from pathlib import Path

# Make sure we can import from the services directory
sys.path.append(str(Path(__file__).parent))

# Import required modules
from services.classification.classifier import ClassificationService
from services.classification.prompt_builder import ClassificationPromptBuilder

def test_date_extraction():
    """Test extracting a specific date from a query."""
    print("Testing time period extraction from queries...")
    
    # Create configuration
    # Note: Normally we'd get the API key from config, but for testing we'll use environment variable
    # You need to set OPENAI_API_KEY in your environment before running this script
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set this variable to your OpenAI API key and try again.")
        return
    
    config = {
        "api": {
            "openai": {
                "api_key": openai_api_key,
                "model": "gpt-4o-mini"  # Using the smaller model for faster results
            }
        }
    }
    
    # Initialize the classification service
    print("Initializing classification service...")
    classifier = ClassificationService(config)
    
    # Test queries
    test_queries = [
        "How many orders were completed on 2/21/2025?",
        "Show me sales from last week",
        "What were the most popular items in January 2024?",
        "How did our dessert menu perform during the holiday season?",
        "List all vegetarian orders from the past 3 months"
    ]
    
    # Run tests
    print("\nRunning test queries...\n")
    for query in test_queries:
        print(f"Query: '{query}'")
        result = classifier.classify(query)
        
        # Extract and display results
        category = result.get("category")
        time_period = result.get("time_period_clause")
        
        print(f"  Category: {category}")
        print(f"  Time Period Clause: {time_period if time_period else 'None detected'}")
        print()
    
    # Focus on our specific test case
    specific_query = "How many orders were completed on 2/21/2025?"
    print(f"\nDetailed test for: '{specific_query}'")
    result = classifier.classify(specific_query)
    
    print(f"Full classification result:")
    print(json.dumps(result, indent=2))
    
    # Evaluate success
    time_period = result.get("time_period_clause")
    if time_period and "2025-02-21" in time_period:
        print("\n✅ SUCCESS: The date '2/21/2025' was correctly extracted!")
    else:
        print("\n❌ FAILED: The date extraction did not work as expected.")
        if time_period:
            print(f"Expected to find '2025-02-21' in the time period clause but got: {time_period}")
        else:
            print("No time period clause was returned.")

if __name__ == "__main__":
    test_date_extraction() 