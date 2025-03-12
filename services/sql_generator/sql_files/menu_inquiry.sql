
        -- Query: What items do you have on the menu?
        -- Category: menu_inquiry
        SELECT i.name, i.description, i.price, c.name as category
        FROM items i
        JOIN categories c ON i.category_id = c.id
        WHERE i.disabled = FALSE
        ORDER BY c.seq_num, i.seq_num;
        