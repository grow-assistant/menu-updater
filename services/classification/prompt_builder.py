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
- A question is ONLY considered a follow-up if it's a logical continuation to a previous query
- The primary test: "Would this question make sense without any prior conversation context?"
- If the answer is NO, then it's a follow-up question
- Look for pronouns referring to previous context: "those orders", "that time", "them", "those items"
- Look for implied information: "How many were sold?" (without specifying what items)
- Questions that stand on their own are NOT follow-ups, even if related to a previous topic
- YOU must determine this, not any hard-coded logic or rules

Example follow-up patterns:
- Questions using pronouns without clear antecedents in the same question
- Questions that omit critical information (what items, what time period, etc.)
- Questions that directly reference a previous response
- Questions that only make sense in the context of previous conversation

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
  Follow-up: "Who placed those orders?" (still order_history, is_followup=true)
- Initial: "What were our most popular items last month?" (popular_items)
  Follow-up: "How many of each did we sell?" (still popular_items, is_followup=true)
- Initial: "Show me sales data for February." (trend_analysis)
  Follow-up: "How does that compare to January?" (still trend_analysis, is_followup=true)
- Individual question: "What were the most popular items last week?" (popular_items, is_followup=false)
  Even if asked after another question, this is NOT a follow-up because it's complete on its own.

Your response MUST accurately identify if a question is a follow-up based SOLELY on the question's content and whether it requires previous context to make sense. This determination must be reflected in the "is_followup" field of your JSON response.

For queries related to 'order_history', please also extract and provide:
1. A specific start_date in ISO format (YYYY-MM-DD)
2. A specific end_date in ISO format (YYYY-MM-DD)

For example, if the query is 'Show me orders from last month', you should determine:
- start_date: The first day of last month (e.g., '2025-02-01')
- end_date: The last day of last month (e.g., '2025-02-28')

Example response format for order_history queries:
{{
  "query_type": "order_history",
  "time_period_clause": "WHERE updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)",
  "is_followup": false,
  "start_date": "2025-02-01",
  "end_date": "2025-02-28"
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