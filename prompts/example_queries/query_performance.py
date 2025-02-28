"""
Example queries for analyzing business performance metrics.
"""

QUERY_PERFORMANCE_QUERIES = """
These example queries demonstrate how to analyze business performance:

1. Average order value over the past six months:
--------------------------------------------------
SELECT COALESCE(AVG(total), 0) as avg_order_value
FROM orders
WHERE location_id = 62
  AND (created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '6 months'
  AND status = 7;

2. Peak ordering hours (top 3):
--------------------------------------------------
SELECT EXTRACT(HOUR FROM (created_at - INTERVAL '7 hours')) as order_hour,
       COUNT(*) as order_count
FROM orders
WHERE location_id = 62
GROUP BY order_hour
ORDER BY order_count DESC
LIMIT 3;

3. Days of the week with highest order volume:
--------------------------------------------------
SELECT TRIM(TO_CHAR((created_at - INTERVAL '7 hours'), 'Day')) as order_day,
       COUNT(*) as order_count
FROM orders
WHERE location_id = 62
GROUP BY TRIM(TO_CHAR((created_at - INTERVAL '7 hours'), 'Day'))
ORDER BY order_count DESC;

4. Average fulfillment time (minutes):
--------------------------------------------------
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))/60 
       AS avg_fulfillment_time_minutes
FROM orders
WHERE location_id = 62
  AND status = 7
  AND (updated_at - created_at) BETWEEN INTERVAL '5 minutes' AND INTERVAL '4 hours';

5. Average delivery time (minutes) for app orders:
--------------------------------------------------
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))/60 
       AS avg_delivery_time_minutes
FROM orders
WHERE location_id = 62
  AND status = 7
  AND type = 1
  AND (updated_at - created_at) BETWEEN INTERVAL '5 minutes' AND INTERVAL '4 hours';

6. Menu categories with highest sales:
--------------------------------------------------
SELECT c.name as category, COUNT(DISTINCT o.id) as order_count,
       COALESCE(SUM(oi.quantity * i.price), 0) as total_revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN items i ON oi.item_id = i.id
JOIN categories c ON i.category_id = c.id
WHERE o.location_id = 62
  AND o.status = 7
GROUP BY c.name
ORDER BY total_revenue DESC;

7. Average order time with proper NULL handling:
--------------------------------------------------
SELECT 
    COALESCE(AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at))), 0)/60 AS avg_order_time_minutes,
    MIN(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)))/60 AS min_order_time_minutes,
    MAX(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)))/60 AS max_order_time_minutes,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT CASE WHEN (o.updated_at - o.created_at) IS NULL THEN o.id END) AS orders_with_null_time
FROM orders o
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
  AND (o.updated_at - o.created_at) BETWEEN INTERVAL '1 minute' AND INTERVAL '180 minutes';

8. Orders with specific items that have a zero value:
--------------------------------------------------
SELECT 
    o.id AS order_id,
    o.updated_at - INTERVAL '7 hours' AS order_time,
    i.name AS item_name,
    COALESCE(oi.price, 0) AS item_price,
    CASE 
        WHEN oi.price IS NULL OR oi.price = 0 THEN 'Yes' 
        ELSE 'No' 
    END AS is_zero_price
FROM orders o
INNER JOIN order_items oi ON o.id = oi.order_id
INNER JOIN items i ON oi.item_id = i.id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
  AND (oi.price IS NULL OR oi.price = 0)
ORDER BY o.updated_at DESC;
""" 