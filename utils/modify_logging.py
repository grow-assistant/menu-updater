"""
Script to show how to modify the application code to ensure prompts are properly logged.
Run this script to patch logger configuration or test logger behavior.
"""

import os
import logging
import datetime

# Function to verify logger configuration
def verify_and_fix_logger():
    """
    Verify that the ai_menu_updater logger is configured properly
    and fix it if necessary.
    """
    # Check if the ai_menu_updater logger exists and has handlers
    logger = logging.getLogger("ai_menu_updater")
    
    # Print current logger configuration
    print(f"Logger 'ai_menu_updater' exists: {logger is not None}")
    print(f"Logger level: {logging.getLevelName(logger.level)}")
    print(f"Has handlers: {len(logger.handlers) > 0}")
    print(f"Handlers: {[type(h).__name__ for h in logger.handlers]}")
    print(f"Is disabled: {logger.disabled}")
    print(f"Propagates: {logger.propagate}")
    
    # If no handlers, set them up
    if len(logger.handlers) == 0:
        print("Adding handlers to logger...")
        
        # Create a session ID
        session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure logs directory exists
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create log file path
        log_filename = f"logs/fixed_log_{session_id}.log"
        
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
        
        # Set level to INFO
        logger.setLevel(logging.INFO)
        
        print(f"Logger configuration fixed. Logging to: {log_filename}")
    
    # Test the logger
    logger.info("=== Logger verification test ===")
    logger.info("If you see this message in your log file, logging is working correctly")
    
    return logger

# Example of how to add direct logging in the integrate_with_existing_flow function
def example_integrate_flow_fix(query):
    """
    Example showing how the integrate_with_existing_flow function should log prompts
    """
    # Get the logger
    logger = logging.getLogger("ai_menu_updater")
    
    # Log the incoming user query
    logger.info(f"User query: '{query}'")
    
    # Example of how prompts should be logged
    logger.info(f"Example prompt that would be generated for: '{query}'")
    
    # Simulate categorization
    logger.info(f"Categorization complete for query: '{query}'")
    
    # Simulate SQL generation
    logger.info(f"SQL generation complete for query: '{query}'")
    
    return {"success": True, "message": "Logging test successful"}

# Run the verification
if __name__ == "__main__":
    print("Verifying logger configuration...")
    logger = verify_and_fix_logger()
    
    # Test with a sample query
    test_query = "Show yesterday's sales figures"
    print(f"\nTesting with query: '{test_query}'")
    result = example_integrate_flow_fix(test_query)
    
    print("\nCheck your log files to verify that logging is working correctly.")
    print("If not, consider adding the following line to the beginning of your application:")
    print("\nimport logging")
    print("logging.basicConfig(level=logging.INFO, filename='logs/app.log',")
    print("                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')")
    
    print("\nOr add direct logging calls in your prompt generation functions:")
    print("with open('logs/prompts.log', 'a') as f:")
    print("    f.write(f\"[{datetime.datetime.now()}] Generated prompt: {prompt[:200]}...\\n\")") 