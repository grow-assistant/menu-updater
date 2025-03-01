"""
Test script to verify prompt logging functionality.
This script directly calls prompt generation functions to make sure they are properly logged.
"""

import os
import sys
import logging
import datetime
from utils.langchain_integration import setup_logging

# Set up a session ID and initialize logging
session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
logger = setup_logging(session_id)
logger.info(f"=== Starting Prompt Logging Test at {session_id} ===")

# Import prompt generation functions
from prompts.google_gemini_prompt import create_gemini_prompt
from prompts.openai_categorization_prompt import create_categorization_prompt, create_query_categorization_prompt

# Test load_application_context function from main.py
try:
    from main import load_application_context
    context_files = load_application_context()
    logger.info(f"Successfully loaded application context: {context_files.keys() if context_files else 'None'}")
except Exception as e:
    logger.error(f"Error loading application context: {str(e)}")
    context_files = {
        "business_rules": "Test business rules",
        "database_schema": "Test database schema",
        "example_queries": "Test example queries"
    }

# Test each prompt function
def test_prompts():
    """Test various prompt generation functions"""
    logger.info("Testing prompt generation functions...")
    
    # Test gemini prompt
    logger.info("Testing create_gemini_prompt...")
    gemini_prompt = create_gemini_prompt(
        context_files=context_files,
        user_query="How many restaurants are open today?",
        location_id="location123"
    )
    logger.info(f"Gemini prompt length: {len(gemini_prompt)}")
    logger.info(f"Gemini prompt sample: {gemini_prompt[:100]}...")
    
    # Test categorization prompt
    logger.info("Testing create_categorization_prompt...")
    categorization_prompt = create_categorization_prompt()
    logger.info(f"Categorization prompt length: {len(str(categorization_prompt))}")
    logger.info(f"Categorization prompt sample: {str(categorization_prompt)[:100]}...")
    
    # Test query categorization prompt
    logger.info("Testing create_query_categorization_prompt...")
    query_categorization_prompt = create_query_categorization_prompt(
        user_query="How many orders did we have yesterday?"
    )
    logger.info(f"Query categorization prompt length: {len(query_categorization_prompt)}")
    logger.info(f"Query categorization prompt sample: {query_categorization_prompt[:100]}...")
    
    logger.info("All prompt tests completed successfully.")

if __name__ == "__main__":
    test_prompts()
    logger.info("=== Prompt Logging Test Completed ===")
    print(f"Test completed. Check logs/app_log_{session_id}.log for results.") 