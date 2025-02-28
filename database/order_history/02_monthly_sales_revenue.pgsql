-- Total sales revenue for the past month
SELECT COALESCE(SUM(total), 0) as total_revenue
FROM orders
WHERE location_id = 62
  AND (updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'
  AND status = 7; 