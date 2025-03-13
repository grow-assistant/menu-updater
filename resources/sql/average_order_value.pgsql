-- Average order value analysis
SELECT 
    ROUND(AVG(total), 2) AS average_order_value,
    MIN(total) AS minimum_order,
    MAX(total) AS maximum_order,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total) AS median_order_value,
    COUNT(*) AS total_orders
FROM 
    orders
WHERE 
    updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND location_id = 62
    AND status = 7
    AND deleted_at IS NULL; 