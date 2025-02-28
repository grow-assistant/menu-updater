"""
Example queries for enabling previously disabled menu items.
"""

ENABLE_ITEM_QUERIES = """
These example queries demonstrate how to enable menu items:

1. Enable a specific menu item:
--------------------------------------------------
UPDATE items
SET disabled = FALSE,
    updated_at = NOW()
WHERE name = 'Veggie Burger'
  AND id IN (
    SELECT i.id
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
  );

2. Enable with verification:
--------------------------------------------------
WITH item_to_enable AS (
    SELECT i.id, i.name, i.disabled as old_status
    FROM items i
    JOIN categories c ON i.category_id = c.id
    JOIN menus m ON c.menu_id = m.id
    WHERE m.location_id = 62
      AND i.name = 'Apple Pie'
      AND i.disabled = TRUE
)
UPDATE items
SET disabled = FALSE,
    updated_at = NOW()
FROM item_to_enable
WHERE items.id = item_to_enable.id;

3. Enable seasonal items:
--------------------------------------------------
UPDATE items
SET disabled = FALSE,
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