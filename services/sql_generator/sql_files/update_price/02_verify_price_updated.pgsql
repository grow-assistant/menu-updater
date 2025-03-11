SELECT i.id, i.name, i.price, c.name as category, m.name as menu
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE i.name ILIKE '%[ITEM_NAME]%'
  AND m.location_id = [LOCATION_ID]
ORDER BY i.name;

SELECT 
    i.name as item_name,
    ph.old_price,
    ph.new_price,
    ph.updated_at,
    ph.updated_by
FROM items i
LEFT JOIN price_history ph ON i.id = ph.item_id
WHERE i.name ILIKE '%[ITEM_NAME]%'
  AND i.id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = [LOCATION_ID]
  )
ORDER BY ph.updated_at DESC
LIMIT 5; 