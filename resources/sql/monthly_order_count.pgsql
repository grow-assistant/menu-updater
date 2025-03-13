-- Total number of orders placed in the past month
SELECT 
    COUNT(*) AS total_orders
FROM 
    orders
WHERE 
    updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND location_id = 62
    AND deleted_at IS NULL
    AND status = 7; 