
SELECT
    l.id,
	l.name as location_name,
	o.id AS order_id,
	o.status AS order_status,
	o.total AS order_total,
	u.id AS user_id,
	u.phone AS user_phone,
	u.email AS user_email,
	o.updated_at - INTERVAL '7 hours' AS order_date,
	o.tip as tip,
	u.first_name || ' ' || u.last_name AS customer,
	d.amount as discount_amount
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
WHERE l.id NOT IN (32,29)
  AND u.id NOT IN (19,644,928,174)
  AND o.status NOT IN (0,6)
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 day'