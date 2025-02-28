-- Median time between first and second order (days)
WITH first_two_orders AS (
  SELECT customer_id, created_at,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at) AS order_num
  FROM orders
  WHERE location_id = 62
    AND status = 7
),
first_second AS (
  SELECT customer_id,
         MIN(CASE WHEN order_num = 1 THEN created_at END) AS first_order,
         MIN(CASE WHEN order_num = 2 THEN created_at END) AS second_order
  FROM first_two_orders
  GROUP BY customer_id
)
SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (second_order - first_order))/(3600*24)))
       AS average_days_between_first_and_second
FROM first_second
WHERE second_order IS NOT NULL; 