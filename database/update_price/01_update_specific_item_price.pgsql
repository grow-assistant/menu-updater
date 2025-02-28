-- Update a specific menu item price
UPDATE items
SET price = 7.00
WHERE name like '%Quesadilla%'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 16
  ); 