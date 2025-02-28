WITH items_to_update AS (
    SELECT i.id AS item_id,
           i.name AS item_name,
           o.id AS option_id,
           o.name AS option_name,
           oi.id AS option_item_id,
           oi.name AS option_item_name,
           oi.price
    FROM locations l
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o ON o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = 62
      --AND c.id = 440

      --AND c.name = 'Salads'
      AND o.name = 'Extras'
      --AND oi.name IN ('Blackened Shrimp')
      order by oi.name, oi.price
)
UPDATE option_items
SET price = 10.00  -- Set your desired price here
WHERE id IN (SELECT option_item_id FROM items_to_update);