WITH popular_items AS (
    SELECT 
        i.id AS item_id,
        i.name AS item_name,
        COUNT(DISTINCT o.id) AS order_count,
        SUM(oi.quantity) AS quantity_sold
    FROM 
        items i
    JOIN 
        order_items oi ON i.id = oi.item_id
    JOIN 
        orders o ON oi.order_id = o.id
    JOIN 
        categories c ON i.category_id = c.id
    JOIN 
        menus m ON c.menu_id = m.id
    WHERE 
        m.location_id = 62
        AND o.status = 7
        AND o.created_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 
        i.id, i.name
    ORDER BY 
        quantity_sold DESC
    LIMIT 10
),
popular_options AS (
    SELECT 
        pi.item_id,
        opt.id AS option_id,
        opt.name AS option_name,
        oi_opt.name AS option_item_name,
        COUNT(*) AS option_count
    FROM 
        popular_items pi
    JOIN 
        order_items oi ON pi.item_id = oi.item_id
    JOIN 
        order_option_items ooi ON oi.id = ooi.order_item_id
    JOIN 
        option_items oi_opt ON ooi.option_item_id = oi_opt.id
    JOIN 
        options opt ON oi_opt.option_id = opt.id
    GROUP BY 
        pi.item_id, opt.id, opt.name, oi_opt.name
)
SELECT 
    pi.item_name,
    pi.quantity_sold,
    i.price AS item_price,
    c.name AS category,
    string_agg(
        po.option_name || ': ' || po.option_item_name || ' (' || po.option_count || ' times)', 
        '; '
        ORDER BY po.option_name, po.option_item_name
    ) AS popular_options
FROM 
    popular_items pi
JOIN 
    items i ON pi.item_id = i.id
JOIN 
    categories c ON i.category_id = c.id
LEFT JOIN 
    popular_options po ON pi.item_id = po.item_id
GROUP BY 
    pi.item_name, pi.quantity_sold, i.price, c.name
ORDER BY 
    pi.quantity_sold DESC; 