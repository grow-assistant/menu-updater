DO $$
DECLARE
    v_location_id INT := 75;
    v_old_category_name VARCHAR := 'Deli Selections';
    v_old_item_name VARCHAR := 'Dinner Salad';
    v_new_category_name VARCHAR := 'Deli Selections';
    v_new_item_name VARCHAR := 'Chef Salad';
    old_item_id INT;
    new_item_id INT;
    max_option_id INT;
    max_option_item_id INT;
BEGIN
    -- Fetch old item ID
    SELECT i.id INTO old_item_id
    FROM locations l
    JOIN menus m ON m.location_id = l.id
    JOIN categories c ON c.menu_id = m.id
    JOIN items i ON i.category_id = c.id
    WHERE l.id = v_location_id
      AND c.name = v_old_category_name
      AND i.name = v_old_item_name;

    -- Fetch new item ID
    SELECT i.id INTO new_item_id
    FROM locations l
    JOIN menus m ON m.location_id = l.id
    JOIN categories c ON c.menu_id = m.id
    JOIN items i ON i.category_id = c.id
    WHERE l.id = v_location_id
      AND c.name = v_new_category_name
      AND i.name = v_new_item_name;

    -- Validate item IDs
    IF old_item_id IS NULL OR new_item_id IS NULL THEN
        RAISE EXCEPTION 'No item found for the specified criteria';
    END IF;

    -- Get current maximum IDs
    SELECT COALESCE(MAX(id), 0) INTO max_option_id FROM options;
    SELECT COALESCE(MAX(id), 0) INTO max_option_item_id FROM option_items;

    -- Insert new options
    WITH new_options AS (
        INSERT INTO options (
            id, created_at, updated_at, deleted_at, name, description, min, max, item_id, disabled
        )
        SELECT 
            max_option_id + ROW_NUMBER() OVER (ORDER BY id),
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
        RETURNING id, name
    )
    -- Insert new option items
    INSERT INTO option_items (
        id, created_at, updated_at, deleted_at, name, description, price, option_id, disabled
    )
    SELECT 
        max_option_item_id + ROW_NUMBER() OVER (ORDER BY oi.id),
        NOW(),
        NOW(),
        oi.deleted_at,
        oi.name,
        oi.description,
        oi.price,
        no.id AS option_id,
        oi.disabled
    FROM option_items oi
    JOIN options o ON o.id = oi.option_id
    JOIN new_options no ON o.name = no.name
    WHERE o.item_id = old_item_id;
END $$;
