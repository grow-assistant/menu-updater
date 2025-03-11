SELECT c.name AS category, i.name, i.description, i.price
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE i.price BETWEEN 5.00 AND 10.00
  AND i.disabled = FALSE
  AND m.location_id = 16
ORDER BY i.price, i.name; 