WITH option_id AS (
    SELECT DISTINCT o.id
    FROM locations l 
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    INNER JOIN options o on o.item_id = i.id
    WHERE l.id = 75
    AND i.name = 'Traditional Club'
    AND o.name = 'Remove Options'
),
max_id AS (
    SELECT COALESCE(MAX(id), 0) + 1 as next_id 
    FROM option_items
)
INSERT INTO option_items
    (id, created_at, updated_at, deleted_at, name, description, price, option_id, disabled)
VALUES
    ((SELECT next_id FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Lettuce', 'No Lettuce', 0.0000, (SELECT id FROM option_id), false),
    ((SELECT next_id + 1 FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Tomato', 'No Tomato', 0.0000, (SELECT id FROM option_id), false),
    ((SELECT next_id + 2 FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Mayo', 'No Mayo', 0.0000, (SELECT id FROM option_id), false),
    ((SELECT next_id + 3 FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Bacon', 'No Bacon', 0.0000, (SELECT id FROM option_id), false),
    ((SELECT next_id + 4 FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Turkey', 'No Turkey', 0.0000, (SELECT id FROM option_id), false),
    ((SELECT next_id + 5 FROM max_id), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, 'No Ham', 'No Ham', 0.0000, (SELECT id FROM option_id), false);