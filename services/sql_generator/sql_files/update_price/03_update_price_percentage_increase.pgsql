BEGIN;

WITH item_to_update AS (
    SELECT i.id, i.name, i.price as old_price, 
           ROUND(i.price * 1.10, 2) as new_price
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = [LOCATION_ID]
      AND c.name ILIKE '%[CATEGORY_NAME]%'
)

SELECT id, name, old_price, new_price,
       new_price - old_price as price_difference,
       ROUND((new_price - old_price) / old_price * 100, 1) as percent_increase
FROM item_to_update;

SET price = item_to_update.new_price,
    updated_at = NOW()
FROM item_to_update
WHERE items.id = item_to_update.id;

SELECT i.id, i.name, i.price, c.name as category
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = [LOCATION_ID]
  AND c.name ILIKE '%[CATEGORY_NAME]%'
ORDER BY i.name;

COMMIT; 