-- Orders on a specific date (2/21/2025 format)
-- This example shows how to filter orders by a specific date, handling MM/DD/YYYY format
SELECT 
    COUNT(*) as order_count
FROM 
    orders o
WHERE 
    o.location_id = 62
    AND o.status = 7 -- Completed orders
    AND (o.updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY');

-- Alternative version with detailed order information
SELECT
    o.id AS order_id,
    u.first_name || ' ' || u.last_name AS customer_name,
    o.total AS order_total,
    to_char((o.updated_at - INTERVAL '7 hours'), 'YYYY-MM-DD HH24:MI:SS') AS order_date,
    o.status AS order_status
FROM 
    orders o
JOIN 
    users u ON o.customer_id = u.id
WHERE 
    o.location_id = 62
    AND o.status = 7
    AND (o.updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY')
ORDER BY 
    o.updated_at; 