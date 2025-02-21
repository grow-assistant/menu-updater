
DECLARE
    old_item_id INT := 3056;
    new_item_id INT := 3848;
BEGIN
    -- Create a temporary table with the same structure as 'options'
    CREATE TEMP TABLE temp_options (LIKE options INCLUDING ALL);

    -- Insert into the temporary table, duplicating the existing option for a new item
    INSERT INTO temp_options (id, created_at, updated_at, deleted_at, name, description, min, max, item_id, disabled)
    SELECT 
        (SELECT COALESCE(MAX(id), 0) + 1 FROM temp_options), -- Use COALESCE in case table is empty
        NOW(), -- Current time for created_at
        NOW(), -- Current time for updated_at
        deleted_at, 
        name, 
        description, 
        min, 
        max, 
        new_item_id, -- Link this entry to the new item
        disabled
    FROM options
    WHERE item_id = old_item_id
    LIMIT 1
    
    SELECT * FROM   temp_options;
    
    -- Clean up: Drop the temporary table
    --DROP TABLE temp_options;

