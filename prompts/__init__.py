"""
This package contains prompt templates and query examples for the AI menu updater application.
"""

import os
import glob
import logging

# Get the logger that was configured in utils/langchain_integration.py
logger = logging.getLogger("ai_menu_updater")

def load_example_queries(request_type=None):
    """
    Load SQL queries directly from the database folder.
    
    Args:
        request_type (str, optional): The specific request type to load. If None, loads all.
        
    Returns:
        str: A string containing all the loaded queries with descriptions
    """
    all_queries = []
    
    try:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
        logger.info(f"Looking for database directory at: {base_dir}")
        logger.info(f"Absolute path exists: {os.path.exists(base_dir)}")
        
        # Try alternative paths if the standard one doesn't work
        if not os.path.exists(base_dir):
            # Try absolute path
            alt_base_dir = "C:/Python/ai-menu-updater/database"
            logger.info(f"Trying alternative path: {alt_base_dir}")
            if os.path.exists(alt_base_dir):
                logger.info(f"Found database at alternative path: {alt_base_dir}")
                base_dir = alt_base_dir
            else:
                # List parent directory to help debug
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                logger.info(f"Parent directory: {parent_dir}")
                try:
                    logger.info(f"Contents of parent directory: {os.listdir(parent_dir)}")
                except Exception as e:
                    logger.error(f"Could not list parent directory: {str(e)}")
                
                logger.warning(f"Database directory not found at {base_dir}")
                return "No example queries available - database directory not found"
        
        # Define which folders to load based on request_type
        folders_to_load = []
        if request_type:
            # Map request_type to folder name
            folder_map = {
                "order_history": "order_history",
                "update_price": "update_price",
                "disable_item": "disable_item",
                "enable_item": "enable_item",
                "query_menu": "query_menu",
                "query_performance": "query_performance",
                "query_ratings": "query_ratings",
                "delete_options": "delete_options"
            }
            if request_type in folder_map:
                folders_to_load = [folder_map[request_type]]
                logger.info(f"Loading examples for specific request type: {request_type}")
            else:
                logger.warning(f"Unknown request type: {request_type}, falling back to all folders")
                folders_to_load = [d for d in os.listdir(base_dir) 
                                if os.path.isdir(os.path.join(base_dir, d))]
        else:
            # Load all folders if no specific request_type
            logger.info("No specific request type provided, loading all example folders")
            folders_to_load = [d for d in os.listdir(base_dir) 
                              if os.path.isdir(os.path.join(base_dir, d))]
        
        logger.info(f"Folders to load: {folders_to_load}")
        
        # Process each folder
        for folder in folders_to_load:
            folder_path = os.path.join(base_dir, folder)
            if not os.path.exists(folder_path):
                logger.warning(f"Folder not found: {folder_path}")
                continue
                
            # Get SQL files in the folder
            sql_files = glob.glob(os.path.join(folder_path, "*.pgsql"))
            sql_files.sort()  # Sort to process in order (assuming filenames start with numbers)
            
            if sql_files:
                logger.info(f"Found {len(sql_files)} SQL files in {folder}")
                all_queries.append(f"\n{folder.upper()} EXAMPLES:")
                all_queries.append("--------------------------------------------------")
            else:
                logger.warning(f"No SQL files found in {folder}")
                continue
            
            # Process each SQL file
            for file_path in sql_files:
                try:
                    file_name = os.path.basename(file_path)
                    # Extract a description from the filename
                    description = file_name.replace(".pgsql", "").replace("_", " ")
                    # Remove leading numbers (like 01_, 02_)
                    if description[0].isdigit() and description[1].isdigit() and description[2] == "_":
                        description = description[3:]
                    
                    with open(file_path, 'r') as file:
                        content = file.read()
                        # Check for comment at top of file to use as description
                        lines = content.split("\n")
                        if lines and lines[0].startswith("--"):
                            description = lines[0].strip("- ")
                        
                        all_queries.append(f"{len(all_queries) - 1}. {description}:")
                        all_queries.append("--------------------------------------------------")
                        all_queries.append(content.strip())
                        all_queries.append("")
                except Exception as e:
                    logger.error(f"Error loading SQL file {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in load_example_queries: {str(e)}")
        return "Error loading example queries: " + str(e)
    
    if not all_queries:
        # If no queries were loaded, return a default message
        logger.warning("No example queries were loaded")
        return "No example queries available"
    
    # Join all queries with newlines
    result = "\n".join(all_queries)
    logger.info(f"Loaded {len(all_queries)} example query sections")
    return result

# Define a constant for backward compatibility
EXAMPLE_QUERIES = load_example_queries() 