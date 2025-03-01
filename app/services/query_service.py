"""
Query Service module.

This module provides services for categorizing and processing user queries,
integrating with LLMs, and generating appropriate responses.
"""

import os
import json
import logging
import datetime
import re
from typing import Dict, List, Any, Optional, Tuple, Union

# Get the logger
logger = logging.getLogger("ai_menu_updater")

class QueryService:
    """
    Service for categorizing and processing user queries.
    
    This service centralizes query categorization and processing,
    integrating with the OpenAI API and LangChain for query handling.
    """
    
    def __init__(self):
        """Initialize the QueryService."""
        logger.info("Initializing QueryService")
        
        # Import query-related modules
        try:
            import openai
            from app.services.prompt_service import prompt_service
            
            # Store references
            self._openai_client = openai
            self._prompt_service = prompt_service
            
            # Load API key from environment
            from config.settings import OPENAI_API_KEY
            if OPENAI_API_KEY:
                self._openai_client.api_key = OPENAI_API_KEY
                logger.info("OpenAI API key loaded")
            else:
                logger.warning("OpenAI API key not found in environment")
                
            logger.info("Successfully configured QueryService")
        except ImportError as e:
            logger.error(f"Error importing query service dependencies: {str(e)}")
            raise
    
    def categorize_query(self, query: str, openai_client=None) -> Dict[str, Any]:
        """
        Categorize a user query to determine the appropriate path.
        
        Args:
            query: User query to categorize
            openai_client: Optional OpenAI client (for testing)
            
        Returns:
            Dictionary with categorization results including request_type and other parameters
        """
        logger.info(f"Categorizing query: {query}")
        
        if not query.strip():
            logger.warning("Empty query received, returning default categorization")
            return {"request_type": "unknown"}
        
        # Use provided client or default
        client = openai_client or self._openai_client
        
        try:
            # Get the categorization prompt
            categorization_prompt = self._prompt_service.create_query_categorization_prompt(
                user_query=query
            )
            
            # Log prompt for debugging
            logger.debug(f"Using categorization prompt: {categorization_prompt[:100]}...")
            
            # Call OpenAI for categorization
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[{"role": "user", "content": categorization_prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            # Extract and parse the response
            result_content = response.choices[0].message.content
            logger.debug(f"Raw categorization response: {result_content}")
            
            # Extract JSON from response text
            pattern = r'```json\s*(.*?)\s*```'
            match = re.search(pattern, result_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                result = json.loads(json_str)
            else:
                # Try to load the entire response as JSON
                try:
                    result = json.loads(result_content)
                except json.JSONDecodeError:
                    logger.error("Could not parse JSON from categorization response")
                    result = {"request_type": "unknown"}
            
            # Ensure all expected fields have default values
            # Default all potential fields that might not be included
            defaults = {
                "time_period": None,
                "item_name": None,
                "new_price": None,
                "start_date": None,
                "end_date": None
            }
            
            # Merge with defaults
            full_result = {**defaults, **result}
            logger.info(f"Categorization result: {result}")
            
            return full_result
            
        except Exception as e:
            logger.error(f"Error during query categorization: {str(e)}")
            # Return a basic response on error
            return {"request_type": "unknown"}
    
    def process_query_with_path(
        self, 
        query: str, 
        query_category: Dict[str, Any],
        location_id: int = 62
    ) -> Dict[str, Any]:
        """
        Process a query using the appropriate query path based on categorization.
        
        Args:
            query: Original user query
            query_category: Categorization result from categorize_query
            location_id: Location ID to use for filtering
            
        Returns:
            Dictionary with processing results including SQL and verbal responses
        """
        logger.info(f"Processing query with category: {query_category.get('request_type', 'unknown')}")
        
        # Import query path module here to avoid circular imports
        try:
            from query_paths import get_query_path
            query_path_factory = get_query_path(query_category.get('request_type', 'unknown'))
            
            if query_path_factory:
                query_path = query_path_factory(location_id=location_id)
                result = query_path.process(query, query_category)
                logger.info(f"Query processing successful: {result.get('success', False)}")
                return result
            else:
                logger.warning(f"No query path found for type: {query_category.get('request_type', 'unknown')}")
                return {
                    "success": False,
                    "verbal_answer": "I'm not sure how to process that type of request.",
                    "text_answer": "Unknown query type",
                    "sql_query": ""
                }
        except Exception as e:
            logger.error(f"Error processing query with path: {str(e)}")
            return {
                "success": False,
                "verbal_answer": "Sorry, I encountered an error processing your request.",
                "text_answer": f"Error: {str(e)}",
                "sql_query": ""
            }


# Create a singleton instance
query_service = QueryService() 