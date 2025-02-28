"""
Example queries for updating prices of menu items.
"""

UPDATE_PRICE_QUERIES = """
These example queries demonstrate how to update the price of menu items:

1. Update a specific menu item price:
--------------------------------------------------
UPDATE items
SET price = 4.99
WHERE name = 'French Fries'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
  );

2. Update price with validation:
--------------------------------------------------
WITH item_to_update AS (
    SELECT i.id, i.name, i.price as old_price, 8.50 as new_price
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
      AND i.name = 'Burger'
)
UPDATE items
SET price = item_to_update.new_price,
    updated_at = NOW()
FROM item_to_update
WHERE items.id = item_to_update.id;

3. Update price with percentage increase:
--------------------------------------------------
WITH item_to_update AS (
    SELECT i.id, i.name, i.price as old_price, 
           ROUND(i.price * 1.10, 2) as new_price  -- 10% increase
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
      AND i.name = 'Caesar Salad'
)
UPDATE items
SET price = item_to_update.new_price,
    updated_at = NOW()
FROM item_to_update
WHERE items.id = item_to_update.id;
""" 