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
                "least popular", "worst selling", "least ordered"
            ],
            "customer_preferences": [
                "favorite", "preferred", "like", "enjoy", "customer favorite",
                "dislike", "hate", "avoid"
            ],
            "time_analysis": [
                "trend", "over time", "history", "historical", "pattern",
                "season", "seasonal", "monthly", "weekly", "daily", "hourly"
            ],
            "geographical_analysis": [
                "location", "region", "area", "city", "state", "country",
                "branch", "store", "outlet"
            ]
        }
    
    def _init_examples(self) -> None:
        """Initialize example queries for each category."""
        self.examples = {
            "order_history": [
                "Show me my order history from the past week",
                "What did I order last month?",
                "List all my purchases from January",
                "Show me what I ordered on December 25th"
            ],
            "trend_analysis": [
                "How have burger sales changed over the past 3 months?",
                "Show me the weekly trend for salad orders",
                "What's the sales pattern for coffee in the morning vs afternoon?",
                "Has the popularity of vegetarian options increased since last year?"
            ],
            "popular_items": [
                "What are the most popular desserts?",
                "Which appetizers sell best on weekends?",
                "Show me the top 5 best-selling items this month",
                "What's the most ordered breakfast item before 9am?"
            ],
            "order_ratings": [
                "What's the average rating for the chicken sandwich?",
                "Show me dishes with the highest customer ratings",
                "Which menu items received poor reviews last month?",
                "What's the trend in satisfaction scores for the new pizza?"
            ],
            "menu_inquiry": [
                "What vegetarian options do you have?",
                "How much is the deluxe burger?",
                "Does the chicken salad contain nuts?",
                "When will the seasonal menu be available?"
            ],
            "general_question": [
                "What are your opening hours?",
                "Do you offer delivery service?",
                "How can I place a catering order?",
                "Where is your nearest location?"
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
        
        # Create a custom system prompt with instructions for time period extraction
        system_prompt = """You are an AI assistant specialized in classifying restaurant menu-related queries. 
Your task is to:
1. FIRST determine if the query is a follow-up question
2. Analyze the user's query
3. Categorize it into one of these types:
{categories}

4. IDENTIFY ANY TIME PERIOD INFORMATION and convert it to a SQL WHERE clause for the 'updated_at' column.

FOLLOW-UP QUESTION DETECTION:
- A follow-up question often refers to previous information without explicitly stating it
- Look for phrases like "those orders", "that time", "them", "those items", etc.
- If the query seems incomplete without prior context, it's likely a follow-up
- Example: "Who placed those orders?" is a follow-up to a previous query about orders
- Example: "What items were included?" is a follow-up to a previous order discussion

When classifying follow-up questions:
- Maintain the same query_type as the most logical parent query
- For instance, a follow-up to an "order_history" query is also an "order_history" query
- "Who placed those orders?" should be classified as "order_history"
- "What were the most popular items in that period?" should be classified as "popular_items"

Examples of time period information and corresponding WHERE clauses:
- "last week" → WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
- "past 3 months" → WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
- "January" → WHERE MONTH(updated_at) = 1
- "2023" → WHERE YEAR(updated_at) = 2023
- "between March and June" → WHERE updated_at BETWEEN '2023-03-01' AND '2023-06-30'
- "yesterday" → WHERE updated_at = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
- "weekends over the past month" → WHERE DAYOFWEEK(updated_at) IN (1, 7) AND updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)

The CURRENT DATE is: {current_date}
The CURRENT TIME is: {current_time}

Here are examples of different query types:
{examples}

EXAMPLES OF FOLLOW-UP QUESTIONS:
- Initial: "How many orders were completed yesterday?" (order_history)
  Follow-up: "Who placed those orders?" (still order_history)
- Initial: "What were our most popular items last month?" (popular_items)
  Follow-up: "How many of each did we sell?" (still popular_items)
- Initial: "Show me sales data for February." (trend_analysis)
  Follow-up: "How does that compare to January?" (still trend_analysis)

Respond with a JSON object containing three fields:
1. "query_type": The category that best matches the query
2. "time_period_clause": A SQL WHERE clause for time constraints if present, or null if not applicable
3. "is_followup": Boolean indicating if this is a follow-up question

Example response format:
{{
  "query_type": "order_history",
  "time_period_clause": "WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK)",
  "is_followup": false
}}

For follow-up questions:
{{
  "query_type": "order_history",
  "time_period_clause": null,
  "is_followup": true
}}
"""
        
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
        
        # User prompt is just the query itself
        user_prompt = query
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def get_available_query_types(self) -> List[str]:
        """Get the list of available query categories."""
        return self.query_categories
    
    def is_valid_query_type(self, query_type: str) -> bool:
        """Check if a query type is valid."""
        return query_type in self.query_categories


# Global instance
classification_prompt_builder = ClassificationPromptBuilder() 