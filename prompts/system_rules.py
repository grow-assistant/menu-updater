"""
System rules and definitions for the Swoop application.
These are core system definitions that apply across all customer implementations.
"""

# Order Status Definitions - Core system statuses
ORDER_STATUS = {
    0: "Open",
    1: "Pending",
    2: "Confirmed",
    3: "In Progress",
    4: "Ready",
    5: "In Transit",
    6: "Cancelled",
    7: "Completed",
}

# Rating Significance - For interpreting customer ratings
RATING_SIGNIFICANCE = {
    1: "Very Dissatisfied - Critical issue requiring immediate attention",
    2: "Dissatisfied - Significant issues with the experience",
    3: "Neutral - Average experience with some issues",
    4: "Satisfied - Good experience with minor issues",
    5: "Very Satisfied - Excellent experience with no issues",
}

# Order Types - Core system order types
ORDER_TYPES = {1: "Delivery", 2: "Pickup"}

# Query Rules - Important rules for consistent query handling
QUERY_RULES = {
    "completed_orders": "Always use updated_dt instead of created_dt when querying for completed orders, as completion time is more relevant than creation time",
    "date_reference": "Always use CURRENT_DATE in queries to reference today's date for accurate time-based filtering",
    "order_ratings": "CRITICAL: For rating queries: 1) Always start with orders table 2) LEFT JOIN order_ratings ON orders.id 3) LEFT JOIN order_ratings_feedback ON rating_id 4) Use COUNT(DISTINCT o.id) for totals 5) For averages, handle NULL ratings 6) Include: total_orders, orders_with_ratings, orders_without_ratings, percent_rated 7) Always use (o.updated_at - INTERVAL '7 hours')::date for dates 8) Use DISTINCT in all counts to avoid duplication from multiple ratings",
    "rating_definition": "CRITICAL: An order has a rating ONLY if it has at least one entry in the order_ratings_feedback table (f.id IS NOT NULL). Many orders have entries in the order_ratings table but no actual feedback - these should NOT be counted as rated orders.",
    "averages": "When calculating ANY average metric, ALWAYS include the total count of records and the count of non-null values used in the calculation to provide proper context. This is MANDATORY for all average calculations.",
    "ratings_aggregation": "MANDATORY FOR RATINGS: Include 4 core metrics: 1) COUNT(DISTINCT o.id) AS total_orders 2) COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) AS orders_with_ratings 3) COUNT(DISTINCT CASE WHEN f.id IS NULL THEN o.id END) AS orders_without_ratings 4) percent_rated calculation. Always handle potential NULL values in averages.",
    "rating_joins": "When joining rating tables: 1) orders → order_ratings (LEFT JOIN) 2) order_ratings → order_ratings_feedback (LEFT JOIN) 3) Use DISTINCT ON (rating_id, category_id) with proper sorting when getting latest feedback",
    "rating_error_prevention": "CRITICAL: Prevent rating errors by: 1) Never use COUNT(*) in rating queries 2) Always qualify columns with table aliases (o.id vs id) 3) Handle NULL ratings in averages 4) Use DISTINCT in all aggregate functions 5) Explicitly cast dates with ::date 6) Always check f.id IS NOT NULL, not r.id IS NOT NULL, to count orders with ratings",
    "sql_validation": "For any query that calculates an average, verify that the SELECT clause includes appropriate COUNT expressions to provide context for the average.",
    "date_conversion": "MANDATORY: For all date comparisons, use (updated_at - INTERVAL '7 hours')::date instead of time zone conversions to maintain consistency with historical data patterns",
    "order_detail_requirements": "MANDATORY FOR ORDER DETAILS: 1) Always include u.first_name || ' ' || u.last_name AS full_name, u.email, u.phone 2) Include o.id, o.total, o.tip 3) Show (o.updated_at - INTERVAL '7 hours') AS order_date 4) Always LEFT JOIN discounts d AND include d.amount as discount_amount (NOT o.discount which doesn't exist)",
    "date_filter_requirement": "CRITICAL: Every query MUST include date filtering in the WHERE clause using exactly this pattern: (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE (or specific date). This filter MUST be in the WHERE clause, not just SELECT.",
}
