"""
Configuration settings for the Swoop AI application.

This module contains configuration settings and environment variables
used throughout the application.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration class for the Swoop AI application."""
    
    _instance = None
    _config_data = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        
        try:
            with open(config_path, "r") as f:
                self._config_data = yaml.safe_load(f)
            
            # Replace environment variable placeholders
            self._process_env_vars(self._config_data)
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Fallback to empty config
            self._config_data = {}
    
    def _process_env_vars(self, config_dict):
        """
        Recursively process configuration dictionary and replace ${ENV_VAR} with
        the corresponding environment variable value.
        """
        if not isinstance(config_dict, dict):
            return
            
        for key, value in config_dict.items():
            if isinstance(value, dict):
                self._process_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value is not None:
                    config_dict[key] = env_value
                    
                    # Convert to appropriate type if needed
                    if env_value.lower() in ("true", "false"):
                        config_dict[key] = env_value.lower() == "true"
                    elif env_value.isdigit():
                        config_dict[key] = int(env_value)
                    elif env_value.replace(".", "", 1).isdigit() and env_value.count(".") == 1:
                        config_dict[key] = float(env_value)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., "database.host")
            default: Default value to return if the key is not found
            
        Returns:
            The configuration value or the default value if not found
        """
        if not self._config_data:
            return default
            
        current = self._config_data
        for key in key_path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_all(self) -> Dict:
        """
        Get the entire configuration dictionary.
        
        Returns:
            Dict: The configuration dictionary
        """
        return self._config_data or {}


# Create a singleton instance
config = Config()

# Export the config instance
__all__ = ["config"]
