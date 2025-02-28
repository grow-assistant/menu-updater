DO $$
DECLARE
    old_item_id int;
    new_item_id int;
BEGIN

-- Old Item
SELECT i.id INTO old_item_id
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
WHERE 
    l.id = 62
    AND c.name = 'Entrees'
    AND i.name = 'IHCC Classic Filet Mignon';

-- New Item
SELECT i.id INTO new_item_id
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
WHERE 
    l.id = 62
    AND c.name = 'Entrees'
    AND i.name = 'Seared Sea Scallops';

-- Exit if no item was found
IF old_item_id IS NULL THEN 
    RAISE EXCEPTION 'No item found for the specified criteria';
END IF;

-- Directly insert into the 'options' table, duplicating the existing options for a new item
INSERT INTO options (id, created_at, updated_at, deleted_at, name, description, min, max, item_id, disabled)
SELECT 
    (SELECT COALESCE(MAX(id), 0) + 1 FROM options) + ROW_NUMBER() OVER (ORDER BY id),
    NOW(),
    NOW(), 
    deleted_at, 
    name,
    description,
    min,
    max,
    new_item_id,
    disabled
FROM options
WHERE item_id = old_item_id;

END $$;
