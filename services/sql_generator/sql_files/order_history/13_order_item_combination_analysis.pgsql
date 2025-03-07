-- Order item combination analysis (item_combination_analysis)
-- Identifies which menu items are frequently ordered together

WITH order_items_list AS (
    -- Get all order item pairs
    SELECT
        o.id AS order_id,
        o.updated_at AS order_date,
        i1.id AS item1_id,
        i1.name AS item1_name,
        i2.id AS item2_id,
        i2.name AS item2_name
    FROM
        orders o
    JOIN
        order_items oi1 ON o.id = oi1.order_id
    JOIN
        items i1 ON oi1.item_id = i1.id
    JOIN
        order_items oi2 ON o.id = oi2.order_id
    JOIN
        items i2 ON oi2.item_id = i2.id
    JOIN
        categories c1 ON i1.category_id = c1.id
    JOIN
        categories c2 ON i2.category_id = c2.id
    JOIN
        menus m ON c1.menu_id = m.id
    WHERE
        o.location_id = 62
        AND o.status = 7
        AND o.updated_at >= CURRENT_DATE - INTERVAL '90 days'
        AND i1.id < i2.id  -- Avoid duplicate pairs and self-pairs
),
item_stats AS (
    -- Get individual item frequencies
    SELECT
        i.id AS item_id,
        i.name AS item_name,
        COUNT(DISTINCT o.id) AS order_count
    FROM
        orders o
    JOIN
        order_items oi ON o.id = oi.order_id
    JOIN
        items i ON oi.item_id = i.id
    JOIN
        categories c ON i.category_id = c.id
    JOIN
        menus m ON c.menu_id = m.id
    WHERE
        o.location_id = 62
        AND o.status = 7
        AND o.updated_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY
        i.id, i.name
)
-- Calculate co-occurrence metrics
SELECT
    oil.item1_name,
    oil.item2_name,
    COUNT(DISTINCT oil.order_id) AS times_ordered_together,
    ROUND(
        COUNT(DISTINCT oil.order_id)::numeric / LEAST(s1.order_count, s2.order_count) * 100,
        2
    ) AS co_occurrence_rate,
    ROUND(
        COUNT(DISTINCT oil.order_id)::numeric / (s1.order_count + s2.order_count - COUNT(DISTINCT oil.order_id)) * 100,
        2
    ) AS jaccard_similarity
FROM
    order_items_list oil
JOIN
    item_stats s1 ON oil.item1_id = s1.item_id
JOIN
    item_stats s2 ON oil.item2_id = s2.item_id
GROUP BY
    oil.item1_name, oil.item2_name, s1.order_count, s2.order_count
HAVING
    COUNT(DISTINCT oil.order_id) >= 5
ORDER BY
    times_ordered_together DESC
LIMIT 20; 