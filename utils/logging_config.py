import logging
from datetime import datetime

# Replace multiple logger configurations with a single session logger
def setup_logging(session_id):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"logs/app_log_{timestamp}.log"
    
    # Configure root logger to write to the session log file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler() # Keep console output if desired
        ]
    )
    
    logging.info(f"=== New Session Started at {timestamp} ===")
    logging.info(f"Session ID: {session_id}")
    
    return log_filename 