-- Update price with percentage increase
WITH item_to_update AS (
    SELECT i.id, i.name, i.price as old_price, 
           ROUND(i.price * 1.10, 2) as new_price  -- 10% increase
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 16
      AND i.name like '%Quesadilla%'
)
    UPDATE items
    SET price = item_to_update.new_price,
    updated_at = NOW()
FROM item_to_update
WHERE items.id = item_to_update.id; 