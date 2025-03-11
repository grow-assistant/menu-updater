"""
Rules specific to popular items queries.
"""

from typing import Dict, Any
from services.rules.base_rules import get_base_rules
from services.rules.query_rules import (
    replace_placeholders,
    load_all_sql_files_from_directory,
)
from services.rules.business_rules import DEFAULT_LOCATION_ID, TIMEZONE_OFFSET

# Schema information for popular items queries
POPULAR_ITEMS_SCHEMA = {
    "orders": {
        "description": "Main orders table for popularity analysis",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "customer_id": "INTEGER - Foreign key to users table (customer)",
            "vendor_id": "INTEGER - Foreign key to users table (vendor)",
            "location_id": "INTEGER - Foreign key to locations table",
            "status": "INTEGER - Order status (7=completed, 6=cancelled, 3-5=in progress)",
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
    "order_items": {
        "description": "Individual items within an order for popularity analysis",
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
        "description": "Menu items for popularity analysis",
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
    "categories": {
        "description": "Menu categories for grouping items",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "menu_id": "INTEGER - Foreign key to menus table",
            "name": "TEXT - Name of the category",
            "description": "TEXT - Description of the category",
            "disabled": "BOOLEAN - Whether the category is disabled",
            "start_time": "SMALLINT - Time when category becomes available",
            "end_time": "SMALLINT - Time when category becomes unavailable",
            "seq_num": "INTEGER - Display sequence number (default 0)",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the category was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the category was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the category was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (menu_id) REFERENCES menus(id)"]
    }
}

# Popular items query rules
POPULAR_ITEMS_RULES = {
    "general": {
        "completed_orders_only": "Only include completed orders (status = 7) for accurate popularity metrics",
        "time_period": "Filter by time period to show recent popularity (e.g., last 30 days, last 3 months)",
        "location_filter": "ALWAYS filter by orders.location_id = [LOCATION_ID]",
        "join_structure": "Join orders to order_items to items to categories for complete data",
        "quantity_aggregation": "Use SUM(order_items.quantity) to account for multiple quantities of the same item in orders",
        "popularity_metrics": "Include multiple metrics: order count, total quantity, revenue, percentage of total",
        "ordering": "Order by the primary popularity metric (quantity or revenue) in descending order",
        "null_handling": "Handle NULL values appropriately in all aggregations"
    }
}

def get_rules(rules_service=None) -> Dict[str, Any]:
    """
    Get rules for popular items queries.
    
    Args:
        rules_service: Optional reference to the RulesService instance
    
    Returns:
        Dictionary containing rules, patterns, and examples for popular items queries
    """
    base_rules = get_base_rules()
    
    # Load SQL patterns from file system
    sql_patterns = load_all_sql_files_from_directory("popular_items")
    
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
        "name": "popular_items",
        "description": "Rules for popular items queries",
        "schema": POPULAR_ITEMS_SCHEMA,
        "query_rules": POPULAR_ITEMS_RULES,
        "base_rules": base_rules,
        "query_patterns": sql_patterns,
    }
