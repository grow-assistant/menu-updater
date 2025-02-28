"""
Example queries for disabling menu items.
"""

DISABLE_ITEM_QUERIES = """
These example queries demonstrate how to disable menu items:

1. Disable a menu item:
--------------------------------------------------
UPDATE items
SET disabled = TRUE,
    updated_at = NOW()
WHERE name = 'Chocolate Cake'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
  );

2. Disable with verification:
--------------------------------------------------
WITH item_to_disable AS (
    SELECT i.id, i.name, i.disabled as old_status
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
      AND i.name = 'Veggie Burger'
      AND i.disabled = FALSE
)
UPDATE items
SET disabled = TRUE,
    updated_at = NOW()
FROM item_to_disable
WHERE items.id = item_to_disable.id;

3. Disable multiple related items:
--------------------------------------------------
UPDATE items
SET disabled = TRUE,
    updated_at = NOW()
WHERE name LIKE '%Seasonal%'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
  );
""" 