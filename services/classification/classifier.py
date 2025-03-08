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
            "skip_database": result.get("skip_database", False),
            "time_period_clause": result.get("time_period_clause", None),  # Add time period clause to response
            "is_followup": result.get("is_followup", False)  # Add follow-up question indicator
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
        return {
            "query": query,
            "query_type": "general_question",  # Default fallback
            "confidence": 0.1,
            "time_elapsed": 0.0,
            "from_cache": False,
            "classification_method": "fallback",
            "time_period_clause": None,  # Default empty time period clause
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
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                temperature=0.2,
                max_tokens=300,  # Increased token limit to accommodate time period clause extraction
                response_format={"type": "json_object"}  # Request JSON format for structured output
            )
            
            # Log the OpenAI response
            log_openai_response(
                response=response,
                processing_time=time.time() - start_time
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
    
    def parse_classification_response(self, response: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Parse the classification response from the API."""
        try:
            # Extract the content from response
            content = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                parsed_json = json.loads(content)
                query_type = parsed_json.get("query_type", "").strip().lower()
                time_period_clause = parsed_json.get("time_period_clause", None)
                is_followup = parsed_json.get("is_followup", False)
                
                # Validate query type
                if query_type in self.categories:
                    return {
                        "query_type": query_type,
                        "confidence": 0.9,
                        "time_period_clause": time_period_clause,
                        "is_followup": is_followup
                    }
            except json.JSONDecodeError:
                # Fall back to text parsing if JSON parsing fails
                content_lower = content.lower()
                
                # Default to empty time period clause
                time_period_clause = None
                is_followup = "follow-up" in content_lower or "followup" in content_lower
                
                # Check if the content contains a valid category
                for valid_category in self.categories:
                    if valid_category in content_lower:
                        return {
                            "query_type": valid_category,
                            "confidence": 0.8,
                            "time_period_clause": time_period_clause,
                            "is_followup": is_followup
                        }
            
            # No valid category found
            return {
                "query_type": "general_question",
                "confidence": 0.5,
                "time_period_clause": None,
                "is_followup": False
            }
        
        except Exception as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            return {
                "query_type": "general_question",
                "confidence": 0.1,
                "time_period_clause": None,
                "is_followup": False
            }
    
    async def classify_query_async(self, query: str, cached_dates=None, use_cache=True) -> Dict[str, Any]:
        """Asynchronous version of classify_query."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.classify_query(query, cached_dates, use_cache)
        )
        return result 