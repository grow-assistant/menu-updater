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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Query Classifier Interface.
        
        Args:
            config: Optional configuration dictionary
        """
        self._classifier = ClassificationService(config=config)
        self._prompt_builder = classification_prompt_builder
        # Initialize with database schema information
        self._init_database_schema()
        logger.info("QueryClassifierInterface initialized")
    
    def _init_database_schema(self) -> None:
        """Initialize database schema information for the classifier."""
        # Updated database schema in sync with resources/database_fields.md
        self.db_schema = {
            "orders": [
                "id", "created_at", "updated_at", "deleted_at", "customer_id", "vendor_id",
                "location_id", "status", "total", "tax", "instructions", "type", "marker_id",
                "fee", "loyalty_id", "fee_percent", "tip"
            ],
            "order_items": [
                "id", "created_at", "updated_at", "deleted_at", "item_id", "quantity",
                "order_id", "instructions"
            ],
            "items": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "price", "category_id", "disabled", "seq_num"
            ],
            "categories": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "menu_id", "disabled", "start_time", "end_time", "seq_num"
            ],
            "menus": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "location_id", "disabled"
            ],
            "options": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "min", "max", "item_id", "disabled"
            ],
            "option_items": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "price", "option_id", "disabled"
            ],
            "locations": [
                "id", "created_at", "updated_at", "deleted_at", "name", "description",
                "timezone", "latitude", "longitude", "active", "disabled", "code", "tax_rate", "settings"
            ],
            "users": [
                "id", "created_at", "updated_at", "deleted_at", "first_name", "last_name",
                "email", "picture", "phone"
            ]
        }
        # Provide schema to classifier and prompt builder
        self._classifier.set_database_schema(self.db_schema)
        self._prompt_builder.set_database_schema(self.db_schema)
    
    def classify_query(
        self, 
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify a query into one of the supported query types.
        
        Args:
            query: The user's query
            model: Model to use for classification (defaults to configured default)
            temperature: Temperature for generation (defaults to configured default)
            use_cache: Whether to use cached classifications
            conversation_context: Optional conversation context for improved classification
            
        Returns:
            Dictionary with classification results
        """
        try:
            # Use context if provided for better classification
            if conversation_context:
                result = self._classifier.get_classification_with_context(
                    query=query,
                    conversation_context=conversation_context
                )
            else:
                result = self._classifier.classify_query(
                    query=query,
                    use_cache=use_cache
                )
            
            return result
        except Exception as e:
            logger.error(f"Error classifying query: {str(e)}")
            # Return a fallback result
            return {
                "query": query,
                "query_type": "general",
                "confidence": 0.1,
                "parameters": {},
                "error": str(e),
                "needs_clarification": True
            }
    
    async def classify_query_async(
        self, 
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously classify a query into one of the supported query types.
        
        Args:
            query: The user's query
            model: Model to use for classification (defaults to configured default)
            temperature: Temperature for generation (defaults to configured default)
            use_cache: Whether to use cached classifications
            conversation_context: Optional conversation context for improved classification
            
        Returns:
            Dictionary with classification results
        """
        # Running synchronously for now, could be implemented properly later
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.classify_query(query, model, temperature, use_cache, conversation_context)
            )
            return result
        except Exception as e:
            logger.error(f"Error classifying query asynchronously: {str(e)}")
            # Return a fallback result
            return {
                "query": query,
                "query_type": "general",
                "confidence": 0.1,
                "parameters": {},
                "error": str(e),
                "needs_clarification": True
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
        self._classifier.clear_cache()

    def get_database_schema(self) -> Dict[str, List[str]]:
        """
        Get the database schema information.
        
        Returns:
            Dictionary mapping table names to their fields
        """
        return self.db_schema


# Singleton instance
classifier_interface = QueryClassifierInterface() 