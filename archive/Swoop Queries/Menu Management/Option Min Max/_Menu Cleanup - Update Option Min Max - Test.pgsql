SELECT 
    i.name AS item_name,
    o.name AS option_name,
    oi.id AS option_item_id,
    oi.name AS option_item_name,
    oi.price AS option_item_price,
    o.*
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
INNER JOIN options o ON o.item_id = i.id
INNER JOIN option_items oi ON oi.option_id = o.id
WHERE l.id = 79
AND c.name = 'Brunch - Menu'
--AND i.name = 'Breakfast Burrito'
AND o.name = 'Side Choice'
AND o.min = 2
AND o.max = 2
ORDER BY oi.name;