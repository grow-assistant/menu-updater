"""
Customer-specific business rules and definitions.
These rules can be customized for each customer implementation.
"""

from prompts.system_rules import ORDER_STATUS, RATING_SIGNIFICANCE

# Customer-specific business metrics and KPIs
BUSINESS_METRICS = {
    "target_daily_orders": 100,
    "target_daily_revenue": 2500.00,
    "target_avg_order_value": 25.00,
    "target_customer_rating": 4.5,
    "high_value_threshold": 50.00,
    "low_value_threshold": 15.00
}

# Default location ID for all queries
DEFAULT_LOCATION_ID = 62

# Time period filter guidance for Gemini
# This provides guidance on how to construct time filters in SQL queries
TIME_PERIOD_GUIDANCE = {
    "today": "DATE(TIMEZONE('EST', NOW())) = CURRENT_DATE AND location_id = [LOCATION_ID]",
    "yesterday": "DATE(TIMEZONE('EST', NOW())) = CURRENT_DATE - INTERVAL '1 day' AND location_id = [LOCATION_ID]",
    "this_week": "DATE_TRUNC('week', TIMEZONE('EST', NOW())) = DATE_TRUNC('week', CURRENT_DATE) AND location_id = [LOCATION_ID]",
    "last_week": "DATE_TRUNC('week', TIMEZONE('EST', NOW())) = DATE_TRUNC('week', CURRENT_DATE - INTERVAL '7 days') AND location_id = [LOCATION_ID]",
    "this_month": "DATE_TRUNC('month', TIMEZONE('EST', NOW())) = DATE_TRUNC('month', CURRENT_DATE) AND location_id = [LOCATION_ID]",
    "last_month": "DATE_TRUNC('month', TIMEZONE('EST', NOW())) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND location_id = [LOCATION_ID]",
    "date_format": "Use 'YYYY-MM-DD' format for specific dates in queries and always include location_id = [LOCATION_ID]"
}

# Order detail fields to include in responses
ORDER_DETAIL_FIELDS = {
    "customer_info": ["full_name", "email", "phone_number"],
    "order_info": ["order_id", "total", "tip", "updated_at"],
    "query_guidance": "For order detail requests, always include u.first_name || ' ' || u.last_name AS full_name, u.email, u.phone, o.id AS order_id, o.total, o.tip, o.updated_at",
    "required_joins": {
        "users": "INNER JOIN users u ON o.customer_id = u.id",
        "locations": "INNER JOIN locations l ON o.location_id = l.id",
        "discounts": "LEFT JOIN discounts d ON d.order_id = o.id"
    }
}

# Get combined business context for AI prompts
def get_business_context():
    """Get combined business context from system and customer-specific rules
    
    Returns:
        dict: Combined business context for AI prompts
    """
    from prompts.system_rules import ORDER_STATUS, RATING_SIGNIFICANCE, ORDER_TYPES
    
    return {
        "order_status": ORDER_STATUS,
        "rating_significance": RATING_SIGNIFICANCE,
        "order_types": ORDER_TYPES,
        "business_metrics": BUSINESS_METRICS,
        "time_period_guidance": TIME_PERIOD_GUIDANCE,
        "default_location_id": DEFAULT_LOCATION_ID,
        "order_detail_fields": ORDER_DETAIL_FIELDS
    }
