"""
Classification Service Prompt Builder

This module provides a builder class for constructing classification prompts
using the template-based system.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

from services.utils.prompt_loader import get_prompt_loader
from services.utils.logging import get_logger

logger = get_logger(__name__)


class ClassificationPromptBuilder:
    """Builder for classification service prompts."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the prompt builder.
        
        Args:
            config: Optional configuration parameters
        """
        self.config = config or {}
        self.prompt_loader = get_prompt_loader()
        self.db_schema = {}  # Initialize empty database schema
        
        # Initialize query categories and analysis types
        self._init_categories()
        self._init_parameter_schemas()
        self._init_examples()
    
    def _init_categories(self) -> None:
        """Initialize query categories according to the development plan."""
        self.query_categories = [
            "order_history",  # Queries about past orders and analytics
            "menu",           # Queries about current menu items
            "action",         # Requests to perform actions like editing items
            "general",        # General questions not requiring specific data
            "follow_up"       # Follow-up questions to previous queries
        ]
    
    def _init_parameter_schemas(self) -> None:
        """Initialize schemas for parameters that should be extracted for each query type."""
        self.parameter_schemas = {
            "order_history": {
                "time_period": "String describing the time period for query (e.g., 'last month', '2025-02-21'). Applies to the 'orders' table using fields like created_at or updated_at.",
                "filters": "Array of filter conditions, each with 'field', 'operator', and 'value'. Fields should match columns in the 'orders' table (e.g., total, status).",
                "sort": "Optional object with 'field' (e.g., total, created_at) and 'order' (asc or desc) for sorting orders.",
                "limit": "Optional integer specifying the maximum number of orders to return.",
                "aggregation": "Optional aggregation function (SUM, AVG, COUNT, etc.) applied to a numeric field."
            },
            "menu": {
                "entities": "Array of menu item names or category names. Should correspond with 'items' and 'categories' table columns.",
                "attributes": "Array of attributes to include (e.g., name, price, description) from the 'items' table.",
                "filters": "Optional array of filter conditions for menu items."
            },
            "action": {
                "action": "String describing the action (e.g., update_price, disable_item) that maps to an operation on a specific table field.",
                "entities": "Array of target entity names (e.g., item names from the 'items' table).",
                "values": "Object containing the values for the action (e.g., {price: 9.99})."
            },
            "general": {
                "subject": "Optional string describing the general subject of the query."
            },
            "follow_up": {
                "refers_to": "String indicating the reference of the follow-up (e.g., 'previous_query', 'last_item')."
            }
        }
    
    def _init_examples(self) -> None:
        """Initialize classification examples to guide the model."""
        self.examples = [
            {
                "query": "How many orders did we have last month?",
                "classification": {
                    "query_type": "order_history",
                    "confidence": 0.95,
                    "parameters": {
                        "time_period": "last month"
                    }
                }
            },
            {
                "query": "What's our most popular item?",
                "classification": {
                    "query_type": "order_history",
                    "confidence": 0.92,
                    "parameters": {
                        "time_period": "all time",
                        "sort": {"field": "total", "order": "desc"},
                        "limit": 1
                    }
                }
            },
            {
                "query": "Show me the burger menu",
                "classification": {
                    "query_type": "menu",
                    "confidence": 0.98,
                    "parameters": {
                        "entities": ["burger"],
                        "attributes": ["name", "price", "description"]
                    }
                }
            },
            {
                "query": "Change the price of the Deluxe Burger to $12.99",
                "classification": {
                    "query_type": "action",
                    "confidence": 0.97,
                    "parameters": {
                        "action": "update_price",
                        "entities": ["Deluxe Burger"],
                        "values": {"price": 12.99}
                    }
                }
            },
            {
                "query": "How many of those did we sell last week?",
                "classification": {
                    "query_type": "follow_up",
                    "confidence": 0.91,
                    "parameters": {
                        "time_period": "last week",
                        "refers_to": "previous_query"
                    }
                }
            }
        ]
    
    def get_classification_system_prompt(self) -> str:
        """
        Generate the system prompt for the classification model.
        
        Returns:
            System prompt instructing how to classify queries
        """
        prompt = f"""You are an advanced query classifier for a restaurant club management system. Your task is to analyze user queries and classify them into the appropriate category, extract relevant parameters, and assign a confidence score.

QUERY CATEGORIES:
{', '.join(self.query_categories)}

PARAMETER SCHEMAS:
"""
        
        # Add parameter schema information
        for category, schema in self.parameter_schemas.items():
            prompt += f"\n{category}:\n"
            for param, description in schema.items():
                prompt += f"- {param}: {description}\n"
        
        # Add example classifications
        prompt += "\n\nEXAMPLES OF CLASSIFICATIONS:\n"
        for example in self.examples:
            prompt += f"\nQuery: \"{example['query']}\"\nClassification: {example['classification']}\n"
        
        # Add final instructions
        prompt += """
INSTRUCTIONS:
1. Analyze the query to determine its category
2. Extract all relevant parameters based on the schema for that category
3. Assign a confidence score (0.0-1.0) reflecting how certain you are of the classification
4. Return a JSON object with query_type, confidence, and parameters

You must ALWAYS respond with a valid JSON object containing these keys.
"""
        return prompt
    
    def get_classification_user_prompt(self, query: str) -> str:
        """
        Generate the user prompt for the classification model.
        
        Args:
            query: The user's query text
            
        Returns:
            Formatted user prompt
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        return f"Current date: {current_date}\n\nClassify this query: \"{query}\""
    
    def build_classification_prompt(self, query: str, cached_dates=None) -> Dict[str, str]:
        """
        Build a complete prompt for query classification.
        
        Args:
            query: The user's query text
            cached_dates: Optional date information to include
            
        Returns:
            Dictionary with system and user prompt components
        """
        return {
            "system": self.get_classification_system_prompt(),
            "user": self.get_classification_user_prompt(query)
        }
    
    def get_available_query_types(self) -> List[str]:
        """Get a list of all available query types."""
        return self.query_categories
    
    def is_valid_query_type(self, query_type: str) -> bool:
        """Check if a query type is valid."""
        return query_type in self.query_categories
    
    def set_database_schema(self, schema: Dict[str, List[str]]) -> None:
        """
        Set the database schema information for classification context.
        
        Args:
            schema: A dictionary mapping table names to lists of column names
        """
        self.db_schema = schema
        logger.info(f"Prompt builder database schema set with {len(schema)} tables")


# Singleton instance for shared use
classification_prompt_builder = ClassificationPromptBuilder() 