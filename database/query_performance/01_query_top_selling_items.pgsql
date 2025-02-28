-- Query top selling menu items
SELECT i.id, i.name, i.price, c.name AS category, 
       COUNT(oi.order_id) AS order_count,
       SUM(oi.quantity) AS total_quantity,
       SUM(i.price * oi.quantity) AS total_revenue
FROM items i
JOIN order_items oi ON i.id = oi.item_id
JOIN orders o ON oi.order_id = o.id
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND (o.updated_at - INTERVAL '7 hours') >= (CURRENT_DATE - INTERVAL '30 days')
  AND o.status = 7
  AND i.price > 0
GROUP BY i.id, i.name, i.price, c.name
ORDER BY total_quantity DESC
LIMIT 10;