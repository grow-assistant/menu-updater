#!/usr/bin/env python
"""
Script to read all SQL files in each subdirectory of sql_files and update the corresponding examples.json files.

Usage:
  python update_sql_examples.py                     # Process all subdirectories
  python update_sql_examples.py order_ratings       # Process only the order_ratings directory
  python update_sql_examples.py dir1 dir2 dir3      # Process multiple specific directories
  python update_sql_examples.py --list              # List available directories without processing
"""

import os
import json
import re
import sys
import argparse
import logging
from datetime import datetime

# Constants
SQL_BASE_DIR = "services/sql_generator/sql_files"
LOG_FILE = "sql_examples_update.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def extract_query_from_sql(filename, sql_content):
    """
    Extract a natural language query description from the SQL file.
    Uses both the file name and the comment at the top of the file.
    """
    # Clean up the filename to make it more readable
    name_without_ext = os.path.splitext(filename)[0]
    name_parts = name_without_ext.split('_')
    
    # Remove numeric prefix if it exists (like "01_", "02_", etc.)
    if name_parts[0].isdigit() or (len(name_parts[0]) >= 2 and name_parts[0][:-1].isdigit()):
        name_parts = name_parts[1:]
    
    # Convert snake_case to spaces
    name_query = ' '.join(name_parts).replace('_', ' ')
    
    # Look for comments at the beginning of the file
    comment_match = re.match(r'^--\s*(.*?)\n', sql_content)
    comment_query = comment_match.group(1).strip() if comment_match else ""
    
    # If both name and comment provide information, combine them
    if name_query and comment_query and not comment_query.lower() in name_query.lower():
        query = f"{comment_query} ({name_query})"
    else:
        # Otherwise use whichever is more informative
        query = comment_query if comment_query else name_query
        if not query:
            query = "SQL Query"  # Fallback
    
    # Capitalize the first letter and ensure it ends with a proper question mark if it's a question
    query = query[0].upper() + query[1:]
    if query.lower().startswith("what") or query.lower().startswith("how") or query.lower().startswith("show"):
        if not query.endswith("?"):
            query += "?"
    
    return query


def read_sql_files(directory):
    """Read all SQL files in the directory and extract query and SQL content."""
    examples = []
    
    try:
        # Get all .pgsql files in the directory and sort them
        sql_files = [f for f in os.listdir(directory) if f.endswith('.pgsql') or f.endswith('.sql')]
        sql_files.sort()  # Sort filenames to preserve their numeric order
        
        if not sql_files:
            logger.info(f"No SQL files found in {directory}")
            return examples
        
        logger.info(f"Processing {len(sql_files)} files in {directory}")
        
        for filename in sql_files:
            filepath = os.path.join(directory, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                    # Extract query from comment at the top and filename
                    query = extract_query_from_sql(filename, content)
                    logger.info(f"  - {filename}: '{query}'")
                    
                    # Create example object
                    example = {
                        "query": query,
                        "sql": content.strip()
                    }
                    
                    examples.append(example)
            except Exception as e:
                logger.error(f"Error processing file {filepath}: {e}")
                
    except Exception as e:
        logger.error(f"Error reading directory {directory}: {e}")
    
    return examples


def update_examples_json(examples, directory):
    """Update the examples.json file with the new examples."""
    examples_file = os.path.join(directory, "examples.json")
    
    try:
        # Create backup of existing file if it exists
        if os.path.exists(examples_file):
            backup_file = f"{examples_file}.bak"
            try:
                with open(examples_file, 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                logger.info(f"Created backup: {backup_file}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
        
        # Write the new examples to the file
        with open(examples_file, 'w', encoding='utf-8') as file:
            json.dump(examples, file, indent=2)
        
        logger.info(f"Updated {examples_file} with {len(examples)} examples")
        return True
    except Exception as e:
        logger.error(f"Error updating {examples_file}: {e}")
        return False


def process_directory(directory):
    """Process all SQL files in a directory and update its examples.json."""
    logger.info(f"\nProcessing directory: {directory}")
    
    if not os.path.exists(directory):
        logger.error(f"Directory {directory} does not exist")
        return False
    
    if not os.path.isdir(directory):
        logger.error(f"{directory} is not a directory")
        return False
    
    examples = read_sql_files(directory)
    
    if examples:
        success = update_examples_json(examples, directory)
        return success
    else:
        logger.info(f"No examples to update in {directory}")
        return False


def get_full_path(dir_name):
    """Get the full path of a directory, handling both relative and absolute paths."""
    # Check if it's already a full path to an existing directory
    if os.path.isdir(dir_name):
        return dir_name
        
    # Check if it's a subdirectory of SQL_BASE_DIR
    potential_path = os.path.join(SQL_BASE_DIR, dir_name)
    if os.path.isdir(potential_path):
        return potential_path
        
    # Return the original name (which will fail the existence check later)
    return dir_name


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update examples.json files from SQL files in subdirectories"
    )
    parser.add_argument(
        "directories", 
        nargs="*", 
        help="Specific subdirectories to process (default: process all)"
    )
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List available directories without processing"
    )
    return parser.parse_args()


def main():
    """Main function to run the script."""
    start_time = datetime.now()
    logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    args = parse_arguments()
    
    # List available directories if requested
    if args.list:
        logger.info(f"Available directories in {SQL_BASE_DIR}:")
        try:
            subdirs = [d for d in os.listdir(SQL_BASE_DIR) if os.path.isdir(os.path.join(SQL_BASE_DIR, d))]
            subdirs.sort()
            for i, subdir in enumerate(subdirs, 1):
                logger.info(f"  {i}. {subdir}")
        except Exception as e:
            logger.error(f"Error listing directories: {e}")
        return
    
    # Determine which directories to process
    if args.directories:
        # Process only specified directories
        raw_dirs = args.directories
        logger.info(f"Processing specified directories: {', '.join(raw_dirs)}")
        
        # Convert directory names to full paths
        subdirs = [get_full_path(d) for d in raw_dirs]
    else:
        # Process all subdirectories
        logger.info(f"Scanning for subdirectories in {SQL_BASE_DIR}...")
        try:
            subdirs = [os.path.join(SQL_BASE_DIR, d) for d in os.listdir(SQL_BASE_DIR) 
                      if os.path.isdir(os.path.join(SQL_BASE_DIR, d))]
            subdirs.sort()
            
            if not subdirs:
                logger.warning(f"No subdirectories found in {SQL_BASE_DIR}")
                return
            
            logger.info(f"Found {len(subdirs)} subdirectories")
        except Exception as e:
            logger.error(f"Error scanning for subdirectories: {e}")
            return
    
    # Process each directory
    processed_count = 0
    for full_path in subdirs:
        if process_directory(full_path):
            processed_count += 1
    
    total = len(subdirs)
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"\nDone! Successfully processed {processed_count} out of {total} directories.")
    logger.info(f"Script completed in {duration.total_seconds():.2f} seconds")
    logger.info(f"Log saved to {os.path.abspath(LOG_FILE)}")


if __name__ == "__main__":
    main() 