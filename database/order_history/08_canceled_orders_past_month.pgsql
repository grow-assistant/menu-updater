-- Canceled orders in the past month
SELECT COUNT(*) as canceled_orders
FROM orders
WHERE location_id = 62
  AND (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'
  AND status IN (6); 