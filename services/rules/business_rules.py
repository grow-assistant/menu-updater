"""
Business rules and configuration for the Restaurant AI Assistant.
These values can be customized per business implementation.
"""

from typing import Dict, Any

# Default location ID used when no specific location is mentioned
DEFAULT_LOCATION_ID: int = 62

# Timezone offset for date calculations (hours)
TIMEZONE_OFFSET: int = 7

# Business-specific metrics and targets
BUSINESS_METRICS: Dict[str, Any] = {
    "target_daily_orders": 100,
    "avg_order_value_target": 25.00,
    "delivery_time_target": 30,
    "rating_target": 4.5,
}

# Business operating hours (24-hour format)
OPERATING_HOURS: Dict[str, Dict[str, str]] = {
    "monday": {"open": "11:00", "close": "22:00"},
    "tuesday": {"open": "11:00", "close": "22:00"},
    "wednesday": {"open": "11:00", "close": "22:00"},
    "thursday": {"open": "11:00", "close": "22:00"},
    "friday": {"open": "11:00", "close": "23:00"},
    "saturday": {"open": "10:00", "close": "23:00"},
    "sunday": {"open": "10:00", "close": "22:00"},
}

# Define promotions and special offers
ACTIVE_PROMOTIONS: Dict[str, Dict[str, Any]] = {
    "happy_hour": {
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "start_time": "16:00",
        "end_time": "18:00",
        "discount": 0.15,  # 15% off
    },
    "weekend_special": {
        "days": ["saturday", "sunday"],
        "items": ["family_meal", "dessert_bundle"],
        "discount": 0.10,  # 10% off
    }
}

# Export commonly used constants
__all__ = [
    "DEFAULT_LOCATION_ID",
    "TIMEZONE_OFFSET",
    "BUSINESS_METRICS",
    "OPERATING_HOURS",
    "ACTIVE_PROMOTIONS",
]