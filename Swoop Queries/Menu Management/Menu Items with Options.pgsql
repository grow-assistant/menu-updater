
SELECT 
	l.id AS location_id,
	l.name AS location_name,
	m.id AS menu_id,
	m.name AS menu_name,
	c.id as category_id, 
	c.name as category_name, 
	c.seq_num,
	i.id AS item_id,
	i.name AS item_name,
	o.id AS option_id, 
	o.name AS option_name,
	oi.id AS option_item_id,
	oi.name AS option_item_name
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
LEFT JOIN options o on o.item_id = i.id
LEFT JOIN option_items oi ON oi.option_id = o.id
	    WHERE l.id = 62
      --AND c.name = 'Signature Sandwiches'
      AND oi.name LIKE ('%Risotto%')
	--And oi.name = 'Wedge Salad'
    --and c.id = 529
	--i.id = 3522 AND

	--o.id = 3500
	--AND oi.name LIKE ('%Rye%')
	order by c.seq_num, i.seq_num
--SELECT * FROM option_items --where id IN (13160, 13211, 13222)

