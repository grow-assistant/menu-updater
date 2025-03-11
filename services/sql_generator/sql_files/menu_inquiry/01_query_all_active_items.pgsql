SELECT i.id, i.name, i.description, i.price, c.name AS category
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE i.disabled = FALSE
  AND m.location_id = 62
ORDER BY c.name, i.name; 