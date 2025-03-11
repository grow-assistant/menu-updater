SELECT i.name as menu_item, COUNT(oi.id) as order_count,
       COALESCE(SUM(i.price * oi.quantity), 0) as revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN items i ON oi.item_id = i.id
WHERE o.location_id = 62
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '3 months'
  AND o.status = 7
GROUP BY i.name
ORDER BY revenue DESC
LIMIT 5; 