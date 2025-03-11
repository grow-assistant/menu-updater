SELECT COALESCE(SUM(total), 0) as last_year_same_month_revenue
FROM orders
WHERE location_id = 62
  AND date_trunc('month', (updated_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE - INTERVAL '1 year')
  AND status = 7; 