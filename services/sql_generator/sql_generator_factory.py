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
        # Get the SQL generator type from environment variable or use default
        generator_type = os.environ.get("SQL_GENERATOR_TYPE", "openai")
        
        # Clean up the value - strip whitespace and remove any comments
        if generator_type and "#" in generator_type:
            generator_type = generator_type.split("#")[0].strip()
        else:
            generator_type = generator_type.strip()
            
        generator_type = generator_type.lower()
        
        logger.info(f"Creating SQL generator of type: {generator_type}")
        
        if generator_type == "openai":
            logger.info("Using OpenAI for SQL generation.")
            return OpenAISQLGenerator(config)
        elif generator_type == "gemini":
            logger.info("Using Gemini for SQL generation.")
            return GeminiSQLGenerator(config)
        else:
            logger.warning(f"Unknown SQL generator type: {generator_type}. Defaulting to OpenAI.")
            return OpenAISQLGenerator(config) 