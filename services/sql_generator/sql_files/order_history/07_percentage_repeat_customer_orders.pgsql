WITH customer_orders AS (
    SELECT customer_id, COUNT(*) as order_count
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
),
repeat_customers AS (
    SELECT customer_id
    FROM customer_orders
    WHERE order_count > 1
)
SELECT 
    ROUND(
        (SELECT COUNT(*) FROM orders o 
         WHERE o.location_id = 62 AND o.status = 7 
           AND o.customer_id IN (SELECT customer_id FROM repeat_customers)
        ) * 100.0
        / NULLIF((SELECT COUNT(*) FROM orders o 
                  WHERE o.location_id = 62 AND o.status = 7), 0),
        0
    ) || '%' AS repeat_percentage;