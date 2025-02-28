UPDATE options
SET min = 0,
    max = 0
WHERE id IN (
    SELECT DISTINCT o.id
    FROM locations l 
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    INNER JOIN options o ON o.item_id = i.id
    INNER JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = 79
    AND c.name = 'Brunch - Menu'
    AND o.name = 'Side Choice'
    AND o.min = 2
    AND o.max = 2
);