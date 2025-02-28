"""
Knowledge Base for Order Query System

This file contains a collection of rules, configurations, and best practices that
should be followed when processing order queries. These items will be passed into
prompts to ensure consistency and adherence to standards.

How to use:
1. Import the relevant knowledge items in your prompt-building code
2. Include the knowledge text in your prompts to guide AI behavior
3. Update this file as new rules or knowledge emerge

Knowledge is organized by categories and accessible through simple functions.
"""

import datetime
from typing import Dict, List, Optional


class KnowledgeItem:
    """Represents a single piece of knowledge with metadata for retrieval."""

    def __init__(
        self, title: str, content: str, triggers: List[str], importance: int = 1
    ):
        """
        Initialize a knowledge item.

        Args:
            title: Short descriptive title
            content: The actual knowledge content
            triggers: List of keywords that should trigger this knowledge
            importance: Priority level (1-5, 5 being highest)
        """
        self.title = title
        self.content = content
        self.triggers = triggers
        self.importance = importance
        self.created_at = datetime.datetime.now()
        self.last_updated = self.created_at

    def update(self, content: str):
        """Update the content and last_updated timestamp."""
        self.content = content
        self.last_updated = datetime.datetime.now()

    def __str__(self):
        return f"{self.title}: {self.content}"


# Time and Date Rules
TIME_TIMEZONE_RULE = KnowledgeItem(
    title="Time Format and Timezone",
    content="""
    All times should be displayed in Eastern Standard Time (EST) timezone.
    When generating SQL queries involving time:
    1. Use appropriate timezone conversion functions if needed
    2. Format times as 'YYYY-MM-DD HH:MM:SS' for display
    3. Make sure all time comparisons account for timezone differences
    """,
    triggers=["time", "timezone", "EST", "date", "datetime"],
)

ORDER_STATUS_RULES = KnowledgeItem(
    title="Order Status Definitions",
    content="""
    Order statuses follow these definitions:
    - 'completed' (status code 7): Order has been delivered and payment processed
    - 'pending': Order has been placed but not yet fulfilled
    - 'cancelled' (status code 6): Order was cancelled by either customer or staff
    - 'in_progress': Order is being prepared or is out for delivery

    When filtering by status in SQL queries, use the numeric status codes (e.g., 7 for completed, 6 for cancelled).
    """,
    triggers=["status", "completed", "pending", "cancelled", "in_progress"],
)

PRICE_FORMATTING_RULES = KnowledgeItem(
    title="Price Formatting",
    content="""
    All monetary values should:
    1. Be displayed with 2 decimal places
    2. Include currency symbol ($) for display purposes
    3. Use proper comma separation for thousands (e.g., $1,234.56)
    4. Be calculated including all applicable taxes and fees
    """,
    triggers=["price", "cost", "amount", "total", "money", "dollars"],
)

SQL_QUERY_RULES = KnowledgeItem(
    title="SQL Query Standards",
    content="""
    When generating SQL queries:
    1. Always use WHERE clauses to filter for the appropriate date/time ranges
    2. Join only necessary tables to improve performance
    3. Apply appropriate LIMIT clauses for large result sets
    4. Always use proper parameterization to prevent SQL injection
    5. Include ORDER BY clauses when sequence is important
    6. Use 'updated_at' instead of 'created_at' for consistency
    7. Always handle NULL values properly with COALESCE or IS NULL/IS NOT NULL checks
    8. Use CASE statements for complex conditional logic
    """,
    triggers=[
        "SQL",
        "query",
        "database",
        "select",
        "where",
        "join",
        "created_at",
        "updated_at",
    ],
)

RESPONSE_FORMAT_RULES = KnowledgeItem(
    title="AI Response Formatting",
    content="""
    When generating natural language responses:
    1. Begin with a direct answer to the question
    2. Structure data in an easily readable format (lists or tables for multiple items)
    3. Use clear, concise language appropriate for business contexts
    4. Include numeric totals and summaries for quantitative queries
    5. Add brief context or explanation when results might be unexpected
    6. Always use bold formatting (**text**) for key metrics and important figures
    7. Organize information hierarchically with numbered lists for multiple items
    8. End responses with a brief insight or actionable suggestion when appropriate
    """,
    triggers=["response", "answer", "format", "display", "output"],
)

