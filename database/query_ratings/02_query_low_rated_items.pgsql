-- Query low rated items (less than 5 rating)
SELECT 
    i.id, 
    i.name, 
    AVG(orf.value) AS average_rating,
    COUNT(orf.id) AS review_count,
    ROUND(COUNT(CASE WHEN orf.value >= 4 THEN 1 END)::NUMERIC / 
          NULLIF(COUNT(orf.id), 0) * 100, 2) AS positive_percentage,
    AVG(CASE WHEN rc.label = 'How was your food?' THEN orf.value ELSE NULL END) AS avg_food_rating,
    AVG(CASE WHEN rc.label = 'How was your service?' THEN orf.value ELSE NULL END) AS avg_service_rating,
    AVG(CASE WHEN rc.label = 'How was your order experience?' THEN orf.value ELSE NULL END) AS avg_experience_rating,
    COUNT(DISTINCT o.id) AS total_orders
FROM items i
JOIN order_items oi ON i.id = oi.item_id
JOIN orders o ON oi.order_id = o.id
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
LEFT JOIN order_ratings r ON o.id = r.order_id
LEFT JOIN order_ratings_feedback orf ON r.id = orf.rating_id
LEFT JOIN rating_categories rc ON rc.id = orf.category_id
WHERE m.location_id = 62
  AND i.disabled = FALSE
  AND o.status = 7
GROUP BY i.id, i.name
HAVING COUNT(orf.id) > 0 AND AVG(orf.value) < 5
ORDER BY average_rating ASC, review_count DESC;