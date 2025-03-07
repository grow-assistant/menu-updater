-- Hourly order distribution (hourly_order_distribution)
-- Analysis of order volume by hour of day

SELECT
    EXTRACT(HOUR FROM (o.updated_at - INTERVAL '7 hours')) AS hour_of_day,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders WHERE status = 7 AND location_id = 62), 2) AS percentage_of_total,
    SUM(o.total) AS total_revenue,
    ROUND(AVG(o.total), 2) AS avg_order_value,
    -- Create simple visualization with asterisks
    REPEAT('*', (COUNT(*) * 30 / (
        SELECT MAX(order_cnt) FROM (
            SELECT COUNT(*) AS order_cnt 
            FROM orders 
            WHERE status = 7 AND location_id = 62
            GROUP BY EXTRACT(HOUR FROM (created_at - INTERVAL '7 hours'))
        ) AS max_counts
    ))::integer) AS volume_chart
FROM
    orders o
WHERE
    o.location_id = 62
    AND o.status = 7 -- Completed orders
    AND o.updated_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY
    hour_of_day
ORDER BY
    hour_of_day; 