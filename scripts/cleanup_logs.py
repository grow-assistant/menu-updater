#!/usr/bin/env python
"""
Log Cleanup Utility

This script helps manage log files for the Swoop AI application.
It provides commands to:
1. Rotate the main app.log file
2. Clean up old log files
3. Purge all logs except the main app.log file

Usage:
  python scripts/cleanup_logs.py [command]

Commands:
  rotate   - Rotate the main app.log file
  clean    - Clean up old log files
  purge    - Purge all logs except the main app.log file

Examples:
  python scripts/cleanup_logs.py rotate
  python scripts/cleanup_logs.py clean --days 30
  python scripts/cleanup_logs.py purge
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add project root to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import log utilities
from services.utils.logging import setup_logging, cleanup_log_files, purge_logs

def rotate_app_log():
    """Rotate the main app.log file"""
    logger = logging.getLogger("swoop_ai")
    
    logs_dir = "logs"
    app_log_path = os.path.join(logs_dir, "app.log")
    
    if not os.path.exists(app_log_path):
        logger.info("app.log file not found")
        return
        
    try:
        # Create backup name with timestamp
        backup_name = f"app.log.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup_path = os.path.join(logs_dir, backup_name)
        
        # Get file size for logging
        size_mb = os.path.getsize(app_log_path) / (1024 * 1024)
        
        # Rename the current file
        os.rename(app_log_path, backup_path)
        
        # Create a fresh file
        with open(app_log_path, 'w') as f:
            f.write(f"Log rotated at {datetime.now().isoformat()} - previous log at {backup_name}\n")
            
        logger.info(f"Rotated app.log to {backup_name} ({size_mb:.2f} MB)")
        print(f"Rotated app.log to {backup_name} ({size_mb:.2f} MB)")
        
    except Exception as e:
        logger.error(f"Failed to rotate app.log: {str(e)}")
        print(f"Error: Failed to rotate app.log: {str(e)}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Log Cleanup Utility")
    parser.add_argument("command", choices=["rotate", "clean", "purge"], help="Log management command")
    parser.add_argument("--days", type=int, default=30, help="Maximum age of log files in days")
    parser.add_argument("--max-app-size", type=int, default=100, help="Maximum size of app.log in MB")
    parser.add_argument("--max-sessions", type=int, default=10, help="Maximum number of session directories to keep")
    
    args = parser.parse_args()
    
    # Set up basic logging
    setup_logging()
    
    # Execute the requested command
    if args.command == "rotate":
        print("Rotating app.log...")
        rotate_app_log()
        
    elif args.command == "clean":
        print(f"Cleaning up log files older than {args.days} days...")
        cleanup_log_files(max_file_age_days=args.days, max_app_log_size_mb=args.max_app_size)
        print("Log cleanup complete!")
        
    elif args.command == "purge":
        print("WARNING: This will delete all logs except the main app.log file!")
        confirm = input("Are you sure you want to continue? (y/n): ")
        if confirm.lower() == 'y':
            print("Purging logs...")
            purge_logs()
            print("Log purge complete!")
        else:
            print("Purge cancelled.")

if __name__ == "__main__":
    main() 