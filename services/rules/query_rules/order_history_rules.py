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
    "items": {
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
    "critical_requirements": {
        "location_isolation": "EVERY SQL query MUST include 'o.location_id = " + str(DEFAULT_LOCATION_ID) + "' in the WHERE clause without exception",
        "date_field_critical": "CRITICAL: The orders table does NOT have an updated_at column. Always use (o.updated_at - INTERVAL '7 hours')::date for date filtering - NEVER reference o.updated_at!"
    },
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
        "date_field": "CRITICAL: Always use o.updated_at for date filtering, NOT o.updated_at (which doesn't exist). Format as: (o.updated_at - INTERVAL '7 hours')::date"
    }
}

# SQL examples for order history queries
ORDER_HISTORY_SQL_EXAMPLES = [
  {
    "query": "Specific date orders",
    "sql": "SELECT \n    COUNT(*) as order_count\nFROM \n    orders o\nWHERE \n    o.location_id = 62\n    AND o.status = 7\n    AND (o.updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY');\n\nSELECT\n    o.id AS order_id,\n    u.first_name || ' ' || u.last_name AS customer_name,\n    o.total AS order_total,\n    to_char((o.updated_at - INTERVAL '7 hours'), 'YYYY-MM-DD HH24:MI:SS') AS updated_at,\n    o.status AS order_status\nFROM \n    orders o\nJOIN \n    users u ON o.customer_id = u.id\nWHERE \n    o.location_id = 62\n    AND o.status = 7\n    AND (o.updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY')\nORDER BY \n    o.updated_at;"
  },
  {
    "query": "Yesterdays order details",
    "sql": "SELECT\n    o.id AS order_id,\n    to_char(o.updated_at - INTERVAL '7 hours', 'YYYY-MM-DD HH24:MI') AS updated_at,\n    u.first_name || ' ' || u.last_name AS customer,\n    regexp_replace(u.phone, '(\\d{3})(\\d{3})(\\d{4})', '(\\1) \\2-\\3') AS user_phone,\n    u.email AS user_email,\n    o.total AS order_total,\n    CAST(o.tip AS DECIMAL(10,2)) as tip,\n    COALESCE(d.amount, 0) as discount_amount,\n    o.status AS order_status\nFROM orders o\nINNER JOIN users u ON o.customer_id = u.id\nINNER JOIN locations l ON l.id = o.location_id\nLEFT JOIN discounts d on d.order_id = o.id\nWHERE l.id = 62\n  AND o.status = 7\n  AND (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE - INTERVAL '1 day';"
  },
  {
    "query": "Monthly sales revenue",
    "sql": "SELECT COALESCE(SUM(total), 0) as total_revenue\nFROM orders\nWHERE location_id = 62\n  AND (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'\n  AND status = 7;"
  },
  {
    "query": "Current month revenue",
    "sql": "SELECT COALESCE(SUM(total), 0) as current_month_revenue\nFROM orders\nWHERE location_id = 62\n  AND date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE)\n  AND status = 7;"
  },
  {
    "query": "Last year same month revenue",
    "sql": "SELECT COALESCE(SUM(total), 0) as last_year_same_month_revenue\nFROM orders\nWHERE location_id = 62\n  AND date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE - INTERVAL '1 year')\n  AND status = 7;"
  },
  {
    "query": "Top menu items by revenue",
    "sql": "SELECT i.name as menu_item, COUNT(oi.id) as order_count,\n       COALESCE(SUM(i.price * oi.quantity), 0) as revenue\nFROM orders o\nJOIN order_items oi ON o.id = oi.order_id\nJOIN items i ON oi.item_id = i.id\nWHERE o.location_id = 62\n  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '3 months'\n  AND o.status = 7\nGROUP BY i.name\nORDER BY revenue DESC\nLIMIT 5;"
  },
  {
    "query": "New customers past week",
    "sql": "WITH first_orders AS (\n    SELECT customer_id, MIN((updated_at - INTERVAL '7 hours')::date) as first_updated_at\n    FROM orders\n    WHERE location_id = 62\n      AND status = 7\n    GROUP BY customer_id\n)\nSELECT COUNT(*) as new_customers\nFROM first_orders\nWHERE first_updated_at >= CURRENT_DATE - INTERVAL '7 days';"
  },
  {
    "query": "Percentage repeat customer orders",
    "sql": "WITH customer_orders AS (\n    SELECT customer_id, COUNT(*) as order_count\n    FROM orders\n    WHERE location_id = 62\n      AND status = 7\n    GROUP BY customer_id\n),\nrepeat_customers AS (\n    SELECT customer_id\n    FROM customer_orders\n    WHERE order_count > 1\n)\nSELECT \n    ROUND(\n        (SELECT COUNT(*) FROM orders o \n         WHERE o.location_id = 62 AND o.status = 7 \n           AND o.customer_id IN (SELECT customer_id FROM repeat_customers)\n        ) * 100.0\n        / NULLIF((SELECT COUNT(*) FROM orders o \n                  WHERE o.location_id = 62 AND o.status = 7), 0),\n        0\n    ) || '%' AS repeat_percentage;"
  },
  {
    "query": "Canceled orders past month",
    "sql": "SELECT COUNT(*) as canceled_orders\nFROM orders\nWHERE location_id = 62\n  AND (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'\n  AND status IN (6);"
  },
  {
    "query": "Avg time between orders",
    "sql": "WITH first_two_orders AS (\n  SELECT customer_id, created_at,\n         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at) AS order_num\n  FROM orders\n  WHERE location_id = 62\n    AND status = 7\n),\nfirst_second AS (\n  SELECT customer_id,\n         MIN(CASE WHEN order_num = 1 THEN created_at END) AS first_order,\n         MIN(CASE WHEN order_num = 2 THEN created_at END) AS second_order\n  FROM first_two_orders\n  GROUP BY customer_id\n)\nSELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (second_order - first_order))/(3600*24)))\n       AS average_days_between_first_and_second\nFROM first_second\nWHERE second_order IS NOT NULL;"
  },
  {
    "query": "Lifetime customer value",
    "sql": "SELECT TO_CHAR(AVG(total_spent), 'FM$999,999,990.00') as avg_lifetime_value\nFROM (\n    SELECT customer_id, SUM(total) as total_spent\n    FROM orders\n    WHERE location_id = 62\n      AND status = 7\n    GROUP BY customer_id\n) sub;"
  },
  {
    "query": "Order details with discount",
    "sql": "SELECT\n    l.id,\n    l.name as location_name,\n    o.id AS order_id,\n    o.status AS order_status,\n    o.total AS order_total,\n    u.id AS user_id,\n    u.phone AS user_phone,\n    u.email AS user_email,\n    o.updated_at - INTERVAL '7 hours' AS updated_at,\n    o.tip as tip,\n    u.first_name || ' ' || u.last_name AS customer,\n    d.amount as discount_amount\nFROM orders o\nINNER JOIN users u ON o.customer_id = u.id\nINNER JOIN locations l ON l.id = o.location_id\nLEFT JOIN discounts d on d.order_id = o.id\nWHERE l.id = 62\n  AND o.status = 7\n  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 day'\n  AND d.amount > 0;"
  },
  {
    "query": "Customer order frequency",
    "sql": "WITH customer_orders AS (\n    SELECT\n        o.customer_id,\n        u.first_name || ' ' || u.last_name AS customer_name,\n        u.phone,\n        u.email,\n        COUNT(o.id) AS total_orders,\n        MIN(o.updated_at) AS first_updated_at,\n        MAX(o.updated_at) AS last_updated_at,\n        AVG(o.total) AS avg_order_value,\n        SUM(o.total) AS total_spent\n    FROM\n        orders o\n    JOIN\n        users u ON o.customer_id = u.id\n    WHERE\n        o.location_id = 62\n        AND o.status = 7\n        AND o.updated_at >= CURRENT_DATE - INTERVAL '180 days'\n    GROUP BY\n        o.customer_id, u.first_name, u.last_name, u.phone, u.email\n    HAVING\n        COUNT(o.id) >= 3\n)\nSELECT\n    customer_name,\n    phone,\n    email,\n    total_orders,\n    to_char(first_updated_at, 'YYYY-MM-DD') AS first_order_date,\n    to_char(last_updated_at, 'YYYY-MM-DD') AS last_order_date,\n    ROUND(avg_order_value / 100.0, 2) AS avg_order_value,\n    ROUND(total_spent / 100.0, 2) AS total_spent,\n    ROUND(EXTRACT(EPOCH FROM (last_updated_at - first_updated_at)) / 86400 / total_orders, 1) AS avg_days_between_orders\nFROM\n    customer_orders\nORDER BY\n    total_orders DESC;"
  },
  {
    "query": "Order item combination analysis",
    "sql": "WITH order_items_list AS (\n    SELECT\n        o.id AS order_id,\n        o.updated_at AS updated_at,\n        i1.id AS item1_id,\n        i1.name AS item1_name,\n        i2.id AS item2_id,\n        i2.name AS item2_name\n    FROM\n        orders o\n    JOIN\n        order_items oi1 ON o.id = oi1.order_id\n    JOIN\n        items i1 ON oi1.item_id = i1.id\n    JOIN\n        order_items oi2 ON o.id = oi2.order_id\n    JOIN\n        items i2 ON oi2.item_id = i2.id\n    WHERE\n        o.location_id = 62\n        AND o.status = 7\n        AND o.updated_at >= CURRENT_DATE - INTERVAL '90 days'\n        AND i1.id < i2.id\n),\nitem_pairs AS (\n    SELECT\n        item1_name,\n        item2_name,\n        COUNT(DISTINCT order_id) AS times_ordered_together\n    FROM\n        order_items_list\n    GROUP BY\n        item1_name, item2_name\n    HAVING\n        COUNT(DISTINCT order_id) >= 3\n)\nSELECT\n    item1_name,\n    item2_name,\n    times_ordered_together\nFROM\n    item_pairs\nORDER BY\n    times_ordered_together DESC\nLIMIT 10;"
  },
  {
    "query": "Cancelled orders",
    "sql": "SELECT\n    o.id AS order_id,\n    to_char(o.updated_at - INTERVAL '7 hours', 'YYYY-MM-DD HH24:MI') AS updated_at,\n    u.first_name || ' ' || u.last_name AS customer,\n    regexp_replace(u.phone, '(\\d{3})(\\d{3})(\\d{4})', '(\\1) \\2-\\3') AS user_phone,\n    u.email AS user_email,\n    o.total AS order_total,\n    CAST(o.tip AS DECIMAL(10,2)) as tip,\n    COALESCE(d.amount, 0) as discount_amount,\n    o.status AS order_status\nFROM orders o\nINNER JOIN users u ON o.customer_id = u.id\nINNER JOIN locations l ON l.id = o.location_id\nLEFT JOIN discounts d on d.order_id = o.id\nWHERE l.id = 62\n  AND o.status = 6\n  AND o.updated_at > CURRENT_TIMESTAMP - INTERVAL '1 day'"
  }
]


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
    
    # Add a critical requirement specifically for location filtering and date field
    if "critical_requirements" not in modified_rules:
        modified_rules["critical_requirements"] = {}
    modified_rules["critical_requirements"]["location_isolation"] = f"EVERY SQL query MUST include 'o.location_id = {DEFAULT_LOCATION_ID}' in the WHERE clause without exception"
    modified_rules["critical_requirements"]["date_field"] = "CRITICAL: The orders table does NOT have an updated_at column. Always use (o.updated_at - INTERVAL '7 hours')::date for date filtering - NEVER reference o.updated_at!"
    
    return {
        "name": "order_history",
        "description": "Rules for order history queries",
        "schema": ORDER_HISTORY_SCHEMA,
        "query_rules": modified_rules,  # Use the modified rules with explicit location ID
        "base_rules": base_rules,
        "query_patterns": sql_patterns,
        "sql_examples": ORDER_HISTORY_SQL_EXAMPLES  # Use the hardcoded examples
    }

def get_sql_examples():
    """
    Get SQL examples for order history queries.
    
    Returns:
        List of dictionaries containing 'query' and 'sql' pairs for examples
    """
    # Return the hardcoded examples directly
    return ORDER_HISTORY_SQL_EXAMPLES
