-- Busiest day of week for delivery orders
SELECT 
    TO_CHAR(updated_at, 'Day') AS day_of_week,
    EXTRACT(DOW FROM updated_at) AS day_number, -- 0=Sunday, 6=Saturday
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM 
    orders
WHERE 
    updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND location_id = 62
    AND status = 7
    AND deleted_at IS NULL
GROUP BY 
    day_of_week, day_number
ORDER BY 
    day_number; 