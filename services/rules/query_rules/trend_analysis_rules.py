"""
Rules specific to trend analysis queries.
"""

from typing import Dict, Any
from services.rules.base_rules import get_base_rules
from services.rules.query_rules import (
    replace_placeholders,
    load_all_sql_files_from_directory,
)
from services.rules.business_rules import DEFAULT_LOCATION_ID, TIMEZONE_OFFSET

# Schema information for trend analysis queries
TREND_ANALYSIS_SCHEMA = {
    "orders": {
        "description": "Main orders table for trend analysis",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "customer_id": "INTEGER - Foreign key to users table (users.id)",
            "vendor_id": "INTEGER - Foreign key to users table (users.id)",
            "location_id": "INTEGER - Foreign key to locations table (locations.id)",
            "status": "INTEGER - Order status (7=completed, 6=cancelled, 3-5=in progress)",
            "total": "NUMERIC - Total order amount",
            "tax": "NUMERIC - Tax amount",
            "instructions": "TEXT - Special instructions for the order",
            "type": "INTEGER - Order type identifier",
            "marker_id": "INTEGER - Foreign key to markers table (markers.id)",
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
    "order_items": {
        "description": "Individual items within an order for trend analysis",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "order_id": "INTEGER - Foreign key to orders table",
            "item_id": "INTEGER - Foreign key to items table",
            "quantity": "INTEGER - Number of this item ordered",
            "instructions": "TEXT - Special instructions for this item",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the record was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the record was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the record was deleted (if applicable)"
        },
        "relationships": [
            "FOREIGN KEY (order_id) REFERENCES orders(id)",
            "FOREIGN KEY (item_id) REFERENCES items(id)"
        ]
    },
    "items": {
        "description": "Menu items for trend analysis",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "category_id": "INTEGER - Foreign key to categories table",
            "name": "TEXT - Name of the menu item",
            "description": "TEXT - Description of the menu item",
            "price": "NUMERIC - Price of the item",
            "disabled": "BOOLEAN - Whether the item is currently available",
            "seq_num": "INTEGER - Display sequence number (default 0)",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the item was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the item was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the item was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (category_id) REFERENCES categories(id)"]
    },
    "discounts": {
        "description": "Discounts applied to orders",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "order_id": "INTEGER - Foreign key to orders table",
            "user_id": "INTEGER - Foreign key to users table",
            "amount": "NUMERIC - Discount amount",
            "reason": "TEXT - Reason for discount",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the discount was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the discount was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the discount was deleted (if applicable)"
        }
    },
    "users": {
        "description": "User information for customers and vendors",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "first_name": "TEXT - User's first name",
            "last_name": "TEXT - User's last name",
            "email": "TEXT - User's email address",
            "phone": "TEXT - User's phone number",
            "picture": "TEXT - User's profile picture URL",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the user was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the user was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the user was deleted (if applicable)"
        }
    }
}

# Trend analysis query rules
TREND_ANALYSIS_RULES = {
    "general": {
        "order_status_filter": "Only include completed orders (status = 7) for consistent performance analysis",
        "time_period_required": "Performance queries MUST be scoped to a specific time period (e.g., 'last 7 days', 'this month')",
        "location_filter": "ALWAYS filter by orders.location_id = [LOCATION_ID] for security and data isolation",
        "aggregation_groups": "When aggregating data, use meaningful groups like: daily trends, time of day, day of week, customer segments, or item categories",
        "revenue_calculation": "For accurate revenue calculations always use: SUM(orders.total - COALESCE(orders.tip, 0))",
        "averages": "When calculating averages, ALWAYS include the count of records used (n) and handle NULL values appropriately",
        "statistic_requirements": "For performance metrics ALWAYS include: 1) Total count 2) Sum/aggregate 3) Average 4) Percent of total where applicable",
        "sorting": "For ranked performance data, use ORDER BY with the primary metric DESC and LIMIT to an appropriate number of results (typically 5-10 for top performers)"
        }
    }

# Standard performance metrics to include
PERFORMANCE_METRICS = {
    "order_counts": "COUNT(DISTINCT orders.id)",
    "revenue": "SUM(orders.total - COALESCE(orders.tip, 0))",
    "average_order_value": "AVG(orders.total - COALESCE(orders.tip, 0))",
    "average_prep_time": "AVG(EXTRACT(EPOCH FROM (orders.updated_at - orders.confirmed_at)) / 60)",
    "order_completion_rate": "COUNT(CASE WHEN orders.status = 7 THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100",
    "cancellation_rate": "COUNT(CASE WHEN orders.status = 6 THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100"
}

def get_rules(rules_service=None) -> Dict[str, Any]:
    """
    Get rules for trend analysis queries.
    
    Args:
        rules_service: Optional reference to the RulesService instance
    
    Returns:
        Dictionary containing rules, patterns, and examples for trend analysis queries
    """
    base_rules = get_base_rules()
    
    # Load SQL patterns from file system
    sql_patterns = load_all_sql_files_from_directory("trend_analysis")
    
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
        "name": "trend_analysis",
        "description": "Rules for trend analysis queries",
        "schema": TREND_ANALYSIS_SCHEMA,
        "query_rules": TREND_ANALYSIS_RULES,
        "base_rules": base_rules,
        "metrics": PERFORMANCE_METRICS,
        "query_patterns": sql_patterns,
    }
