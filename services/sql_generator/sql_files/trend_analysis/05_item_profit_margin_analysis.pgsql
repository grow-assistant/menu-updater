-- Item profit margin analysis (profit_margin_analysis)
-- Analyzes menu items by their profit margin and sales volume

WITH item_costs AS (
    -- Simulated item costs (in real system, would pull from inventory/cost tables)
    SELECT 
        i.id AS item_id,
        i.name AS item_name,
        i.price AS selling_price,
        -- Simulate cost as 30-40% of selling price based on item_id
        ROUND(i.price * (0.3 + (i.id % 10) * 0.01), 2) AS cost_price
    FROM 
        items i
    JOIN 
        categories c ON i.category_id = c.id
    JOIN 
        menus m ON c.menu_id = m.id
    WHERE 
        m.location_id = 62
        AND i.disabled = FALSE
),
item_sales AS (
    -- Calculate sales volume and revenue by item
    SELECT 
        i.id AS item_id,
        COUNT(oi.id) AS order_count,
        SUM(oi.quantity) AS units_sold,
        SUM(i.price * oi.quantity) AS total_revenue
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
        AND o.updated_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 
        i.id
)
-- Join the data and calculate margins
SELECT 
    ic.item_id,
    ic.item_name,
    ic.selling_price,
    ic.cost_price,
    ROUND(ic.selling_price - ic.cost_price, 2) AS gross_profit,
    CASE 
        WHEN ic.selling_price = 0 THEN NULL
        ELSE ROUND((ic.selling_price - ic.cost_price) / ic.selling_price * 100, 1)
    END AS margin_percentage,
    COALESCE(s.units_sold, 0) AS units_sold,
    COALESCE(s.total_revenue, 0) AS total_revenue,
    COALESCE(ROUND((ic.selling_price - ic.cost_price) * s.units_sold, 2), 0) AS total_profit,
    CASE 
        WHEN COALESCE(s.units_sold, 0) > 100 AND (NULLIF(ic.selling_price, 0) IS NOT NULL AND (ic.selling_price - ic.cost_price) / NULLIF(ic.selling_price, 0) > 0.5)
            THEN 'Star (High Volume, High Margin)'
        WHEN COALESCE(s.units_sold, 0) > 100 
            THEN 'Volume Driver (High Volume, Low Margin)'
        WHEN NULLIF(ic.selling_price, 0) IS NOT NULL AND (ic.selling_price - ic.cost_price) / NULLIF(ic.selling_price, 0) > 0.5
            THEN 'Opportunity (Low Volume, High Margin)'
        ELSE 'Reconsider (Low Volume, Low Margin)'
    END AS item_classification
FROM 
    item_costs ic
LEFT JOIN 
    item_sales s ON ic.item_id = s.item_id
ORDER BY 
    total_profit DESC; 