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
from openai import OpenAI

from services.classification.prompt_builder import ClassificationPromptBuilder, classification_prompt_builder
from services.utils.logging import log_openai_request, log_openai_response

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
        
        # Track the last classification result for context
        self._last_classification = None
        
        # Initialize OpenAI client if API key is provided
        if self.api_key:
            # Use the newer client-based approach instead of setting API key directly
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized for classification service")
        else:
            self.client = None
            logger.warning("OpenAI API key not provided for classification service")
    
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
        
        # Call the actual implementation method with previous classification context
        result = self.classify_query(query, cached_dates, use_cache)
        
        # Store this classification for future context
        self._last_classification = result.copy()
        
        # Transform the output to match what the orchestrator expects
        return {
            "category": result.get("query_type", "general_question"),
            "confidence": result.get("confidence", 0.0),
            "skip_database": result.get("skip_database", False),
            "time_period_clause": result.get("time_period_clause", None),
            "is_followup": result.get("is_followup", False)
        }
    
    def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            # Use the client-based approach for health check
            if self.client:
                self.client.models.list()
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
        # Remove extra whitespace, lowercase
        return re.sub(r'\s+', ' ', query.lower().strip())
    
    def _check_query_cache(self, query: str, use_cache: bool) -> Optional[Dict[str, Any]]:
        """Check if query is in cache."""
        if not use_cache:
            return None
            
        normalized_query = self._normalize_query(query)
        return self._classification_cache.get(normalized_query)
    
    def _fallback_classification(self, query: str) -> Dict[str, Any]:
        """Provide a fallback classification when API calls fail."""
        # If we have previous classification and this looks like a followup,
        # use the previous query type instead of defaulting to general_question
        if self._last_classification and any(token in query.lower() for token in ["those", "them", "that", "these"]):
            # This might be a followup question based on simple heuristics
            return {
                "query": query,
                "query_type": self._last_classification.get("query_type", "general_question"),
                "confidence": 0.4,
                "time_elapsed": 0.0,
                "from_cache": False,
                "classification_method": "fallback_with_context",
                "time_period_clause": self._last_classification.get("time_period_clause"),
                "is_followup": True
            }
        else:
            return {
                "query": query,
                "query_type": "general_question",  # Default fallback
                "confidence": 0.1,
                "time_elapsed": 0.0,
                "from_cache": False,
                "classification_method": "fallback",
                "time_period_clause": None,
                "is_followup": False
            }
    
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
            # Create a prompt for classification
            prompt = self.prompt_builder.build_classification_prompt(query, cached_dates)
            
            # Log the OpenAI request
            log_openai_request(
                prompt=f"System: {prompt['system']}\nUser: {prompt['user']}",
                parameters={
                    "model": self.model,
                    "temperature": 0.2,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"}
                }
            )
            
            # Use the client-based approach instead of the deprecated module approach
            if not self.client:
                logger.error("OpenAI client not initialized. Using fallback classification.")
                return self._fallback_classification(query)
                
            # Call OpenAI API using the client
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            # Log the OpenAI response
            log_openai_response(
                response=response,
                processing_time=time.time() - start_time
            )
            
            # Parse the response
            result = self.parse_classification_response(response, query)
            
            # Check if this is a followup question based on LLM's determination
            if result.get("is_followup", False) and self._last_classification:
                # Use the previous query type and timeframe for followup questions
                result["query_type"] = self._last_classification.get("query_type", result["query_type"])
                
                # For time-related information, keep the previous context if relevant
                if not result.get("time_period_clause"):
                    result["time_period_clause"] = self._last_classification.get("time_period_clause")
                
                # Increase confidence for followup classification
                result["confidence"] = max(result["confidence"], 0.85)
            
            # Ensure order_history queries always have a proper time_period_clause
            if result["query_type"] == "order_history" and not result.get("time_period_clause"):
                # Generate a default time period clause for last month
                from datetime import datetime, timedelta
                
                today = datetime.now()
                # First day of previous month
                first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                # Last day of previous month
                last_day = today.replace(day=1) - timedelta(days=1)
                
                # Create a BETWEEN clause with the dates
                result["time_period_clause"] = f"WHERE updated_at BETWEEN '{first_day.strftime('%Y-%m-%d')}' AND '{last_day.strftime('%Y-%m-%d')}'"
            
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
    
    def parse_classification_response(self, response: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Parse the response from the OpenAI classification API.
        
        Args:
            response: The API response
            query: The original query
            
        Returns:
            Dictionary with parsed classification results
        """
        result = {
            "query": query,
            "classification_method": "openai",
            "query_type": "general_question", # Default to general_question
            "confidence": 0.0,
            "skip_database": False,
            "time_period_clause": None,
            "is_followup": False
        }
        
        try:
            # Get the content from the response based on the API version
            if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
                # This is a response from the client-based API (newer)
                message_content = response.choices[0].message.content
            elif isinstance(response, dict) and 'choices' in response:
                # This is a response from the module-based API (older) or mocked
                message_content = response['choices'][0]['message']['content']
            else:
                logger.error(f"Unexpected response format: {response}")
                return result
                
            # Parse the JSON
            classification_data = json.loads(message_content)
            
            # Extract category and validate it
            if "query_type" in classification_data:
                query_type = classification_data["query_type"]
                # Check if the query_type is valid (in the available categories)
                if query_type in self.categories:
                    result["query_type"] = query_type
                else:
                    # If invalid category, use the default
                    result["query_type"] = "general_question"
                    logger.warning(f"Invalid category received: {query_type}. Using general_question instead.")
                
                result["confidence"] = 0.9  # High confidence for direct classification
                
            # Extract time period clause
            if "time_period_clause" in classification_data:
                result["time_period_clause"] = classification_data["time_period_clause"]
                
            # Extract date information for order history
            if result["query_type"] == "order_history":
                if "start_date" in classification_data:
                    result["start_date"] = classification_data.get("start_date")
                if "end_date" in classification_data:
                    result["end_date"] = classification_data.get("end_date")
                    
            # Extract followup information
            if "is_followup" in classification_data:
                result["is_followup"] = classification_data["is_followup"]
                
            return result
        except Exception as e:
            logger.error(f"Error parsing classification response: {e}")
            logger.error(f"Response: {response}")
            return result
    
    async def classify_query_async(self, query: str, cached_dates=None, use_cache=True) -> Dict[str, Any]:
        """Asynchronous version of classify_query."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.classify_query(query, cached_dates, use_cache)
        )
        return result 