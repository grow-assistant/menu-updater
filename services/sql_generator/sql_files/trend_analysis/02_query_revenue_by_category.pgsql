SELECT c.name AS category,
       COUNT(DISTINCT o.id) AS order_count,
       SUM(oi.quantity * i.price) AS total_revenue,
       ROUND(AVG(i.price), 2) AS average_price
FROM categories c
JOIN items i ON c.id = i.category_id
JOIN order_items oi ON i.id = oi.item_id
JOIN orders o ON oi.order_id = o.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND (o.updated_at - INTERVAL '7 hours') >= (CURRENT_DATE - INTERVAL '90 days')
  AND o.status = 7
  AND i.price > 0
GROUP BY c.name
ORDER BY total_revenue DESC;