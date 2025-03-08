-- Yesterday's order details
SELECT
    o.id AS order_id,
    to_char(o.updated_at - INTERVAL '7 hours', 'YYYY-MM-DD HH24:MI') AS updated_at,
    u.first_name || ' ' || u.last_name AS customer,
    regexp_replace(u.phone, '(\d{3})(\d{3})(\d{4})', '(\1) \2-\3') AS user_phone,
    u.email AS user_email,
    o.total AS order_total,
    CAST(o.tip AS DECIMAL(10,2)) as tip,
    COALESCE(d.amount, 0) as discount_amount,
    o.status AS order_status
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
WHERE l.id = 62
  AND o.status = 6
  AND o.updated_at > CURRENT_TIMESTAMP - INTERVAL '1 day'

