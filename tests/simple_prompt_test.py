"""
Minimalist script to test prompt logging functionality.
This script directly tests logging without any application context dependencies.
"""

import os
import logging
import datetime

# Set up logging directly in this script
def direct_setup_logging():
    """Configure a logger directly, bypassing any app-specific logic that might be failing"""
    session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    log_filename = f"logs/prompt_test_{session_id}.log"
    
    # Configure a simple logger
    logger = logging.getLogger("prompt_test")
    logger.setLevel(logging.INFO)
    
    # Add file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create and set formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"=== Test Started with ID {session_id} ===")
    logger.info(f"Logging to {log_filename}")
    
    return logger, log_filename

# Create logger
logger, log_file = direct_setup_logging()

# Test data
test_queries = [
    "Show me yesterday's orders",
    "What was our revenue last week?",
    "Update the price of Hamburger to $12.99"
]

# Log some test messages
logger.info("Testing simple prompt logging")
for i, query in enumerate(test_queries):
    logger.info(f"Test query {i+1}: '{query}'")
    # Simulate a prompt generation
    logger.info(f"Generated prompt would be for: '{query}'")
    logger.info("This would normally be a full prompt template")

logger.info("=== Test Completed Successfully ===")
print(f"Test completed. Check {log_file} to verify logging.") 