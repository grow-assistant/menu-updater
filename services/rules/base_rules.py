"""
Base rules and definitions for the Swoop AI application.
These are core system definitions that apply across all customer implementations.
"""

import logging
from typing import Dict, Any, List, Union, Optional, cast
from services.rules.business_rules import DEFAULT_LOCATION_ID, BUSINESS_METRICS

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

ORDER_STATUS: Dict[int, str] = {
    0: "Open",
    1: "Pending",
    2: "Confirmed",
    3: "In Progress",
    4: "Ready",
    5: "In Transit",
    6: "Cancelled",
    7: "Completed",
}

RATING_SIGNIFICANCE: Dict[int, str] = {
    1: "Very Dissatisfied - Critical issue requiring immediate attention",
    2: "Dissatisfied - Significant issues with the experience",
    3: "Neutral - Average experience with some issues",
    4: "Satisfied - Good experience with minor issues",
    5: "Very Satisfied - Excellent experience with no issues",
}

ORDER_TYPES: Dict[int, str] = {1: "Delivery", 2: "Pickup"}

CORE_STATUSES: Dict[str, Union[int, List[int]]] = {
    "completed": 7,
    "cancelled": 6,
    "in_progress": [3, 4, 5],
}

BASE_QUERY_RULES: Dict[str, str] = {
    "date_reference": "Always use CURRENT_DATE in queries to reference today's date for accurate time-based filtering",
    "averages": "When calculating ANY average metric, ALWAYS include the total count of records and the count of non-null values used in the calculation to provide proper context.",
    "sql_validation": "For any query that calculates an average, verify that the SELECT clause includes appropriate COUNT expressions to provide context for the average.",
    "date_conversion": "MANDATORY: For all date comparisons, use (updated_at - INTERVAL '7 hours')::date instead of time zone conversions to maintain consistency with historical data patterns",
    "location_filter": "CRITICAL: Every query MUST include a filter for location_id in the WHERE clause.",
}

ORDER_FILTERS: Dict[str, str] = {
    "time_filter": "Use: (orders.updated_at - INTERVAL '7 hours')::date for date filtering",
    "status_filter": "Always include explicit status filtering: orders.status IN (7) for completed orders",
    "customer_filter": "Use orders.customer_id = users.id when joining to users table for customer information"
}

# Using DEFAULT_LOCATION_ID imported from business_rules.py
# No longer duplicated here

DEFAULT_BUSINESS_METRICS: Dict[str, Any] = BUSINESS_METRICS

# Add schema reference to ensure correct field usage
DATABASE_SCHEMA_REFERENCE = {
    "orders": {
        "primary_key": "id",
        "customer_reference": "customer_id",  # Not user_id
        "related_tables": ["order_items", "order_option_items", "order_ratings", "discounts"],
        "status_field": "status",
        "location_field": "location_id",
        "types": ORDER_TYPES,
        "statuses": ORDER_STATUS
    },
    "locations": {
        "primary_key": "id",
        "related_tables": ["menus", "location_hours", "api_keys", "markers"]
    },
    "users": {
        "primary_key": "id",
        "related_tables": ["identities", "roles"]
    }
}

def get_status_name(status_code: int) -> str:
    """
    Get the human-readable name for an order status code.
    
    Args:
        status_code: The numeric status code
        
    Returns:
        The human-readable status name or 'Unknown Status' if not found
    """
    return ORDER_STATUS.get(status_code, f"Unknown Status ({status_code})")

def get_status_code(status_name: str) -> Optional[int]:
    """
    Get the status code for a status name.
    
    Args:
        status_name: The status name to look up (case-insensitive)
        
    Returns:
        The status code or None if not found
    """
    status_name_lower = status_name.lower()
    for code, name in ORDER_STATUS.items():
        if name.lower() == status_name_lower:
            return code
    return None

def get_order_type_name(type_code: int) -> str:
    """
    Get the human-readable name for an order type code.
    
    Args:
        type_code: The numeric type code
        
    Returns:
        The human-readable type name or 'Unknown Type' if not found
    """
    return ORDER_TYPES.get(type_code, f"Unknown Type ({type_code})")

def get_status_codes_for_category(category: str) -> List[int]:
    """
    Get all status codes for a high-level status category.
    
    Args:
        category: The high-level status category (e.g., 'in_progress')
        
    Returns:
        List of status codes in that category
    """
    if category not in CORE_STATUSES:
        return []
        
    value = CORE_STATUSES[category]
    if isinstance(value, int):
        return [value]
    elif isinstance(value, list):
        return value
    else:
        return []

def is_order_in_category(status_code: int, category: str) -> bool:
    """
    Check if an order status code belongs to a high-level status category.
    
    Args:
        status_code: The numeric status code
        category: The high-level status category (e.g., 'in_progress')
        
    Returns:
        True if the status code belongs to the category, False otherwise
    """
    category_codes = get_status_codes_for_category(category)
    return status_code in category_codes

def get_base_rules() -> Dict[str, Any]:
    """
    Get the base rules that apply to all query types.
    
    Returns:
        Dictionary of base rules
    """
    return {
        "general": BASE_QUERY_RULES,
        "order": ORDER_FILTERS,
        "status_mapping": ORDER_STATUS,
        "rating_significance": RATING_SIGNIFICANCE,
        "order_types": ORDER_TYPES,
        "core_statuses": CORE_STATUSES,
        "default_location_id": DEFAULT_LOCATION_ID,
        "default_metrics": DEFAULT_BUSINESS_METRICS,
    }

# Export commonly used functions and constants
__all__ = [
    "ORDER_STATUS",
    "RATING_SIGNIFICANCE",
    "ORDER_TYPES",
    "CORE_STATUSES",
    "BASE_QUERY_RULES",
    "ORDER_FILTERS",
    "DEFAULT_LOCATION_ID",  # Now imported from business_rules
    "DEFAULT_BUSINESS_METRICS",
    "get_status_name",
    "get_status_code",
    "get_order_type_name",
    "get_status_codes_for_category",
    "is_order_in_category",
    "get_base_rules",
] 