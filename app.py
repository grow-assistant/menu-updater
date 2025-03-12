"""
Restaurant Assistant Application

This is the main entry point for the restaurant assistant application.
"""
import os
import logging
import yaml
import argparse
from typing import Dict, Any

from services.utils.service_initializer import initialize_services, health_check
from services.utils.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

def setup_logging():
    """Set up application logging."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "restaurant_assistant.log")),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Logging initialized")

def load_config() -> Dict[str, Any]:
    """
    Load application configuration from file.
    
    Returns:
        Configuration dictionary
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.yaml")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Substitute environment variables in the config
        config = replace_env_vars(config)
        
        logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        # Return a minimal default configuration
        return {
            "application": {
                "name": "Restaurant Assistant",
                "version": "1.0.0",
                "environment": "development"
            }
        }

def replace_env_vars(obj):
    """
    Recursively replace environment variable references in a configuration object.
    
    Args:
        obj: Configuration object (dict, list, or scalar value)
        
    Returns:
        Configuration with environment variables replaced
    """
    if isinstance(obj, dict):
        return {k: replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_env_vars(i) for i in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        # Extract environment variable name
        env_var = obj[2:-1]
        # Get the value with an optional default after :
        if ":" in env_var:
            env_name, default = env_var.split(":", 1)
            return os.environ.get(env_name, default)
        else:
            # Return the value or the original string if not found
            return os.environ.get(env_var, obj)
    else:
        return obj

def create_app(config):
    """
    Create and configure the application.
    
    Args:
        config: Application configuration
        
    Returns:
        Configured application
    """
    logger.info("Creating application")
    
    # Initialize services
    logger.info("Initializing services")
    initialized_services = initialize_services(config)
    
    if "sql_validation" in initialized_services:
        logger.info("SQL Validation service initialized successfully")
    else:
        logger.warning("SQL Validation service not initialized")
    
    # Create application object (this would be your Flask app, FastAPI app, etc.)
    # For this example, we'll just create a simple object with references to services
    app = type("Application", (), {
        "config": config,
        "service_registry": ServiceRegistry,
        "health_check": health_check
    })
    
    logger.info("Application created successfully")
    return app

def main():
    """
    Main entry point for the application.
    """
    # Set up logging
    setup_logging()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Restaurant Assistant")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Override with command-line arguments
    if args.debug:
        config["application"]["debug"] = True
    
    # Create the application
    app = create_app(config)
    
    # Start the application (this would start your web server, etc.)
    # For this example, we'll just print a message
    logger.info("Restaurant Assistant is ready")
    logger.info(f"Application version: {config['application']['version']}")
    
    # Check health of services
    health_status = app.health_check()
    logger.info(f"Service health: {health_status}")
    
    # Return the app for testing purposes
    return app

if __name__ == "__main__":
    main() 