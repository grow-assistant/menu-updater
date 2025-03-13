SELECT 
    m.name AS menu_name, 
    c.name AS category_name, 
    i.name AS item_name, 
    i.description AS item_description, 
    i.price 
FROM 
    menus m
JOIN 
    categories c ON m.id = c.menu_id AND c.disabled = false
JOIN 
    items i ON c.id = i.category_id AND i.disabled = false
WHERE 
    m.disabled = false
    AND m.deleted_at IS NULL
    AND c.deleted_at IS NULL
    AND i.deleted_at IS NULL
ORDER BY 
    m.name, 
    c.seq_num, 
    i.seq_num;
