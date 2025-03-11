"""
Rules specific to order history queries.
"""

from typing import Dict, Any
from services.rules.base_rules import get_base_rules
from services.rules.query_rules import (
    replace_placeholders,
    load_all_sql_files_from_directory,
)
from services.rules.business_rules import DEFAULT_LOCATION_ID, TIMEZONE_OFFSET

# Schema information for order history queries
ORDER_HISTORY_SCHEMA = {
    "orders": {
        "description": "Main orders table containing all order information",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "user_id": "INTEGER - Foreign key to users table (customer), also referred to as customer_id in some queries",
            "customer_id": "INTEGER - Same as user_id, foreign key to users table for the customer",
            "vendor_id": "INTEGER - Foreign key to users table (vendor)",
            "location_id": "INTEGER - Foreign key to locations table",
            "marker_id": "INTEGER - Foreign key to markers table (optional)",
            "status": "INTEGER - Order status (7=completed, 6=cancelled, 3-5=in progress)",
            "total": "INTEGER - Total amount in cents (includes tip)",
            "tax": "INTEGER - Tax amount in cents",
            "tip": "INTEGER - Tip amount in cents (optional)",
            "fee": "INTEGER - Service fee amount in cents",
            "fee_percent": "FLOAT - Service fee percentage",
            "instructions": "TEXT - Special instructions for the order",
            "type": "INTEGER - Order type identifier",
            "updated_at": "TIMESTAMP - When the order was completed",
            "created_at": "TIMESTAMP - When the order was created",
        },
        "relationships": [
            "FOREIGN KEY (user_id) REFERENCES users(id)",
            "FOREIGN KEY (vendor_id) REFERENCES users(id)",
            "FOREIGN KEY (location_id) REFERENCES locations(id)",
            "FOREIGN KEY (marker_id) REFERENCES markers(id)"
        ]
    },
    "order_items": {
        "description": "Individual items within an order",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "order_id": "INTEGER - Foreign key to orders table",
            "item_id": "INTEGER - Foreign key to menu_items table",
            "quantity": "INTEGER - Number of this item ordered",
            "price": "INTEGER - Price at time of order (in cents)",
            "special_instructions": "TEXT - Special instructions for this item",
            "created_at": "TIMESTAMP - When the record was created",
            "updated_at": "TIMESTAMP - When the record was completed",
            "deleted_at": "TIMESTAMP - When the record was deleted (if applicable)"
        },
        "relationships": [
            "FOREIGN KEY (order_id) REFERENCES orders(id)",
            "FOREIGN KEY (item_id) REFERENCES items(id)"
        ]
    },
    "order_option_items": {
        "description": "Options selected for order items",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "order_item_id": "INTEGER - Foreign key to order_items table",
            "option_item_id": "INTEGER - Foreign key to option_items table",
            "price": "INTEGER - Price at time of order (in cents)",
            "quantity": "INTEGER - Quantity of this option selected",
            "created_at": "TIMESTAMP - When the record was created",
            "updated_at": "TIMESTAMP - When the record was completed",
            "deleted_at": "TIMESTAMP - When the record was deleted (if applicable)"
        },
        "relationships": [
            "FOREIGN KEY (order_item_id) REFERENCES order_items(id)",
            "FOREIGN KEY (option_item_id) REFERENCES option_items(id)"
        ]
    },
    "users": {
        "description": "User information for customers and vendors",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "first_name": "TEXT - User's first name",
            "last_name": "TEXT - User's last name",
            "email": "TEXT - User's email address",
            "phone": "TEXT - User's phone number",
            "created_at": "TIMESTAMP - When the user was created",
        },
    },
    "menu_items": {
        "description": "Menu items available for ordering",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "category_id": "INTEGER - Foreign key to menu_categories table",
            "location_id": "INTEGER - Foreign key to locations table",
            "name": "TEXT - Name of the menu item",
            "description": "TEXT - Description of the menu item",
            "price": "INTEGER - Price in cents (e.g., $5.99 is stored as 599)",
            "enabled": "BOOLEAN - Whether the item is currently available",
            "created_at": "TIMESTAMP - When the item was created",
            "updated_at": "TIMESTAMP - When the item was last updated",
        },
    },
    "option_items": {
        "description": "Individual choices within an option group for menu items",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "option_id": "INTEGER - Foreign key to options table",
            "location_id": "INTEGER - Foreign key to locations table",
            "name": "TEXT - Name of the option item",
            "price": "INTEGER - Additional price in cents",
        },
    },
}

