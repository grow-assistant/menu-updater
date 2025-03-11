SELECT 
    COUNT(*) as order_count
FROM 
    orders o
WHERE 
    o.location_id = 62
    AND o.status = 7
    AND (o.updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY');

SELECT
    o.id AS order_id,
    u.first_name || ' ' || u.last_name AS customer_name,
    o.total AS order_total,
    to_char((o.updated_at - INTERVAL '7 hours'), 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
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