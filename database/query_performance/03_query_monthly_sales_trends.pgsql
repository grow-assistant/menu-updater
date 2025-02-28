-- Query revenue by menu category comparing last month to prior month
SELECT 
    c.name AS category,
    SUM(CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE)
        THEN oi.quantity * i.price 
        ELSE 0 
    END) AS last_month_revenue,
    SUM(CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        THEN oi.quantity * i.price 
        ELSE 0 
    END) AS prior_month_revenue,
    COUNT(DISTINCT CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE)
        THEN o.id 
    END) AS last_month_orders,
    COUNT(DISTINCT CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        THEN o.id 
    END) AS prior_month_orders,
    COUNT(DISTINCT CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE)
        THEN o.id 
    END) - COUNT(DISTINCT CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        THEN o.id 
    END) AS order_count_difference,
    ROUND((SUM(CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE)
        THEN oi.quantity * i.price 
        ELSE 0 
    END) - SUM(CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        THEN oi.quantity * i.price 
        ELSE 0 
    END)) / NULLIF(SUM(CASE 
        WHEN (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
        AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        THEN oi.quantity * i.price 
        ELSE 0 
    END), 0) * 100, 2) AS revenue_percent_change
FROM categories c
JOIN items i ON c.id = i.category_id
JOIN order_items oi ON i.id = oi.item_id
JOIN orders o ON oi.order_id = o.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND (o.updated_at - INTERVAL '7 hours') >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 months')
  AND (o.updated_at - INTERVAL '7 hours') < DATE_TRUNC('month', CURRENT_DATE)
  AND o.status = 7
  AND i.price > 0
GROUP BY c.name
ORDER BY last_month_revenue DESC;