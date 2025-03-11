-- Get the customer with the highest number of orders
-- Important: Use o.id (not o.order_id) for counting orders

SELECT
  u.first_name || ' ' || u.last_name AS customer_name,
  COUNT(o.id) AS total_orders  -- Use o.id to count orders, o.order_id doesn't exist
FROM
  orders o
JOIN
  users u ON o.customer_id = u.id  -- Important: Join using o.customer_id, not o.user_id
WHERE
  o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date BETWEEN date_trunc('month', current_date - interval '1 month') AND date_trunc('month', current_date) - interval '1 day'
GROUP BY
  u.id, u.first_name, u.last_name
ORDER BY
  total_orders DESC
LIMIT 1; 