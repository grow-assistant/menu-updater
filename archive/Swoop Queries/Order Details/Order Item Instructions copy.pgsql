
SELECT
	u.first_name || ' ' || u.last_name AS customer,
	i.name AS item_name,
	oi.instructions AS item_instructions
FROM orders o
inner join order_items oi ON oi.order_id = o.id AND oi.deleted_at IS NULL
INNER JOIN items i on i.id = oi.item_id
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
WHERE l.id IN (66)
  AND u.id NOT IN (19,644,928,174)
  AND o.status NOT IN (0,6)
  AND oi.instructions <> ''
  AND (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE - INTERVAL '7 days'
  --AND tip > 0
 ORDER by o.updated_at desc