# New knowledge items
RATINGS_ANALYSIS_RULES = KnowledgeItem(
    title="Ratings Analysis Guidelines",
    content="""
    When analyzing customer ratings:
    1. Ratings range from 1-5 stars with 5 being the highest
    2. Consider ratings below 4 as areas needing improvement
    3. Always look for patterns in low ratings (time of day, specific items, etc.)
    4. When reporting average ratings, include the count/sample size
    5. For ratings analysis, include:
       - Distribution of ratings (how many 1-star, 2-star, etc.)
       - Comparison to previous time periods when possible
       - Specific order details for low-rated orders
    6. Use the order_ratings_feedback table to access rating data
    7. Always suggest potential improvement areas based on rating patterns
    """,
    triggers=[
        "rating",
        "ratings",
        "stars",
        "feedback",
        "satisfaction",
        "review",
        "reviews",
    ],
)

DATA_HANDLING_RULES = KnowledgeItem(
    title="Data Handling for Missing or Zero Values",
    content="""
    When handling missing or zero values in query results:
    1. Always check for NULL values with appropriate SQL functions (COALESCE, NULLIF)
    2. For zero or empty results, explicitly state this in the response
    3. When encountering zeros in metrics like "average order time", explain potential reasons:
       - Data collection issues
       - System configuration errors
       - Actual zero values (rare but possible)
    4. Suggest follow-up queries that could provide more context
    5. Use appropriate statistical methods when calculating averages with outliers
    6. For time-based metrics, consider adding minimum and maximum ranges alongside averages
    """,
    triggers=["zero", "null", "missing", "empty", "average", "avg", "time", "error"],
)

CONTEXT_AWARE_RESPONSE_RULES = KnowledgeItem(
    title="Context-Aware Response Guidelines",
    content="""
    When answering follow-up questions in a conversation:
    1. Reference previous questions and answers for continuity
    2. Use comparative language when showing changes or trends
    3. Highlight new insights not mentioned in previous responses
    4. Connect data points across different queries when relevant
    5. Maintain consistent terminology throughout the conversation
    6. Use phrases like "As we saw earlier..." or "Building on the previous analysis..."
    7. Provide cumulative insights that build on the entire conversation context
    """,
    triggers=[
        "follow-up",
        "followup",
        "previous",
        "earlier",
        "before",
        "already",
        "also",
    ],
)

ERROR_ANALYSIS_RULES = KnowledgeItem(
    title="Error Analysis Guidelines",
    content="""
    When identifying errors or anomalies in data:
    1. Clearly state when results appear unusual or potentially erroneous
    2. Suggest possible causes for data anomalies
    3. Recommend data validation steps when appropriate
    4. For extreme outliers, consider excluding them from aggregate calculations
    5. Compare suspicious values with historical norms
    6. When time metrics show as 0 seconds or NULL, explain potential technical causes
    7. Suggest specific SQL query modifications that might resolve data issues
    """,
    triggers=[
        "error",
        "anomaly",
        "unusual",
        "suspect",
        "incorrect",
        "zero",
        "null",
        "bug",
    ],
)

