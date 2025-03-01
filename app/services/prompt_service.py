"""
Prompt Service module.

This module provides centralized prompt generation functionality for different 
LLM providers (OpenAI, Google Gemini) and different use cases (categorization, SQL generation).
"""

import os
import logging
import datetime
from typing import Dict, List, Any, Optional, Union

# Get the logger
logger = logging.getLogger("ai_menu_updater")

class PromptService:
    """
    Service for generating and managing prompts for various language models.
    
    This service centralizes prompt generation across different LLM providers
    and different use cases, making it easier to maintain and extend.
    """
    
    def __init__(self):
        """Initialize the PromptService."""
        logger.info("Initializing PromptService")
        
        # Import prompt modules only when needed to avoid circular imports
        try:
            from prompts import load_example_queries
            from prompts.google_gemini_prompt import create_gemini_prompt
            from prompts.openai_categorization_prompt import (
                create_categorization_prompt, 
                create_query_categorization_prompt
            )
            
            # Store references to imported functions
            self._load_example_queries = load_example_queries
            self._create_gemini_prompt = create_gemini_prompt
            self._create_categorization_prompt = create_categorization_prompt
            self._create_query_categorization_prompt = create_query_categorization_prompt
            
            logger.info("Successfully loaded prompt generation functions")
        except ImportError as e:
            logger.error(f"Error importing prompt modules: {str(e)}")
            raise
    
    def create_gemini_prompt(
        self,
        user_query: str,
        context_files: Dict[str, Any],
        location_id: Union[int, str] = 62,
        conversation_history: Optional[List[Dict]] = None,
        previous_sql: Optional[str] = None,
        previous_results: Optional[List[Dict]] = None,
        order_detail_fields: Optional[Dict] = None,
        date_context_instruction: str = "",
    ) -> str:
        """
        Create an optimized prompt for Google Gemini with full business context.
        
        Args:
            user_query: The user's original query
            context_files: Dictionary containing business rules, schema, and example queries
            location_id: The location ID to filter data
            conversation_history: List of previous query exchanges
            previous_sql: The SQL query from the previous interaction
            previous_results: Results from the previous query
            order_detail_fields: Optional fields for order details
            date_context_instruction: Additional date context instructions
            
        Returns:
            A formatted prompt string for Gemini
        """
        logger.info(f"Generating Gemini prompt for query: '{user_query}'")
        
        try:
            prompt = self._create_gemini_prompt(
                user_query=user_query,
                context_files=context_files,
                location_id=location_id,
                conversation_history=conversation_history,
                previous_sql=previous_sql,
                previous_results=previous_results,
                order_detail_fields=order_detail_fields,
                date_context_instruction=date_context_instruction,
            )
            
            logger.info(f"Generated Gemini prompt with length: {len(prompt)} characters")
            return prompt
        except Exception as e:
            logger.error(f"Error generating Gemini prompt: {str(e)}")
            # Provide a fallback simple prompt
            return f"Generate SQL for this query: {user_query}"
    
    def create_categorization_prompt(self, cached_dates=None) -> Dict[str, Any]:
        """
        Create an optimized categorization prompt for OpenAI.
        
        Args:
            cached_dates: Optional previously cached date context
            
        Returns:
            Dict containing the prompt string and context information
        """
        logger.info("Generating categorization prompt")
        
        try:
            prompt_dict = self._create_categorization_prompt(cached_dates=cached_dates)
            logger.info(f"Generated categorization prompt data with {len(str(prompt_dict))} characters")
            return prompt_dict
        except Exception as e:
            logger.error(f"Error generating categorization prompt: {str(e)}")
            # Return a simple fallback
            return {"prompt": "Categorize the query into appropriate types"}
    
    def create_query_categorization_prompt(
        self, 
        user_query: str, 
        conversation_history=None
    ) -> str:
        """
        Create a prompt for categorizing a user query.
        
        Args:
            user_query: The user's query to categorize
            conversation_history: Previous conversation history
            
        Returns:
            The formatted prompt for query categorization
        """
        logger.info(f"Generating query categorization prompt for: '{user_query}'")
        
        try:
            prompt = self._create_query_categorization_prompt(
                user_query=user_query,
                conversation_history=conversation_history
            )
            
            logger.info(f"Generated query categorization prompt with length: {len(prompt)} characters")
            return prompt
        except Exception as e:
            logger.error(f"Error generating query categorization prompt: {str(e)}")
            # Provide a fallback simple prompt
            return f"Categorize this query: {user_query}"
    
    def load_example_queries(self) -> str:
        """
        Load example queries for prompt generation.
        
        Returns:
            A string containing example queries for different categories
        """
        try:
            examples = self._load_example_queries()
            logger.info(f"Loaded {len(examples.split())} words of example queries")
            return examples
        except Exception as e:
            logger.error(f"Error loading example queries: {str(e)}")
            # Return an empty string as fallback
            return ""


# Create a singleton instance
prompt_service = PromptService() 