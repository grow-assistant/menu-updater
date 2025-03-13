-- Comparison of order volume between current month and previous month
WITH current_month AS (
    SELECT 
        COUNT(*) AS order_count,
        SUM(total) AS revenue
    FROM 
        orders
    WHERE 
        updated_at >= DATE_TRUNC('month', CURRENT_DATE)
        AND location_id = 62
        and status = 7
        AND deleted_at IS NULL
),
previous_month AS (
    SELECT 
        COUNT(*) AS order_count,
        SUM(total) AS revenue
    FROM 
        orders
    WHERE 
        updated_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND updated_at < DATE_TRUNC('month', CURRENT_DATE)
        AND location_id = 62
        and status = 7
        AND deleted_at IS NULL
)
SELECT 
    c.order_count AS current_month_orders,
    p.order_count AS previous_month_orders,
    c.order_count - p.order_count AS order_difference,
    CASE 
        WHEN p.order_count = 0 THEN NULL
        ELSE ROUND((c.order_count - p.order_count)::numeric / p.order_count * 100, 2)
    END AS order_growth_percentage,
    
    c.revenue AS current_month_revenue,
    p.revenue AS previous_month_revenue,
    c.revenue - p.revenue AS revenue_difference,
    CASE 
        WHEN p.revenue = 0 THEN NULL
        ELSE ROUND((c.revenue - p.revenue)::numeric / p.revenue * 100, 2)
    END AS revenue_growth_percentage
FROM 
    current_month c, previous_month p; 