QUERY_TEMPLATES = {
    "view_location_hours": """
        SELECT * FROM location_hours
        WHERE location_id = %(location_id)s
    """,
    "update_location_hours": """
        UPDATE location_hours
        SET
            updated_at = CURRENT_TIMESTAMP,
            open_time = %(open_time)s,
            close_time = %(close_time)s
        WHERE
            location_id = %(location_id)s
            AND day_of_week = %(day_of_week)s
    """,
    "view_markers": """
        SELECT * FROM markers
        WHERE location_id = %(location_id)s
        ORDER BY id DESC
    """,
    "insert_marker": """
        INSERT INTO markers
        (id, created_at, updated_at, deleted_at, name, disabled, location_id)
        VALUES
        (%(id)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %(deleted_at)s,
         %(name)s, %(disabled)s, %(location_id)s)
    """,
    "menu_cleanup": """
        DO $$
        DECLARE
            v_location_id INT := %(location_id)s;
            v_item_name VARCHAR := %(item_name)s;
            v_option_name VARCHAR := %(option_name)s;
        BEGIN
            -- Delete option items first
            DELETE FROM option_items
            WHERE id IN (
                SELECT DISTINCT oi.id
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
                SELECT DISTINCT o.id
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
    """,
}
