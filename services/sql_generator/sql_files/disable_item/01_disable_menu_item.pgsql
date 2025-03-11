UPDATE items
SET disabled = TRUE,
    updated_at = NOW()
WHERE name like '%Quesadilla%'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 16
  ); 