# SQL Knowledge reference examples - not to be used as templates but as context
SQL_KNOWLEDGE = {
    "day_of_week": {
        "description": "Analysis of order patterns by day of week",
        "context": """
When analyzing orders by day of week, use EXTRACT(DOW FROM timestamp) to get the day number (0=Sunday through 6=Saturday).
Remember to apply appropriate timezone handling with AT TIME ZONE clauses.
Group by the extracted day and count orders to see patterns.
        """,
        "example": """
-- Example query for day of week analysis
SELECT
  EXTRACT(DOW FROM (o.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'US/Eastern')) AS day_of_week,
  COUNT(o.id) AS order_count
FROM orders AS o
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND o.status = 7
GROUP BY day_of_week
ORDER BY order_count DESC;
        """,
    },
    "fulfillment_time": {
        "description": "Calculating average time between order creation and completion",
        "context": """
For fulfillment time analysis, calculate the time difference between timestamps.
Convert to minutes using EXTRACT(EPOCH FROM time_diff) / 60.
Apply appropriate filters to only include completed orders (usually status = 7).
        """,
        "example": """
-- Example query for order fulfillment time
SELECT
  AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)) / 60) AS average_fulfillment_time_minutes
FROM orders AS o
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND o.status = 7 AND o.updated_at >= NOW() - INTERVAL '30 days';
        """,
    },
    "delivery": {
        "description": "Analyzing delivery-specific order patterns",
        "context": """
When analyzing delivery orders, filter by order_type = 'delivery'.
Join with the appropriate delivery service table if needed for more details.
Compare with pickup or other order types for comparative analysis.
        """,
        "example": """
-- Example query for delivery orders analysis
SELECT
  AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)) / 60) AS average_fulfillment_time_minutes
FROM orders AS o
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND o.status = 7 AND o.order_type = 'delivery'
AND o.updated_at >= NOW() - INTERVAL '30 days';
        """,
    },
    "cancellations": {
        "description": "Analyzing canceled or refunded orders",
        "context": """
For cancellation analysis, look for orders with status values indicating cancellation or refund (typically 8 or 9).
Consider grouping by cancellation_reason to find patterns in why orders are being canceled.
        """,
        "example": """
-- Example query for canceled orders count
SELECT
  COUNT(o.id) AS canceled_order_count
FROM orders AS o
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND (o.status = 8 OR o.status = 9)
AND o.updated_at >= NOW() - INTERVAL '30 days';

-- Example query for cancellation reasons
SELECT
  o.cancellation_reason AS reason,
  COUNT(o.id) AS count
FROM orders AS o
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND (o.status = 8 OR o.status = 9)
GROUP BY o.cancellation_reason
ORDER BY count DESC;
        """,
    },
    "general": {
        "description": "General SQL query patterns and best practices",
        "context": """
1. Always include appropriate JOINs (orders to locations, etc.)
2. Filter by location_id when analyzing restaurant-specific data
3. Use proper date/time handling with INTERVAL and timezone conversion
4. For comparative queries, consider using subqueries or window functions
5. Use descriptive column aliases for better readability
        """,
        "example": """
-- Example of a well-structured query
SELECT
  m.name AS menu_item,
  COUNT(oi.id) AS order_count,
  SUM(oi.price) AS total_revenue
FROM order_items AS oi
JOIN menu_items AS m ON oi.menu_item_id = m.id
JOIN orders AS o ON oi.order_id = o.id
JOIN locations AS l ON o.location_id = l.id
WHERE o.location_id = 62 AND o.status = 7
AND o.updated_at >= NOW() - INTERVAL '30 days'
GROUP BY m.name
ORDER BY order_count DESC
LIMIT 10;
        """,
    },
}

# Knowledge Registry - Update with new items
_KNOWLEDGE_REGISTRY: Dict[str, KnowledgeItem] = {
    "time_timezone": TIME_TIMEZONE_RULE,
    "order_status": ORDER_STATUS_RULES,
    "price_formatting": PRICE_FORMATTING_RULES,
    "sql_query": SQL_QUERY_RULES,
    "response_format": RESPONSE_FORMAT_RULES,
    "ratings_analysis": RATINGS_ANALYSIS_RULES,
    "data_handling": DATA_HANDLING_RULES,
    "context_aware": CONTEXT_AWARE_RESPONSE_RULES,
    "error_analysis": ERROR_ANALYSIS_RULES,
}


def get_knowledge_by_key(key: str) -> Optional[str]:
    """
    Retrieve knowledge content by its key.

    Args:
        key: The identifier for the knowledge item

    Returns:
        The knowledge content or None if not found
    """
    item = _KNOWLEDGE_REGISTRY.get(key)
    return item.content if item else None


def get_knowledge_by_trigger(trigger: str) -> List[str]:
    """
    Retrieve all knowledge items that match a trigger word.

    Args:
        trigger: The trigger word to search for

    Returns:
        List of knowledge content that matches the trigger
    """
    matches = []
    for item in _KNOWLEDGE_REGISTRY.values():
        if trigger.lower() in [t.lower() for t in item.triggers]:
            matches.append(item.content)
    return matches


