DO $$
DECLARE
    v_location_id INT := 16;
    v_item_name VARCHAR := 'Quesadilla';
    v_option_name VARCHAR := 'Meat Temperature';
    --v_option_item_name VARCHAR := 'Poached';
BEGIN
    -- Delete option items first
    DELETE FROM option_items 
    WHERE id IN (
        SELECT 
            DISTINCT oi.id AS option_item_id
        FROM locations l 
        INNER JOIN menus m ON m.location_id = l.id
        INNER JOIN categories c ON c.menu_id = m.id
        INNER JOIN items i ON i.category_id = c.id
        INNER JOIN options o ON o.item_id = i.id
        INNER JOIN option_items oi ON oi.option_id = o.id
        WHERE l.id = v_location_id
        AND i.name = v_item_name
        AND o.name = v_option_name
    );

    -- Then delete the options
    DELETE FROM options 
    WHERE id IN (
        SELECT 
            DISTINCT o.id AS option_id
        FROM locations l 
        INNER JOIN menus m ON m.location_id = l.id
        INNER JOIN categories c ON c.menu_id = m.id
        INNER JOIN items i ON i.category_id = c.id
        INNER JOIN options o ON o.item_id = i.id
        WHERE l.id = v_location_id
        AND i.name = v_item_name
        AND o.name = v_option_name
    );
END $$;
