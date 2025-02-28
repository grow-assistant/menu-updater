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
WHERE (m.location_id IS NULL OR l.id = 79)
--AND (i.name IS NULL OR i.name = 'Three Egg Platter')
AND (o.name = 'Toast Type')
--AND (o.name IS NULL OR o.name = 'Toast Type')
--AND (oi.name IS NULL OR oi.name = 'No Croutons');
