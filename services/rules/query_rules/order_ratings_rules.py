"""
Rules specific to order ratings queries.
"""

from typing import Dict, Any
from services.rules.base_rules import get_base_rules
from services.rules.query_rules import (
    replace_placeholders,
    load_all_sql_files_from_directory,
)
from services.rules.business_rules import DEFAULT_LOCATION_ID, TIMEZONE_OFFSET

# Schema information for order ratings queries
ORDER_RATINGS_SCHEMA = {
    "orders": {
        "description": "Main orders table for ratings analysis",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "customer_id": "INTEGER - Foreign key to users table",
            "vendor_id": "INTEGER - Foreign key to users table",
            "location_id": "INTEGER - Foreign key to locations table",
            "status": "INTEGER - Order status (7 = completed)",
            "total": "NUMERIC - Total order amount",
            "tax": "NUMERIC - Tax amount",
            "instructions": "TEXT - Special instructions for the order",
            "type": "INTEGER - Order type identifier",
            "marker_id": "INTEGER - Foreign key to markers table",
            "fee": "NUMERIC - Service fee amount (default 0)",
            "loyalty_id": "CHARACTER VARYING(255) - Loyalty program identifier",
            "fee_percent": "NUMERIC - Service fee percentage (default 0)",
            "tip": "NUMERIC - Tip amount (default 0)",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the order was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the order was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the order was deleted (if applicable)"
        },
        "relationships": [
            "FOREIGN KEY (customer_id) REFERENCES users(id)",
            "FOREIGN KEY (vendor_id) REFERENCES users(id)",
            "FOREIGN KEY (location_id) REFERENCES locations(id)",
            "FOREIGN KEY (marker_id) REFERENCES markers(id)"
        ]
    },
    "order_ratings": {
        "description": "Customer ratings for orders",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "order_id": "INTEGER - Foreign key to orders table",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the rating was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the rating was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the rating was deleted (if applicable)",
            "acknowledged": "BOOLEAN - Whether the rating has been acknowledged by staff (default false)"
        },
        "relationships": ["FOREIGN KEY (order_id) REFERENCES orders(id)"],
        "usage_notes": "Always LEFT JOIN from orders to this table"
    },
    "rating_categories": {
        "description": "Categories for rating feedback (e.g., food quality, service)",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "label": "CHARACTER VARYING(255) - Display name of the rating category",
            "description": "CHARACTER VARYING(25) - Detailed description of what is being rated",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the category was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the category was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the category was deleted (if applicable)"
        }
    },
    "order_ratings_feedback": {
        "description": "Actual ratings provided by customers",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "rating_id": "INTEGER - Foreign key to order_ratings table",
            "category_id": "INTEGER - Foreign key to rating_categories table",
            "value": "INTEGER - Rating value (typically 1-5)",
            "notes": "TEXT - Optional text feedback"
        },
        "relationships": [
            "FOREIGN KEY (rating_id) REFERENCES order_ratings(id)",
            "FOREIGN KEY (category_id) REFERENCES rating_categories(id)"
        ],
        "usage_notes": "Contains the actual rating values. Always LEFT JOIN from order_ratings to this table."
    },
    "rating_responses": {
        "description": "Predefined response options for ratings",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "category_id": "INTEGER - Foreign key to rating_categories table",
            "label": "TEXT - Display text of the response option",
            "description": "TEXT - More detailed explanation of the response"
        },
        "relationships": ["FOREIGN KEY (category_id) REFERENCES rating_categories(id)"]
    },
    "order_ratings_feedback_responses": {
        "description": "Junction table for selected rating responses",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "feedback_id": "INTEGER - Foreign key to order_ratings_feedback table",
            "response_id": "INTEGER - Foreign key to rating_responses table"
        },
        "relationships": [
            "FOREIGN KEY (feedback_id) REFERENCES order_ratings_feedback(id)",
            "FOREIGN KEY (response_id) REFERENCES rating_responses(id)"
        ],
        "usage_notes": "Contains specific response options selected by customers for their ratings."
    }
}

# Order ratings query rules
ORDER_RATINGS_RULES = {
    "general": {
        "completed_orders_only": "Only include completed orders (status = 7) for ratings analysis",
        "time_period": "Filter by time period (e.g., last month, last quarter) for trend analysis",
        "location_filter": "ALWAYS filter by o.location_id = [LOCATION_ID]",
        "rating_range": "Rating values typically range from 1-5 with 5 being highest",
        "aggregation": "When aggregating, calculate count, average, and distribution of ratings",
        "unrated_orders": "Use LEFT JOIN to also include orders without ratings when appropriate",
        "privacy": "Never include personally identifiable information in general ratings reports",
        "comments": "Handle NULL comments appropriately; don't assume all ratings have feedback text"
    }
}

def get_rules(rules_service=None) -> Dict[str, Any]:
    """
    Get rules for order ratings queries.
    
    Args:
        rules_service: Optional reference to the RulesService instance
    
    Returns:
        Dictionary containing rules, patterns, and examples for order ratings queries
    """
    base_rules = get_base_rules()
    
    # Load SQL patterns from file system
    sql_patterns = load_all_sql_files_from_directory("order_ratings")
    
    # Replace placeholders in patterns
    for pattern_name, pattern_text in sql_patterns.items():
        if rules_service:
            # Use the service's replace_placeholders method that takes a dictionary
            temp_dict = {pattern_name: pattern_text}
            result_dict = rules_service.replace_placeholders(temp_dict, {
                "DEFAULT_LOCATION_ID": str(DEFAULT_LOCATION_ID),
                "TIMEZONE_OFFSET": str(TIMEZONE_OFFSET),
            })
            sql_patterns[pattern_name] = result_dict[pattern_name]
        else:
            # Use the local replace_placeholders function that takes a string
            sql_patterns[pattern_name] = replace_placeholders(
                pattern_text,
                {
                    "DEFAULT_LOCATION_ID": str(DEFAULT_LOCATION_ID),
                    "TIMEZONE_OFFSET": str(TIMEZONE_OFFSET),
                }
            )
    
    return {
        "name": "order_ratings",
        "description": "Rules for order ratings queries",
        "schema": ORDER_RATINGS_SCHEMA,
        "query_rules": ORDER_RATINGS_RULES,
        "base_rules": base_rules,
        "query_patterns": sql_patterns,
    }
