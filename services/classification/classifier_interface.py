"""
Query Classifier Interface for the Classification Service.

This module provides a common interface for classifying queries, abstracting away
the underlying implementation details.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import asyncio

# Updated imports to use the new structure
from services.classification.classifier import ClassificationService
from services.classification.prompt_builder import classification_prompt_builder

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

class QueryClassifierInterface:
    """
    A class that provides a common interface for classifying queries.
    """
    
    def __init__(self):
        """Initialize the Query Classifier Interface."""
        self._classifier = ClassificationService()
        self._prompt_builder = classification_prompt_builder
        logger.info("QueryClassifierInterface initialized")
    
    def classify_query(
        self, 
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Classify a query into one of the supported query types.
        
        Args:
            query: The user's query
            model: Model to use for classification (defaults to configured default)
            temperature: Temperature for generation (defaults to configured default)
            use_cache: Whether to use cached classifications
            
        Returns:
            Dictionary with classification results
        """
        try:
            result = self._classifier.classify_query(
                query=query
            )
            
            return result
        except Exception as e:
            logger.error(f"Error classifying query: {str(e)}")
            # Return a fallback result
            return {
                "query": query,
                "query_type": "general",
                "confidence": 0.1,
                "error": str(e)
            }
    
    async def classify_query_async(
        self, 
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Asynchronously classify a query into one of the supported query types.
        
        Args:
            query: The user's query
            model: Model to use for classification (defaults to configured default)
            temperature: Temperature for generation (defaults to configured default)
            use_cache: Whether to use cached classifications
            
        Returns:
            Dictionary with classification results
        """
        # Running synchronously for now, could be implemented properly later
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.classify_query(query, model, temperature, use_cache)
            )
            return result
        except Exception as e:
            logger.error(f"Error classifying query asynchronously: {str(e)}")
            # Return a fallback result
            return {
                "query": query,
                "query_type": "general",
                "confidence": 0.1,
                "error": str(e)
            }
    
    def get_supported_query_types(self) -> List[str]:
        """
        Get a list of all supported query types.
        
        Returns:
            List of query type names
        """
        return self._prompt_builder.get_available_query_types()
    
    def is_supported_query_type(self, query_type: str) -> bool:
        """
        Check if a query type is supported.
        
        Args:
            query_type: Query type to check
            
        Returns:
            True if the query type is valid, False otherwise
        """
        return self._prompt_builder.is_valid_query_type(query_type)
    
    def clear_cache(self) -> None:
        """Clear the classification cache."""
        # Implement if caching is added
        pass


# Singleton instance
classifier_interface = QueryClassifierInterface() 