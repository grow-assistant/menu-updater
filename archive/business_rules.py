"""
Business rules and definitions for the application.
Each category of rules is organized in its own dictionary for clarity and maintainability.
"""

# Order Status Definitions
ORDER_STATUS = {
    0: "Open",
    1: "Pending",
    2: "Confirmed",
    3: "In Progress",
    4: "Ready",
    5: "In Transit",
    6: "Cancelled",
    7: "Completed"
}

# Detailed descriptions for more context
ORDER_STATUS_DETAILS = {
    0: "Order has been created but not submitted",
    1: "Order has been submitted but not confirmed by restaurant",
    2: "Order has been confirmed by restaurant and is queued",
    3: "Restaurant has started preparing the order",
    4: "Order is ready for pickup or delivery",
    5: "Order is being delivered to customer",
    6: "Order has been cancelled by customer or restaurant",
    7: "Order has been successfully delivered or picked up",
    8: "Order was completed but later refunded"
}

# Rating Significance - For interpreting customer ratings
RATING_SIGNIFICANCE = {
    1: "Very Dissatisfied - Critical issue requiring immediate attention",
    2: "Dissatisfied - Significant issues with the experience",
    3: "Neutral - Average experience with some issues",
    4: "Satisfied - Good experience with minor issues",
    5: "Very Satisfied - Excellent experience with no issues"
}

# Order Filters - Common query conditions
ORDER_FILTERS = {
    "active": "status NOT IN (6, 7, 8)",  # Not cancelled, completed, or refunded
    "completed": "status = 7",
    "cancelled": "status = 6",
    "refunded": "status = 8",
    "in_progress": "status IN (2, 3, 4, 5)",  # Confirmed through In Transit
    "problematic": "status = 7 AND EXISTS (SELECT 1 FROM order_ratings_feedback WHERE order_id = orders.id AND value < 4)",
    "outstanding": "status = 7 AND EXISTS (SELECT 1 FROM order_ratings_feedback WHERE order_id = orders.id AND value = 5)",
    "delivery_orders": "type = 1",
    "pickup_orders": "type = 2",
    "dine_in_orders": "type = 3"
}

# Add common time period filters
TIME_PERIOD_FILTERS = {
    "today": "(updated_at - INTERVAL '7 hours')::date = CURRENT_DATE",
    "yesterday": "(updated_at - INTERVAL '7 hours')::date = CURRENT_DATE - INTERVAL '1 day'",
    "this_week": "(updated_at - INTERVAL '7 hours')::date >= date_trunc('week', CURRENT_DATE)",
    "last_week": "(updated_at - INTERVAL '7 hours')::date BETWEEN date_trunc('week', CURRENT_DATE) - INTERVAL '7 days' AND date_trunc('week', CURRENT_DATE) - INTERVAL '1 day'",
    "this_month": "date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE)",
    "last_month": "date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE - INTERVAL '1 month')",
    "last_30_days": "(updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'",
    "last_90_days": "(updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '90 days'"
}

# Add helper function to get SQL WHERE clause for a given time period
def get_time_period_filter(period_name):
    """Get SQL filter clause for a given time period
    
    Args:
        period_name (str): Name of time period (today, yesterday, this_week, etc.)
        
    Returns:
        str: SQL WHERE clause for the time period
    """
    return TIME_PERIOD_FILTERS.get(period_name.lower().replace(' ', '_'), 
                                   "(updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'") 