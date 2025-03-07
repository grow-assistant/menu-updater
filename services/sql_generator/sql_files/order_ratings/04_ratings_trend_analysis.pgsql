-- Ratings trend analysis over time (ratings_trend_analysis)
-- Examines how ratings have changed over time, by month and item category

WITH monthly_ratings AS (
    SELECT
        DATE_TRUNC('month', r.created_at) AS month,
        c.name AS category,
        COUNT(orf.id) AS rating_count,
        ROUND(AVG(orf.value), 2) AS avg_rating,
        ROUND(
            COUNT(CASE WHEN orf.value >= 4 THEN 1 END)::numeric / 
            NULLIF(COUNT(orf.id), 0) * 100, 
            1
        ) AS positive_rating_percent
    FROM
        order_ratings r
    JOIN
        orders o ON r.order_id = o.id
    JOIN
        order_items oi ON o.id = oi.order_id
    JOIN
        items i ON oi.item_id = i.id
    JOIN
        categories c ON i.category_id = c.id
    JOIN
        menus m ON c.menu_id = m.id
    JOIN
        order_ratings_feedback orf ON r.id = orf.rating_id
    WHERE
        m.location_id = 62
        AND r.created_at >= CURRENT_DATE - INTERVAL '12 months'
        AND o.status = 7
    GROUP BY
        DATE_TRUNC('month', r.created_at),
        c.name
),
category_avg AS (
    -- Get the overall average rating for each category
    SELECT
        c.name AS category,
        ROUND(AVG(orf.value), 2) AS category_avg_rating
    FROM
        order_ratings r
    JOIN
        orders o ON r.order_id = o.id
    JOIN
        order_items oi ON o.id = oi.order_id
    JOIN
        items i ON oi.item_id = i.id
    JOIN
        categories c ON i.category_id = c.id
    JOIN
        menus m ON c.menu_id = m.id
    JOIN
        order_ratings_feedback orf ON r.id = orf.rating_id
    WHERE
        m.location_id = 62
        AND r.created_at >= CURRENT_DATE - INTERVAL '12 months'
        AND o.status = 7
    GROUP BY
        c.name
),
overall_trend AS (
    -- Calculate how ratings trend over time overall
    SELECT
        DATE_TRUNC('month', r.created_at) AS month,
        ROUND(AVG(orf.value), 2) AS overall_avg_rating
    FROM
        order_ratings r
    JOIN
        orders o ON r.order_id = o.id
    JOIN
        order_items oi ON o.id = oi.order_id
    JOIN
        items i ON oi.item_id = i.id
    JOIN
        categories c ON i.category_id = c.id
    JOIN
        menus m ON c.menu_id = m.id
    JOIN
        order_ratings_feedback orf ON r.id = orf.rating_id
    WHERE
        m.location_id = 62
        AND r.created_at >= CURRENT_DATE - INTERVAL '12 months'
        AND o.status = 7
    GROUP BY
        DATE_TRUNC('month', r.created_at)
)
-- Put everything together for the trend analysis
SELECT
    TO_CHAR(mr.month, 'Month YYYY') AS month,
    mr.category,
    mr.rating_count,
    mr.avg_rating,
    ca.category_avg_rating,
    ROUND(mr.avg_rating - ca.category_avg_rating, 2) AS diff_from_category_avg,
    mr.positive_rating_percent,
    ot.overall_avg_rating,
    CASE
        WHEN mr.avg_rating > LEAD(mr.avg_rating, 1) OVER (PARTITION BY mr.category ORDER BY mr.month) THEN 'Improving'
        WHEN mr.avg_rating < LEAD(mr.avg_rating, 1) OVER (PARTITION BY mr.category ORDER BY mr.month) THEN 'Declining'
        ELSE 'Stable'
    END AS trend_direction
FROM
    monthly_ratings mr
JOIN
    category_avg ca ON mr.category = ca.category
JOIN
    overall_trend ot ON mr.month = ot.month
ORDER BY
    mr.month DESC,
    mr.category; 