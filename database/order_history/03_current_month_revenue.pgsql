-- This month's sales revenue
SELECT COALESCE(SUM(total), 0) as current_month_revenue
FROM orders
WHERE location_id = 62
  AND date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE)
  AND status = 7; 