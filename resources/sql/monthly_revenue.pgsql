-- Total revenue from orders placed in the past month
SELECT 
    SUM(total) AS total_revenue,
    SUM(tax) AS total_tax,
    SUM(fee) AS total_fees,
    SUM(tip) AS total_tips,
    SUM(total + tax + COALESCE(fee, 0) + COALESCE(tip, 0)) AS gross_revenue
FROM 
    orders
WHERE 
    updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
    AND location_id = 62
    and status = 7
    AND deleted_at IS NULL; 