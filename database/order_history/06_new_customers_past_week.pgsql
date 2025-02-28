-- New customers acquired in the last week
WITH first_orders AS (
    SELECT customer_id, MIN((updated_at - INTERVAL '7 hours')::date) as first_order_date
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
)
SELECT COUNT(*) as new_customers
FROM first_orders
WHERE first_order_date >= CURRENT_DATE - INTERVAL '7 days'; 