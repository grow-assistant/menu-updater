-- Percentage of orders from repeat customers this month
WITH customer_order_counts AS (
    SELECT 
        customer_id,
        COUNT(*) AS order_count
    FROM 
        orders
    WHERE 
        updated_at >= DATE_TRUNC('month', CURRENT_DATE)
        AND location_id = 62
        AND status = 7
       
    GROUP BY 
        customer_id
)

SELECT 
    COUNT(*) AS total_customers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_customer_percentage,
    AVG(order_count) AS avg_orders_per_customer
FROM 
    customer_order_counts