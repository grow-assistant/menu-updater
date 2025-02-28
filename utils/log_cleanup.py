import os
import glob
import logging
from datetime import datetime, timedelta

def cleanup_old_logs(max_age_days=7):
    """Clean up log files older than the specified age"""
    logger = logging.getLogger("ai_menu_updater")
    
    # Get current time
    now = datetime.now()
    
    # Find all log files
    log_files = glob.glob("logs/*.log")
    
    # Track statistics
    removed = 0
    kept = 0
    
    # Process each file
    for log_file in log_files:
        # Skip the consolidated log files
        if "app_log_" in log_file:
            kept += 1
            continue
            
        try:
            # Get the file's modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            
            # Calculate age
            age = now - mod_time
            
            # Remove if older than max_age_days
            if age > timedelta(days=max_age_days):
                os.remove(log_file)
                removed += 1
            else:
                kept += 1
        except Exception as e:
            logger.error(f"Error processing log file {log_file}: {str(e)}")
    
    logger.info(f"Log cleanup complete: {removed} files removed, {kept} files kept") 