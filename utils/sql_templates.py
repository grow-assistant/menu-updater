"""
SQL query templates for common analytics queries.

This module provides pre-defined SQL query templates that can be
used across the application to ensure consistency and maintainability.
"""

# Standard query templates
DAY_OF_WEEK_QUERY = """
SELECT
  EXTRACT(DOW FROM (o.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'US/Eastern')) AS day_of_week,
  COUNT(o.id) AS order_count
FROM orders AS o
JOIN locations AS l
  ON o.location_id = l.id
WHERE
  o.location_id = {location_id}
  AND o.status = 7
GROUP BY
  day_of_week
ORDER BY
  order_count DESC
LIMIT 7;
"""

FULFILLMENT_TIME_QUERY = """
SELECT
  AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)) / 60) AS average_fulfillment_time_minutes
FROM orders AS o
JOIN locations AS l
  ON o.location_id = l.id
WHERE
  o.location_id = {location_id}
  AND o.status = 7
  AND o.updated_at >= NOW() - INTERVAL '{days} days';
"""

DELIVERY_FULFILLMENT_TIME_QUERY = """
SELECT
  AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)) / 60) AS average_fulfillment_time_minutes
FROM orders AS o
JOIN locations AS l
  ON o.location_id = l.id
WHERE
  o.location_id = {location_id}
  AND o.status = 7
  AND o.order_type = 'delivery'
  AND o.updated_at >= NOW() - INTERVAL '{days} days';
"""

CANCELED_ORDERS_QUERY = """
SELECT
  COUNT(o.id) AS canceled_order_count
FROM orders AS o
JOIN locations AS l
  ON o.location_id = l.id
WHERE
  o.location_id = {location_id}
  AND (o.status = 8 OR o.status = 9)  -- Assuming 8=canceled, 9=refunded
  AND o.updated_at >= NOW() - INTERVAL '{days} days';
"""

CANCELLATION_REASONS_QUERY = """
SELECT
  o.cancellation_reason AS reason,
  COUNT(o.id) AS count
FROM orders AS o
JOIN locations AS l
  ON o.location_id = l.id
WHERE
  o.location_id = {location_id}
  AND (o.status = 8 OR o.status = 9)  -- Assuming 8=canceled, 9=refunded
  AND o.updated_at >= NOW() - INTERVAL '{days} days'
GROUP BY
  o.cancellation_reason
ORDER BY
  count DESC;
"""


def get_sql_template(template_name, **kwargs):
    """
    Get a SQL template with the given parameters applied.

    Args:
        template_name: The name of the template to retrieve
        **kwargs: Parameters to apply to the template

    Returns:
        str: The formatted SQL query
    """
    templates = {
        "day_of_week": DAY_OF_WEEK_QUERY,
        "fulfillment_time": FULFILLMENT_TIME_QUERY,
        "delivery_fulfillment_time": DELIVERY_FULFILLMENT_TIME_QUERY,
        "canceled_orders": CANCELED_ORDERS_QUERY,
        "cancellation_reasons": CANCELLATION_REASONS_QUERY,
    }

    if template_name not in templates:
        raise ValueError(f"Unknown SQL template: {template_name}")

    return templates[template_name].format(**kwargs)
