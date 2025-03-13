"""
Logging setup utilities for the test runner.
"""

import os
import logging
import datetime
from pathlib import Path

def setup_logging(log_dir=None, log_level=logging.INFO):
    """
    Set up logging for test runs.
    
    Args:
        log_dir: Directory to store log files (default: PROJECT_ROOT/logs)
        log_level: Logging level to use (default: INFO)
        
    Returns:
        logger: Configured logger instance
    """
    if log_dir is None:
        # Use default log directory if not specified
        project_root = Path(__file__).parents[2]  # Go up 2 levels from utils/
        log_dir = os.path.join(project_root, "logs")
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger("test_runner")
    logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    logger.info(f"Log file: {log_file}")
    
    return logger 