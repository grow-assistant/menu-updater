"""
Configuration loading utilities for the test runner.
"""

import os
import re
import yaml
from pathlib import Path

def load_config(config_path=None):
    """
    Load the application configuration.
    
    Args:
        config_path: Path to the configuration file (optional)
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        # Use default config path if not specified
        project_root = Path(__file__).parents[2]  # Go up 2 levels from utils/
        config_path = os.path.join(project_root, "config", "config.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Process environment variables in connection string
    if "database" in config and "connection_string" in config["database"]:
        conn_str = config["database"]["connection_string"]
        
        # Handle ${VAR:-default} format
        if conn_str.startswith("${") and ":-" in conn_str:
            # Extract default value
            default_value = conn_str.split(":-")[1].rstrip("}")
            # Get from environment or use default
            actual_conn_str = os.environ.get("DB_CONNECTION_STRING", default_value)
            config["database"]["connection_string"] = actual_conn_str
        elif conn_str.startswith("${"):
            # Just a variable without default
            var_name = conn_str[2:-1]  # Remove ${ at start and } at end
            config["database"]["connection_string"] = os.environ.get(var_name, "postgresql://postgres:Swoop123!@127.0.0.1:5433/byrdi")
    
    # Set API keys
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        # Ensure the API key is set in all relevant places
        if "api" in config and "openai" in config["api"]:
            config["api"]["openai"]["api_key"] = openai_api_key
        
        # Also set it in services section if needed
        if "services" in config and "sql_generator" in config["services"]:
            config["services"]["sql_generator"]["openai_api_key"] = openai_api_key
    
    # Set other API keys
    elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
    if elevenlabs_api_key and "api" in config and "elevenlabs" in config["api"]:
        config["api"]["elevenlabs"]["api_key"] = elevenlabs_api_key
    
    # Override with testing settings
    config["testing"] = {
        "provide_fallback_responses": True,
        "generate_critiques": True,
        "sql_schema_validation": True,
        "detect_empty_sql": True,
        "use_real_services": True
    }
    
    return config 