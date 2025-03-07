"""
Service for classifying user queries using OpenAI GPT-4.
"""
import logging
import openai
import json
import time
from typing import Dict, Any, List, Optional, Union
import asyncio
import re

from services.classification.prompt_builder import ClassificationPromptBuilder, classification_prompt_builder

logger = logging.getLogger(__name__)

class ClassificationService:
    def __init__(self, config: Optional[Dict[str, Any]] = None, ai_client=None):
        """Initialize the classification service."""
        self.config = config or {}
        self.ai_client = ai_client
        
        # OpenAI configuration (can be made more flexible)
        self.api_key = self.config.get("api", {}).get("openai", {}).get("api_key")
        self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")
        
        # Initialize categories from the prompt builder
        self.prompt_builder = classification_prompt_builder
        self.categories = self.prompt_builder.get_available_query_types()
        
        # Classification cache
        self._classification_cache = {}
        
        # Set OpenAI API key if provided
        if self.api_key:
            openai.api_key = self.api_key
    
    def classify(self, query: str, cached_dates=None, use_cache=True) -> Dict[str, Any]:
        """
        Classify the user query into a category.
        This method is a wrapper around classify_query to maintain compatibility 
        with the OrchestratorService which calls this method.
        
        Args:
            query: The user's query text
            cached_dates: Optional date information for context
            use_cache: Whether to use cached classifications
            
        Returns:
            Dictionary with classification results in the format expected by the orchestrator
        """
        logger.debug(f"Classifying query via classify method: '{query}'")
        
        # Call the actual implementation method
        result = self.classify_query(query, cached_dates, use_cache)
        
        # Transform the output to match what the orchestrator expects
        return {
            "category": result.get("query_type", "general_question"),
            "confidence": result.get("confidence", 0.0),
            "skip_database": result.get("skip_database", False)
        }
    
    def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            # Simple API check
            if self.api_key:
                openai.models.list()
                return True
            return False
        except Exception as e:
            logger.error(f"OpenAI API health check failed: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Clear the classification cache."""
        self._classification_cache = {}
    
    def _normalize_query(self, query: str) -> str:
        """Normalize the query for caching purposes."""
        return query.strip().lower()
    
    def _check_query_cache(self, query: str, use_cache: bool) -> Optional[Dict[str, Any]]:
        """Check if the query result is in cache."""
        if not use_cache:
            return None
        
        normalized_query = self._normalize_query(query)
        return self._classification_cache.get(normalized_query)
    
    def classify_query(self, query: str, cached_dates=None, use_cache=True) -> Dict[str, Any]:
        """
        Classify the user query into one of the predefined categories.
        
        Args:
            query: The user's query text
            cached_dates: Optional date information for context
            use_cache: Whether to use cached classifications
            
        Returns:
            Dictionary with classification results
        """
        start_time = time.time()
        
        # Check cache first
        cached_result = self._check_query_cache(query, use_cache)
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
        
        try:
            # First try keyword-based classification for efficiency
            keyword_result = self._classify_by_keywords(query)
            if keyword_result.get("confidence", 0) > 0.8:
                # High confidence keyword match
                keyword_result["classification_method"] = "keyword"
                return keyword_result
            
            # Create a prompt for classification
            prompt = self.prompt_builder.build_classification_prompt(query, cached_dates)
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                temperature=0.2,
                max_tokens=50
            )
            
            # Parse the response
            result = self.parse_classification_response(response, query)
            
            # Add metadata
            result["query"] = query
            result["time_elapsed"] = time.time() - start_time
            result["from_cache"] = False
            result["classification_method"] = "ai"
            
            # Cache the result
            if use_cache:
                normalized_query = self._normalize_query(query)
                self._classification_cache[normalized_query] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error in classification: {str(e)}")
            return self._fallback_classification(query)
    
    def _classify_by_keywords(self, query: str) -> Dict[str, Any]:
        """Classify query using keyword matching."""
        normalized_query = self._normalize_query(query)
        
        # Simple keyword mapping for common query types
        keyword_maps = {
            "order_history": ["order history", "past orders", "order list", "transaction history", "purchase history"],
            "trend_analysis": ["trend", "analysis", "pattern", "over time", "growth", "decline", "seasonal"],
            "popular_items": ["popular", "bestseller", "most ordered", "top selling", "favorite", "best performing"],
            "order_ratings": ["rating", "review", "feedback", "satisfaction", "stars", "score"],
            "menu_inquiry": ["menu", "item", "dish", "food", "category", "price", "availability"]
        }
        
        highest_confidence = 0.0
        matched_type = "general_question"  # Default
        
        for query_type, keywords in keyword_maps.items():
            for keyword in keywords:
                if keyword in normalized_query:
                    confidence = 0.7 + (len(keyword) / len(normalized_query) * 0.3)
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        matched_type = query_type
        
        return {
            "query": normalized_query,
            "query_type": matched_type,
            "confidence": highest_confidence,
            "time_elapsed": 0.0,
            "from_cache": False
        }
    
    def parse_classification_response(self, response: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Parse the classification response from the API."""
        try:
            # Extract the category from response
            category = response.choices[0].message.content.strip().lower()
            
            # Check if the response contains a valid category
            if category in self.categories:
                return {
                    "query_type": category,
                    "confidence": 0.9,  # AI classification is generally high confidence
                }
            else:
                # Try to extract a category if response isn't exactly a category name
                for valid_category in self.categories:
                    if valid_category in category:
                        return {
                            "query_type": valid_category,
                            "confidence": 0.7,  # Lower confidence for partial matches
                        }
                
                logger.warning(f"Invalid category returned: {category}. Defaulting to 'general_question'.")
                return {"query_type": "general_question", "confidence": 0.5}
        except Exception as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            return self._fallback_classification(query)
    
    def _fallback_classification(self, query: str) -> Dict[str, Any]:
        """Provide a fallback classification when other methods fail."""
        return {
            "query": query,
            "query_type": "general_question",
            "confidence": 0.3,
            "time_elapsed": 0.0,
            "from_cache": False,
            "classification_method": "fallback",
            "error": "Classification failed, using fallback"
        }
    
    async def classify_query_async(self, query: str, cached_dates=None, use_cache=True) -> Dict[str, Any]:
        """Asynchronous version of classify_query."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.classify_query(query, cached_dates, use_cache)
        )
        return result 