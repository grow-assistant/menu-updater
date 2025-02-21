DO $$
DECLARE
    v_location_id INT := 75;
    v_item_name VARCHAR := 'Three Egg Platter';
    v_option_name VARCHAR := 'Remove Options';
    v_option_item_name VARCHAR := 'No Cucumbers';
BEGIN


-- Delete options items
DELETE FROM option_items 
WHERE id IN (
    SELECT 
        DISTINCT oi.id AS option_item_id
    FROM locations l 
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o on o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = v_location_id
    AND i.name = v_item_name
    AND o.name = v_option_name
    AND oi.name = v_option_item_name
);

END $$;
-- Delete options
DELETE FROM options 
WHERE id IN (
    SELECT 
        DISTINCT o.id AS option_id
    FROM locations l 
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o on o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE l.id = v_location_id
    AND i.name = v_item_name
    --AND o.name = v_option_name
    --AND oi.name = v_option_item_name
);



-- Delete items
DELETE FROM items 
WHERE id IN (
    SELECT 
        DISTINCT i.id AS item_id
    FROM locations l 
    INNER JOIN menus m ON m.location_id = l.id
    INNER JOIN categories c ON c.menu_id = m.id
    INNER JOIN items i ON i.category_id = c.id
    LEFT JOIN options o on o.item_id = i.id
    LEFT JOIN option_items oi ON oi.option_id = o.id
    WHERE (m.location_id IS NULL OR l.id = v_location_id)
    AND (i.name IS NULL OR i.name = v_item_name)
    AND (o.name IS NULL OR o.name = v_option_name)
    AND (oi.name IS NULL OR oi.name = v_option_item_name)
);

END $$;
