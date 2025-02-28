-- Lifetime value of our average customer
SELECT TO_CHAR(AVG(total_spent), 'FM$999,999,990.00') as avg_lifetime_value
FROM (
    SELECT customer_id, SUM(total) as total_spent
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
) sub; 