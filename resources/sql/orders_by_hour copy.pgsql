-- Order distribution by hour of day
SELECT 
    EXTRACT(HOUR FROM updated_at) AS hour_of_day,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage_of_orders
FROM 
    orders
WHERE 
    updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND location_id = 62
    AND status = 7
    AND deleted_at IS NULL
GROUP BY 
    hour_of_day
ORDER BY 
    order_count DESC; 