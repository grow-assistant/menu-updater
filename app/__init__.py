"""
Main package for the Streamlit app.
"""

import logging
import datetime
import os

def setup_logging():
    """
    Configure the shared logger for all components
    
    Returns:
        logger: The configured logger
    """
    # Create a session ID for this run
    session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # Set up log file path
    log_filename = f"logs/app_log_{session_id}.log"
    
    # Configure root logger to capture everything
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also output to console
        ]
    )
    
    # Create or get the application-specific logger
    app_logger = logging.getLogger("ai_menu_updater")
    app_logger.setLevel(logging.INFO)
    
    # Output session start messages
    app_logger.info(f"=== New Session Started at {session_id} ===")
    app_logger.info(f"All logs consolidated in {log_filename}")
    
    return app_logger

# Configure the logger when importing the package
logger = setup_logging() 