def get_all_knowledge() -> str:
    """
    Retrieve all knowledge items concatenated into a single string.

    Returns:
        All knowledge content
    """
    return "\n\n".join(str(item) for item in _KNOWLEDGE_REGISTRY.values())


def get_formatted_knowledge_for_prompt(
    keys: List[str] = None, triggers: List[str] = None
) -> str:
    """
    Get formatted knowledge content ready to be inserted into a prompt.

    Args:
        keys: Specific knowledge keys to include
        triggers: Trigger words to search for relevant knowledge

    Returns:
        Formatted knowledge content for prompts
    """
    items = []

    # Add items by key
    if keys:
        for key in keys:
            content = get_knowledge_by_key(key)
            if content:
                items.append(content)

    # Add items by trigger
    if triggers:
        for trigger in triggers:
            trigger_items = get_knowledge_by_trigger(trigger)
            items.extend(trigger_items)

    # If neither keys nor triggers specified, return all knowledge
    if not keys and not triggers:
        items = [item.content for item in _KNOWLEDGE_REGISTRY.values()]

    # Remove duplicates while preserving order
    unique_items = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)

    return "\n\n===IMPORTANT RULES AND GUIDELINES===\n\n" + "\n\n".join(unique_items)


def get_sql_knowledge(knowledge_type):
    """
    Get knowledge information for a specific type of SQL query.

    Args:
        knowledge_type (str): The type of knowledge to retrieve

    Returns:
        dict: The knowledge information including context and examples
    """
    if knowledge_type in SQL_KNOWLEDGE:
        return SQL_KNOWLEDGE[knowledge_type]
    return SQL_KNOWLEDGE["general"]


def get_formatted_knowledge_for_prompt(triggers=None):
    """
    Format relevant knowledge as context for an LLM prompt.

    Args:
        triggers (list): List of keywords to identify relevant knowledge

    Returns:
        str: Formatted knowledge string for inclusion in prompts
    """
    if not triggers:
        triggers = ["general"]

    knowledge_sections = []

    # Always include general knowledge
    if "general" not in triggers:
        triggers.append("general")

    # Add SQL best practices if SQL is in triggers
    if "SQL" in triggers or "query" in triggers:
        knowledge_sections.append(
            """
## SQL Best Practices
When writing SQL queries:
- Filter by the location_id from the context (currently set to 62)
- Use 'updated_at' instead of 'created_at' for time range filters
- Remember that order status 7 indicates completed orders
- Order types include 'delivery', 'pickup', and 'dine_in'
- Include clear ORDER BY clauses for analytical queries
- Use appropriate JOINs between tables (orders, locations, menu_items, etc.)
        """
        )

    # Add day of week knowledge if relevant
    if any(keyword in triggers for keyword in ["day", "week", "weekday", "weekend"]):
        knowledge = get_sql_knowledge("day_of_week")
        knowledge_sections.append(
            f"""
## Day of Week Analysis
{knowledge['context']}

Example:
{knowledge['example']}
        """
        )

    # Add fulfillment time knowledge if relevant
    if any(
        keyword in triggers
        for keyword in ["time", "fulfillment", "duration", "minutes"]
    ):
        knowledge = get_sql_knowledge("fulfillment_time")
        knowledge_sections.append(
            f"""
## Order Fulfillment Time Analysis
{knowledge['context']}

Example:
{knowledge['example']}
        """
        )

    # Add delivery knowledge if relevant
    if any(keyword in triggers for keyword in ["delivery", "pickup", "order_type"]):
        knowledge = get_sql_knowledge("delivery")
        knowledge_sections.append(
            f"""
## Delivery Orders Analysis
{knowledge['context']}

Example:
{knowledge['example']}
        """
        )

    # Add cancellation knowledge if relevant
    if any(keyword in triggers for keyword in ["cancel", "refund", "reason"]):
        knowledge = get_sql_knowledge("cancellations")
        knowledge_sections.append(
            f"""
## Cancellation Analysis
{knowledge['context']}

Example:
{knowledge['example']}
        """
        )

    # Join all sections
    return "\n\n".join(knowledge_sections)
