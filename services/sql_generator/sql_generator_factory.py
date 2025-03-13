"""
Factory for creating SQL generator instances based on configuration.
"""
import os
import logging
from typing import Dict, Any, Optional

from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
from services.sql_generator.openai_sql_generator import OpenAISQLGenerator

logger = logging.getLogger(__name__)

class SQLGeneratorFactory:
    """Factory class for creating SQL generator instances."""
    
    @classmethod
    def create_sql_generator(cls, config: Dict[str, Any]) -> Any:
        """
        Create an instance of the specified SQL generator.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            SQLGenerator instance
        """
        # Get the generator type from config
        generator_type = config.get("services", {}).get("sql_generator", {}).get("type", "openai").lower()
        
        # Log the generator type being created
        logger.info(f"Creating SQL generator of type: {generator_type}")
        
        # Create the appropriate generator instance
        if generator_type == "openai":
            from services.sql_generator.openai_sql_generator import OpenAISQLGenerator
            logger.info("Using OpenAI for SQL generation.")
            return SQLGeneratorAdapter(OpenAISQLGenerator(config))
        elif generator_type == "gemini":
            from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
            logger.info("Using Gemini for SQL generation.")
            return SQLGeneratorAdapter(GeminiSQLGenerator(config))
        elif generator_type == "mock":
            from services.sql_generator.mock_sql_generator import MockSQLGenerator
            logger.info("Using Mock SQL generator for testing.")
            return SQLGeneratorAdapter(MockSQLGenerator(config))
        else:
            # Default to OpenAI if type is not recognized
            from services.sql_generator.openai_sql_generator import OpenAISQLGenerator
            logger.warning(f"Unknown generator type '{generator_type}', defaulting to OpenAI")
            return SQLGeneratorAdapter(OpenAISQLGenerator(config))


class SQLGeneratorAdapter:
    """Adapter class to maintain compatibility between different SQL generator interfaces."""
    
    def __init__(self, generator):
        """
        Initialize the adapter with an SQL generator.
        
        Args:
            generator: The SQL generator instance to adapt
        """
        self.generator = generator
    
    def generate(self, query: str, category: str, rules_and_examples: Dict[str, Any], 
                 additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Adapt the old interface to the new interface.
        
        Args:
            query: The user's natural language query
            category: The query category as determined by the classifier
            rules_and_examples: Dictionary containing rules and examples for this query type
            additional_context: Optional additional context like previous SQL queries
            
        Returns:
            Dictionary with generated SQL and metadata
        """
        # Check if the generator has the new signature
        if hasattr(self.generator, 'generate') and callable(self.generator.generate):
            try:
                # Try calling with the new signature
                context = additional_context or {}
                
                # Add rules_and_examples as rules to maintain compatibility
                rules = rules_and_examples.get("query_rules", {})
                
                return self.generator.generate(query, category, rules, context)
            except TypeError:
                # Fall back to old signature if the new one fails
                if hasattr(self.generator, 'generate_sql') and callable(self.generator.generate_sql):
                    # Extract examples from rules_and_examples
                    examples = rules_and_examples.get("sql_examples", rules_and_examples.get("examples", []))
                    
                    # Create context dictionary from category and rules
                    context = {
                        "query_type": category,
                        "rules": rules_and_examples.get("query_rules", {})
                    }
                    
                    # Add additional context if provided
                    if additional_context:
                        context.update(additional_context)
                    
                    return self.generator.generate_sql(query, examples, context)
                else:
                    # If no compatible methods found, return an error
                    return {"sql": None, "success": False, "error": "SQL generator interface not compatible"}
        else:
            # No generate method, try generate_sql
            if hasattr(self.generator, 'generate_sql') and callable(self.generator.generate_sql):
                # Extract examples from rules_and_examples
                examples = rules_and_examples.get("sql_examples", rules_and_examples.get("examples", []))
                
                # Create context dictionary from category and rules
                context = {
                    "query_type": category,
                    "rules": rules_and_examples.get("query_rules", {})
                }
                
                # Add additional context if provided
                if additional_context:
                    context.update(additional_context)
                
                return self.generator.generate_sql(query, examples, context)
            else:
                # If no compatible methods found, return an error
                return {"sql": None, "success": False, "error": "SQL generator interface not compatible"} 