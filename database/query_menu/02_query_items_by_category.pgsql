-- Query menu items by category
SELECT i.id, i.name, i.description, i.price, i.disabled
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE c.name = 'Starters'
  AND m.location_id = 16
ORDER BY i.name; 