# Query rules for order history
ORDER_HISTORY_RULES = {
    "general": {
        "date_filtering": "Use date range filters to narrow down order history: (o.updated_at - INTERVAL '7 hours')::date BETWEEN date1 AND date2",
        "status_filter": "Filter by order status using o.status IN (status_codes) for specific order states",
        "location_filter": "***CRITICAL REQUIREMENT*** ALWAYS filter by o.location_id = " + str(DEFAULT_LOCATION_ID) + " to ensure proper data isolation. This filter is MANDATORY for EVERY query without exception.",
        "join_structure": "Join orders to order_items to items for complete order details",
        "order_by": "Sort by creation date (most recent first) using ORDER BY o.updated_at DESC",
        "items_inclusion": "Use LEFT JOIN to include order_items: LEFT JOIN order_items oi ON o.id = oi.order_id",
        "options_inclusion": "To include options: LEFT JOIN order_option_items ooi ON oi.id = ooi.order_item_id",
        "customer_privacy": "When asked about WHO placed orders, ALWAYS join to the users table and return customer names. Example: JOIN users u ON o.customer_id = u.id and include u.first_name || ' ' || u.last_name AS customer_name in the SELECT clause."
    },
    "order_status": {
        "completed": "Completed orders have status=7",
        "cancelled": "Cancelled orders have status=6",
        "in_progress": "In-progress orders have status between 3-5",
        "validation": "When filtering by status, ensure valid status values are used"
    },
    "performance": {
        "indexes": "Use appropriate indexes on date fields, status, and location_id",
        "large_ranges": "For large date ranges, consider adding appropriate WHERE clauses to utilize indexes",
        "analysis": "Include EXPLAIN when analyzing query performance issues"
    },
    "date_handling": {
        "format_support": "Handle various date formats (MM/DD/YYYY, YYYY-MM-DD) in input parameters",
        "relative_dates": "For 'yesterday', 'last week', 'last month', use date arithmetic relative to current_date",
        "date_comparison": "When comparing dates, cast timestamps to date type for whole-day comparisons",
        "date_field": "CRITICAL: Always use o.updated_at for date filtering, NOT o.order_date (which doesn't exist). Format as: (o.updated_at - INTERVAL '7 hours')::date"
    }
}


def get_rules(rules_service=None) -> Dict[str, Any]:
    """
    Get rules for order history queries.
    
    Args:
        rules_service: Optional reference to the RulesService instance
        
    Returns:
        Dictionary containing rules, patterns, and examples for order history queries
    """
    base_rules = get_base_rules()
    
    # Load SQL patterns from file system
    sql_patterns = load_all_sql_files_from_directory("order_history")
    
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
    
    # Explicitly set a modified version of ORDER_HISTORY_RULES with the actual location ID
    modified_rules = ORDER_HISTORY_RULES.copy()
    modified_rules["general"] = ORDER_HISTORY_RULES["general"].copy()
    modified_rules["general"]["location_filter"] = "***CRITICAL REQUIREMENT*** ALWAYS filter by o.location_id = " + str(DEFAULT_LOCATION_ID) + " to ensure proper data isolation. This filter is MANDATORY for EVERY query without exception."
    
    # Add a critical requirement specifically for location filtering
    if "critical_requirements" not in modified_rules:
        modified_rules["critical_requirements"] = {}
    modified_rules["critical_requirements"]["location_isolation"] = f"EVERY SQL query MUST include 'o.location_id = {DEFAULT_LOCATION_ID}' in the WHERE clause without exception"
    modified_rules["critical_requirements"]["date_field"] = "CRITICAL: The orders table has updated_at field, NOT order_date. Always use (o.updated_at - INTERVAL '7 hours')::date for date filtering."
    
    return {
        "name": "order_history",
        "description": "Rules for order history queries",
        "schema": ORDER_HISTORY_SCHEMA,
        "query_rules": modified_rules,  # Use the modified rules with explicit location ID
        "base_rules": base_rules,
        "query_patterns": sql_patterns,
    }
