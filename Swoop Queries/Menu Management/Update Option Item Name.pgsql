UPDATE option_items
SET name = 'Asiago-Chive Risotto'
WHERE id IN (
    SELECT oi.id
    FROM locations l
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o ON o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = 62
      --AND c.id = 440
      AND oi.name = 'Butternut Squash Risotto'
);


SELECT oi.id
    FROM locations l
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o ON o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = 62
      --AND c.id = 440
      AND oi.name = 'Butternut Squash Risotto'