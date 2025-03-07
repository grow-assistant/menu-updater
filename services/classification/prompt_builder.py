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
        
        # Initialize query categories and analysis types
        self._init_categories()
        self._init_analysis_types()
        self._init_examples()
    
    def _init_categories(self) -> None:
        """Initialize query categories."""
        self.query_categories = [
            "order_history",
            "trend_analysis",
            "popular_items",
            "order_ratings",
            "menu_inquiry",
            "general_question"  # Keep general_question as a fallback
        ]
    
    def _init_analysis_types(self) -> None:
        """Initialize analysis types and keywords."""
        self.analysis_types = {
            "item_performance": [
                "popular", "bestseller", "best seller", "top selling", "most ordered",
                "least ordered", "worst seller", "worst performing"
            ],
            "sales_trends": [
                "trend", "trending", "increasing", "decreasing", "growth", "decline"
            ],
            "customer_preferences": [
                "preference", "favorite", "most liked", "highest rated", "best reviewed"
            ],
            "pricing_analysis": [
                "price analysis", "pricing strategy", "price comparison", "margin", "profit"
            ]
        }
    
    def _init_examples(self) -> None:
        """Initialize examples for each query type."""
        self.examples = {
            "order_history": [
                "Show me orders from last week",
                "List all orders from January",
                "How many orders did we get yesterday?",
                "Display transactions from March 1-15"
            ],
            "update_price": [
                "Change the price of margherita pizza to $12.99",
                "Update caesar salad price to $8.50",
                "Set new price for chicken wings to $14",
                "Increase the price of all desserts by 5%"
            ],
            "disable_item": [
                "Remove the seafood pasta from the menu",
                "Disable the tiramisu dessert",
                "Take the veggie burger off the menu temporarily",
                "Deactivate all seasonal items"
            ],
            "enable_item": [
                "Add back the mushroom risotto to the menu",
                "Enable the chocolate lava cake",
                "Make the summer salad available again",
                "Reactivate all holiday specials"
            ],
            "query_menu": [
                "Show me all appetizers on the menu",
                "Which desserts do we offer?",
                "List all gluten-free options",
                "How many vegetarian dishes do we have?"
            ],
            "query_performance": [
                "What's our busiest day of the week?",
                "Show me sales data for February",
                "How did the new burger perform last month?",
                "Compare lunch vs dinner revenue"
            ],
            "query_ratings": [
                "What's our average customer rating?",
                "Show me the worst-rated dishes",
                "How has our customer satisfaction changed over time?",
                "What feedback did we get about the new pasta dish?"
            ],
            "general_question": [
                "What hours are you open tomorrow?",
                "Do you offer catering services?",
                "How can I apply for a job?",
                "What's your cancellation policy?"
            ]
        }
    
    def build_classification_prompt(self, query: str, cached_dates=None) -> Dict[str, str]:
        """
        Build classification prompt for the given query.
        
        Args:
            query: The user query to classify
            cached_dates: Optional date information to include in context
            
        Returns:
            Dictionary with system and user prompts
        """
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Load the base classification system prompt
        system_prompt = self.prompt_loader.load_template("classification_system_prompt")
        
        # Format with categories and examples
        categories_str = "\n".join([f"- {cat}" for cat in self.query_categories])
        
        # Format examples for each category
        examples_str = ""
        for category, example_list in self.examples.items():
            examples_str += f"\n{category.upper()} EXAMPLES:\n"
            examples_str += "\n".join([f"- \"{ex}\"" for ex in example_list[:2]])
            examples_str += "\n"
        
        # Format with all required information
        system_prompt = system_prompt.format(
            categories=categories_str,
            examples=examples_str,
            current_date=current_date,
            current_time=current_time
        )
        
        # Create user prompt
        user_prompt = f"Query to classify: \"{query}\""
        
        # Add date context if available
        if cached_dates:
            dates_str = ", ".join([f"{date}: {count} references" for date, count in cached_dates.items()])
            user_prompt += f"\n\nContext - Dates mentioned in previous conversations: {dates_str}"
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def get_available_query_types(self) -> List[str]:
        """
        Get a list of all available query types.
        
        Returns:
            List of query type names
        """
        return self.query_categories
    
    def is_valid_query_type(self, query_type: str) -> bool:
        """
        Check if a query type is valid.
        
        Args:
            query_type: Query type to check
            
        Returns:
            True if the query type is valid, False otherwise
        """
        return query_type in self.query_categories


# Singleton instance
classification_prompt_builder = ClassificationPromptBuilder() 