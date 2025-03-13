-- Top 5 most ordered items by quantity
SELECT 
    i.name AS item_name,
    SUM(oi.quantity) AS total_quantity_ordered,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(oi.quantity * i.price) AS total_revenue
FROM 
    orders o
JOIN 
    order_items oi ON o.id = oi.order_id
JOIN 
    items i ON oi.item_id = i.id
WHERE 
    o.updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND o.updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND o.location_id = 62
    AND o.status = 7
    AND o.deleted_at IS NULL
    AND oi.deleted_at IS NULL
    AND i.deleted_at IS NULL
GROUP BY 
    i.name
ORDER BY 
    total_quantity_ordered DESC
LIMIT 5; 