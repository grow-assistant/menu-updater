-- Update a specific menu item price (update_item_price)
BEGIN;

-- First verify the current price
SELECT id, name, price 
FROM items 
WHERE name ILIKE '%Quesadilla%'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 16
  );

-- Update the price  
UPDATE items
SET price = 7.00
WHERE name ILIKE '%Quesadilla%'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 16
  );

COMMIT; 