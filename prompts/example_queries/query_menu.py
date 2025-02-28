"""
Example queries for retrieving menu information.
"""

QUERY_MENU_QUERIES = """
These example queries demonstrate how to query menu information:

1. List all menu categories for a specific location:
--------------------------------------------------
SELECT c.id, c.name, c.description, c.seq_num, m.name as menu_name
FROM categories c
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 16
ORDER BY c.seq_num;

2. Get all menu items in a specific category:
--------------------------------------------------
SELECT i.id, i.name, i.description, i.price, i.disabled
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 16
  AND c.name = 'Entrees'
ORDER BY i.seq_num;

3. Find all active dessert items:
--------------------------------------------------
SELECT i.id, i.name, i.description, i.price
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND c.name LIKE '%Dessert%'
  AND i.disabled = FALSE
ORDER BY i.seq_num;

4. Find vegetarian options:
--------------------------------------------------
SELECT i.id, i.name, i.description, i.price
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
JOIN item_tags it ON i.id = it.item_id
JOIN tags t ON it.tag_id = t.id
WHERE m.location_id = 62
  AND i.disabled = FALSE
  AND t.name = 'Vegetarian'
ORDER BY c.seq_num, i.seq_num;

5. Get price for a specific menu item:
--------------------------------------------------
SELECT i.name, i.price, c.name as category
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND i.name = 'Caesar Salad';

6. Get all available menu items:
--------------------------------------------------
SELECT c.name as category, i.name as item, i.price, i.description
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 62
  AND i.disabled = FALSE
ORDER BY c.seq_num, i.seq_num;
""" 