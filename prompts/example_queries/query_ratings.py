"""
Example queries for analyzing customer ratings and feedback.
"""

QUERY_RATINGS_QUERIES = """
These example queries demonstrate how to analyze customer ratings and feedback:

1. Basic rating pattern (CANONICAL EXAMPLE):
--------------------------------------------------
/* REQUIRED PATTERN - Use this structure for all rating queries */
SELECT 
    -- Total orders
    COUNT(DISTINCT o.id) AS total_orders,
    
    -- Orders with actual ratings (has feedback)
    COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) AS orders_with_ratings,
    
    -- Orders without ratings (includes empty rating entries)
    COUNT(DISTINCT CASE WHEN f.id IS NULL THEN o.id END) AS orders_without_ratings,
    
    -- Average rating (only for orders with feedback)
    CASE 
        WHEN COUNT(f.id) > 0 THEN ROUND(AVG(f.value), 2)
        ELSE NULL
    END AS average_rating,
    
    -- Percent with ratings
    ROUND(
        COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) * 100.0 
        / NULLIF(COUNT(DISTINCT o.id), 0), 
        1
    ) AS percent_with_ratings
FROM orders o
LEFT JOIN order_ratings r ON o.id = r.order_id
LEFT JOIN order_ratings_feedback f ON r.id = f.rating_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date = '2025-02-21';

2. Rating breakdown by category:
--------------------------------------------------
/* IMPORTANT: Always check f.id IS NOT NULL, not r.id IS NOT NULL */
SELECT 
    rc.label AS rating_category,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) AS orders_with_ratings,
    ROUND(
        COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN o.id END) * 100.0 
        / NULLIF(COUNT(DISTINCT o.id), 0), 
        1
    ) AS percent_with_ratings,
    CASE 
        WHEN COUNT(f.id) > 0 THEN ROUND(AVG(f.value), 2)
        ELSE NULL
    END AS average_rating
FROM orders o
LEFT JOIN order_ratings r ON o.id = r.order_id
LEFT JOIN order_ratings_feedback f ON r.id = f.rating_id
LEFT JOIN rating_categories rc ON f.category_id = rc.id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date BETWEEN '2025-02-01' AND '2025-02-28'
GROUP BY rc.label
ORDER BY rc.label;

3. Items most frequently found in low-rated orders:
--------------------------------------------------
SELECT 
    i.name AS item_name,
    COUNT(DISTINCT o.id) AS order_count,
    ROUND(AVG(orf.value), 2) AS average_rating
FROM orders o
INNER JOIN order_items oi ON o.id = oi.order_id
INNER JOIN items i ON oi.item_id = i.id
INNER JOIN order_ratings r ON o.id = r.order_id
INNER JOIN order_ratings_feedback orf ON r.id = orf.rating_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '90 days'
  AND orf.value < 4
GROUP BY i.name
HAVING COUNT(DISTINCT o.id) > 2
ORDER BY order_count DESC, average_rating ASC
LIMIT 10;

4. Time-based analysis of order ratings with complete counts:
--------------------------------------------------
SELECT 
    EXTRACT(HOUR FROM (o.updated_at - INTERVAL '7 hours')) AS hour_of_day,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN o.id END) AS orders_with_ratings,
    COUNT(DISTINCT CASE WHEN r.id IS NULL THEN o.id END) AS orders_without_ratings,
    ROUND(AVG(CASE WHEN r.id IS NOT NULL THEN orf.value ELSE NULL END), 2) AS average_rating,
    ROUND(COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN o.id END) * 100.0 / NULLIF(COUNT(DISTINCT o.id), 0), 1) AS percent_rated
FROM orders o
LEFT JOIN order_ratings r ON o.id = r.order_id
LEFT JOIN order_ratings_feedback orf ON r.id = orf.rating_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY EXTRACT(HOUR FROM (o.updated_at - INTERVAL '7 hours'))
ORDER BY hour_of_day;

5. Orders with feedback or comments:
--------------------------------------------------
SELECT 
    o.id AS order_id,
    u.first_name || ' ' || u.last_name AS customer,
    o.updated_at - INTERVAL '7 hours' AS order_time,
    rf.value AS rating,
    rf.comment AS feedback
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN order_ratings_feedback rf ON o.id = rf.order_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
  AND rf.comment IS NOT NULL
  AND LENGTH(TRIM(rf.comment)) > 0
ORDER BY o.updated_at DESC;

6. Comparing ratings across different time periods:
--------------------------------------------------
WITH current_period AS (
    SELECT 
        AVG(rf.value) AS avg_rating,
        COUNT(*) AS rating_count
    FROM orders o
    INNER JOIN order_ratings_feedback rf ON o.id = rf.order_id
    WHERE o.location_id = 62
      AND o.status = 7
      AND (o.updated_at - INTERVAL '7 hours')::date BETWEEN CURRENT_DATE - INTERVAL '30 days' AND CURRENT_DATE
),
previous_period AS (
    SELECT 
        AVG(rf.value) AS avg_rating,
        COUNT(*) AS rating_count
    FROM orders o
    INNER JOIN order_ratings_feedback rf ON o.id = rf.order_id
    WHERE o.location_id = 62
      AND o.status = 7
      AND (o.updated_at - INTERVAL '7 hours')::date BETWEEN CURRENT_DATE - INTERVAL '60 days' AND CURRENT_DATE - INTERVAL '31 days'
)
SELECT 
    c.avg_rating AS current_avg_rating,
    c.rating_count AS current_rating_count,
    p.avg_rating AS previous_avg_rating,
    p.rating_count AS previous_rating_count,
    ROUND((c.avg_rating - p.avg_rating), 2) AS rating_change,
    CASE 
        WHEN c.avg_rating > p.avg_rating THEN 'Improved' 
        WHEN c.avg_rating < p.avg_rating THEN 'Declined'
        ELSE 'Unchanged'
    END AS trend
FROM current_period c, previous_period p;

7. Daily order ratings with complete counts:
--------------------------------------------------
SELECT 
    (o.updated_at - INTERVAL '7 hours')::date AS order_date,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT CASE WHEN orf.id IS NOT NULL THEN o.id END) AS orders_with_ratings,
    COUNT(DISTINCT CASE WHEN orf.id IS NULL THEN o.id END) AS orders_without_ratings,
    CASE 
        WHEN COUNT(orf.id) > 0 THEN ROUND(AVG(orf.value), 2)
        ELSE NULL
    END AS average_rating,
    ROUND(COUNT(DISTINCT CASE WHEN orf.id IS NOT NULL THEN o.id END) * 100.0 / NULLIF(COUNT(DISTINCT o.id), 0), 1) AS percent_rated
FROM orders o
LEFT JOIN order_ratings r ON o.id = r.order_id
LEFT JOIN order_ratings_feedback orf ON r.id = orf.rating_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY (o.updated_at - INTERVAL '7 hours')::date
ORDER BY order_date DESC;

8. Detailed order ratings with categorization:
--------------------------------------------------
SELECT
    l.name as location_name,
    o.id AS order_id,
    o.status AS order_status,
    u.id AS user_id,
    u.first_name || ' ' || u.last_name AS customer,
    o.updated_at - INTERVAL '7 hours' AS order_time,
    o.total AS order_total,
    r.id AS rating_id,
    r.created_at AS rating_created_at,
    r.updated_at AS rating_updated_at,
    r.acknowledged AS rating_acknowledged,
    f.id AS feedback_id,
    rc.label AS category_label,
    CASE 
        WHEN rc.label = 'How was your service?' THEN 'Service'
        WHEN rc.label = 'How was your order experience?' THEN 'Order Experience' 
        WHEN rc.label = 'How was your food?' THEN 'Food' 
        ELSE NULL 
    END AS feedback_category,
    f.value AS rating,
    f.notes AS feedback_notes,
    COALESCE(rr.label,'') AS reason
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
INNER JOIN order_ratings r on r.order_id = o.id 
INNER JOIN (
    SELECT DISTINCT ON (rating_id, category_id) 
        id, rating_id, category_id, value, notes
    FROM order_ratings_feedback
    ORDER BY rating_id, category_id, id DESC
) f on f.rating_id = r.id
LEFT JOIN order_ratings_feedback_responses fr on fr.feedback_id = f.id
LEFT JOIN rating_responses rr on rr.id = fr.response_id
LEFT JOIN rating_categories rc on rc.id = f.category_id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date = '2025-02-21'
ORDER BY r.id DESC, f.id DESC, o.updated_at DESC;
""" 