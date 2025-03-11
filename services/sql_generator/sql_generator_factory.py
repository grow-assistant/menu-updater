"""
Factory for creating SQL generator instances based on configuration.
"""
import os
import logging
from typing import Dict, Any

from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
from services.sql_generator.openai_sql_generator import OpenAISQLGenerator

logger = logging.getLogger(__name__)

class SQLGeneratorFactory:
    """Factory for creating SQL generator instances."""
    
    @staticmethod
    def create_sql_generator(config: Dict[str, Any]):
        """
        Create a SQL generator instance based on configuration and environment.
        
        Args:
            config: Application configuration
            
        Returns:
            A SQL generator instance (OpenAI or Gemini)
        """
        # Validate configuration
        if not config:
            logger.error("No configuration provided to SQL generator factory")
            config = {"api": {"openai": {"api_key": os.environ.get("OPENAI_API_KEY", "")}}}
            logger.info("Using fallback configuration with environment variables")
            
        # Get the SQL generator type from environment variable or use default
        generator_type = os.environ.get("SQL_GENERATOR_TYPE", "openai")
        
        # Clean up the value - strip whitespace and remove any comments
        if generator_type and "#" in generator_type:
            generator_type = generator_type.split("#")[0].strip()
        else:
            generator_type = generator_type.strip()
            
        generator_type = generator_type.lower()
        
        logger.info(f"Creating SQL generator of type: {generator_type}")
        
        # Make sure the configuration has the necessary sections
        if "api" not in config:
            config["api"] = {}
        
        # Setup OpenAI configuration if needed
        if generator_type == "openai" and "openai" not in config["api"]:
            logger.warning("OpenAI configuration not found in config, using environment variables")
            config["api"]["openai"] = {
                "api_key": os.environ.get("OPENAI_API_KEY", ""),
                "model": os.environ.get("DEFAULT_MODEL", "gpt-4o-mini"),
                "temperature": float(os.environ.get("DEFAULT_TEMPERATURE", "0.2")),
                "max_tokens": 2000
            }
            
        # Setup Gemini configuration if needed
        if generator_type == "gemini" and "gemini" not in config["api"]:
            logger.warning("Gemini configuration not found in config, using environment variables")
            config["api"]["gemini"] = {
                "api_key": os.environ.get("GOOGLE_API_KEY", ""),
                "model": os.environ.get("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash"),
                "temperature": float(os.environ.get("DEFAULT_TEMPERATURE", "0.2")),
                "max_tokens": 2000
            }
            
        # Add services section if missing
        if "services" not in config:
            config["services"] = {}
            
        # Add sql_generator section if missing
        if "sql_generator" not in config["services"]:
            config["services"]["sql_generator"] = {
                "max_retries": 2,
                "prompt_cache_ttl": 300,
                "enable_detailed_logging": False
            }
        
        # Create the appropriate generator    
        try:
            if generator_type == "openai":
                logger.info("Using OpenAI for SQL generation.")
                return OpenAISQLGenerator(config)
            elif generator_type == "gemini":
                logger.info("Using Gemini for SQL generation.")
                # In test environments, we set skip_verification to True and pass None for db_service
                # This allows us to test without a real database connection
                return GeminiSQLGenerator(config, db_service=None, skip_verification=True)
            else:
                logger.warning(f"Unknown SQL generator type: {generator_type}. Defaulting to OpenAI.")
                return OpenAISQLGenerator(config)
        except Exception as e:
            logger.error(f"Error creating SQL generator: {str(e)}")
            logger.warning("Falling back to OpenAI SQL generator with default configuration")
            default_config = {
                "api": {
                    "openai": {
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "model": "gpt-4o-mini",
                        "temperature": 0.2,
                        "max_tokens": 2000
                    }
                },
                "services": {
                    "sql_generator": {
                        "max_retries": 2,
                        "prompt_cache_ttl": 300,
                        "enable_detailed_logging": True
                    }
                }
            }
            return OpenAISQLGenerator(default_config) 