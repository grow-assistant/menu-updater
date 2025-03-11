
SELECT
  u.first_name || ' ' || u.last_name AS customer_name,
  SUM(o.total) AS total_spent
FROM
  orders o
JOIN
  users u ON o.customer_id = u.id
WHERE
  o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date BETWEEN date_trunc('month', current_date - interval '1 month') AND date_trunc('month', current_date) - interval '1 day'
GROUP BY
  u.id, u.first_name, u.last_name
ORDER BY
  total_spent DESC
LIMIT 1; 