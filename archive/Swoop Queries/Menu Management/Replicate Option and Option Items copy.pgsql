/*
This script copies options and option items from one menu item to another.
It performs the following steps:
1. Finds the source item ID ('Chuck Roast') and target item ID ('Seared Sea Scallops')
2. Gets the next available option ID to avoid conflicts
3. Copies all options from the source item to the target item, preserving attributes
4. Copies all option items associated with those options to the new options
5. Maintains referential integrity by linking new option items to their new parent options

This is useful when creating a new menu item that needs the same option structure
as an existing item.
*/

DO $$
DECLARE
    old_item_id int;
    new_item_id int;
    new_option_id int;
BEGIN

-- Old Item
SELECT i.id INTO old_item_id
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
WHERE 
    l.id = 62
    AND c.id = 529
    AND i.name = 'Chuck Roast';

RAISE NOTICE 'Old item ID: %', old_item_id;

-- New Item
SELECT i.id INTO new_item_id
FROM locations l 
INNER JOIN menus m ON m.location_id = l.id
INNER JOIN categories c ON c.menu_id = m.id
INNER JOIN items i ON i.category_id = c.id
WHERE 
    l.id = 62
    AND c.id = 529
    AND i.name = 'Seared Sea Scallops';

RAISE NOTICE 'New item ID: %', new_item_id;

-- Exit if no items were found
IF old_item_id IS NULL OR new_item_id IS NULL THEN 
    RAISE EXCEPTION 'One or both items not found for the specified criteria';
END IF;

-- Get the next available option id
SELECT COALESCE(MAX(id), 0) + 1 INTO new_option_id FROM options;
RAISE NOTICE 'Next available option ID: %', new_option_id;

-- Insert new options and store their old and new IDs
WITH inserted_options AS (
    INSERT INTO options (id, created_at, updated_at, deleted_at, name, description, min, max, item_id, disabled)
    SELECT 
        new_option_id + ROW_NUMBER() OVER (ORDER BY id) - 1,
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
    WHERE item_id = old_item_id
    RETURNING id AS new_option_id, 
        (SELECT id FROM options WHERE item_id = old_item_id AND name = options.name) AS old_option_id
)
-- Insert option items for each new option
INSERT INTO option_items (id, created_at, updated_at, deleted_at, name, description, price, option_id, disabled)
SELECT 
    (SELECT COALESCE(MAX(id), 0) + 1 FROM option_items) + ROW_NUMBER() OVER (ORDER BY oi.id),
    NOW(),
    NOW(),
    oi.deleted_at,
    oi.name,
    oi.description,
    oi.price,
    io.new_option_id,
    oi.disabled
FROM option_items oi
INNER JOIN inserted_options io ON io.old_option_id = oi.option_id;

RAISE NOTICE 'Successfully completed option and option item replication';

END $$;
