EXAMPLE_QUERIES = """
Examples of queries used in our project for context:

1. Yesterday's order details:
--------------------------------------------------
SELECT
    l.id,
    l.name as location_name,
    o.id AS order_id,
    o.status AS order_status,
    o.total AS order_total,
    u.id AS user_id,
    u.phone AS user_phone,
    u.email AS user_email,
    o.updated_at - INTERVAL '7 hours' AS order_date,
    o.tip as tip,
    u.first_name || ' ' || u.last_name AS customer,
    COALESCE(d.amount, 0) as discount_amount
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
WHERE l.id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date = CURRENT_DATE - INTERVAL '1 day';

2. Total sales revenue for the past month:
--------------------------------------------------
SELECT COALESCE(SUM(total), 0) as total_revenue
FROM orders
WHERE location_id = 62
  AND (created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'
  AND status = 7;

3. This month's sales revenue:
--------------------------------------------------
SELECT COALESCE(SUM(total), 0) as current_month_revenue
FROM orders
WHERE location_id = 62
  AND date_trunc('month', (created_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE)
  AND status = 7;

4. Same month last year's sales revenue:
--------------------------------------------------
SELECT COALESCE(SUM(total), 0) as last_year_same_month_revenue
FROM orders
WHERE location_id = 62
  AND date_trunc('month', (created_at - INTERVAL '7 hours')) = date_trunc('month', CURRENT_DATE - INTERVAL '1 year')
  AND status = 7;

5. Top 5 menu items by revenue in the past quarter:
--------------------------------------------------
SELECT i.name as menu_item, COUNT(oi.id) as order_count,
       COALESCE(SUM(i.price * oi.quantity), 0) as revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN items i ON oi.item_id = i.id
WHERE o.location_id = 62
  AND (o.created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '3 months'
  AND o.status = 7
GROUP BY i.name
ORDER BY revenue DESC
LIMIT 5;

6. Average order value over the past six months:
--------------------------------------------------
SELECT COALESCE(AVG(total), 0) as avg_order_value
FROM orders
WHERE location_id = 62
  AND (created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '6 months'
  AND status = 7;

7. New customers acquired in the last week:
--------------------------------------------------
WITH first_orders AS (
    SELECT customer_id, MIN((created_at - INTERVAL '7 hours')::date) as first_order_date
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
)
SELECT COUNT(*) as new_customers
FROM first_orders
WHERE first_order_date >= CURRENT_DATE - INTERVAL '7 days';

8. Percentage of orders from repeat customers:
--------------------------------------------------
WITH customer_orders AS (
    SELECT customer_id, COUNT(*) as order_count
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
),
repeat_customers AS (
    SELECT customer_id
    FROM customer_orders
    WHERE order_count > 1
)
SELECT 
    (SELECT COUNT(*) FROM orders o 
     WHERE o.location_id = 62 AND o.status = 7 
       AND o.customer_id IN (SELECT customer_id FROM repeat_customers)
    ) * 100.0
    / NULLIF((SELECT COUNT(*) FROM orders o 
              WHERE o.location_id = 62 AND o.status = 7), 0)
    AS repeat_percentage;

9. Peak ordering hours (top 3):
--------------------------------------------------
SELECT EXTRACT(HOUR FROM (created_at - INTERVAL '7 hours')) as order_hour,
       COUNT(*) as order_count
FROM orders
WHERE location_id = 62
GROUP BY order_hour
ORDER BY order_count DESC
LIMIT 3;

10. Days of the week with highest order volume:
--------------------------------------------------
SELECT TRIM(TO_CHAR((created_at - INTERVAL '7 hours'), 'Day')) as order_day,
       COUNT(*) as order_count
FROM orders
WHERE location_id = 62
GROUP BY TRIM(TO_CHAR((created_at - INTERVAL '7 hours'), 'Day'))
ORDER BY order_count DESC;

11. Average fulfillment time (minutes):
--------------------------------------------------
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))/60 
       AS avg_fulfillment_time_minutes
FROM orders
WHERE location_id = 62
  AND status = 7
  AND (updated_at - created_at) BETWEEN INTERVAL '5 minutes' AND INTERVAL '4 hours';

12. Average delivery time (minutes) for app orders:
--------------------------------------------------
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))/60 
       AS avg_delivery_time_minutes
FROM orders
WHERE location_id = 62
  AND status = 7
  AND type = 1
  AND (updated_at - created_at) BETWEEN INTERVAL '5 minutes' AND INTERVAL '4 hours';

-- UPDATED RATING EXAMPLES --

13. Basic rating pattern (CANONICAL EXAMPLE):
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

14. Rating breakdown by category:
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

15. Canceled orders in the past month:
--------------------------------------------------
SELECT COUNT(*) as canceled_orders
FROM orders
WHERE location_id = 62
  AND (created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'
  AND status IN (6);

16. Menu categories with highest sales:
--------------------------------------------------
SELECT c.name as category, COUNT(DISTINCT o.id) as order_count,
       COALESCE(SUM(oi.quantity * i.price), 0) as total_revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN items i ON oi.item_id = i.id
JOIN categories c ON i.category_id = c.id
WHERE o.location_id = 62
  AND o.status = 7
GROUP BY c.name
ORDER BY total_revenue DESC;

16.1. List all menu categories for a specific location:
--------------------------------------------------
SELECT c.id, c.name, c.description, c.seq_num, m.name as menu_name
FROM categories c
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 16
ORDER BY c.seq_num;

16.2. Get all menu items in a specific category:
--------------------------------------------------
SELECT i.id, i.name, i.description, i.price, i.disabled
FROM items i
JOIN categories c ON i.category_id = c.id
JOIN menus m ON c.menu_id = m.id
WHERE m.location_id = 16
  AND c.name = 'Entrees'
ORDER BY i.seq_num;

17. Average time between first and second order (hours):
--------------------------------------------------
WITH first_two_orders AS (
  SELECT customer_id, created_at,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at) AS order_num
  FROM orders
  WHERE location_id = 62
    AND status = 7
),
first_second AS (
  SELECT customer_id,
         MIN(CASE WHEN order_num = 1 THEN created_at END) AS first_order,
         MIN(CASE WHEN order_num = 2 THEN created_at END) AS second_order
  FROM first_two_orders
  GROUP BY customer_id
)
SELECT AVG(EXTRACT(EPOCH FROM (second_order - first_order)))/3600 
       AS avg_hours_between_first_and_second
FROM first_second
WHERE second_order IS NOT NULL;

18. Lifetime value of our average customer:
--------------------------------------------------
SELECT AVG(total_spent) as avg_lifetime_value
FROM (
    SELECT customer_id, SUM(total) as total_spent
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
) sub;

19. Average order time with proper NULL handling:
--------------------------------------------------
SELECT 
    COALESCE(AVG(EXTRACT(EPOCH FROM (o.updated_at - o.created_at))), 0)/60 AS avg_order_time_minutes,
    MIN(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)))/60 AS min_order_time_minutes,
    MAX(EXTRACT(EPOCH FROM (o.updated_at - o.created_at)))/60 AS max_order_time_minutes,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT CASE WHEN (o.updated_at - o.created_at) IS NULL THEN o.id END) AS orders_with_null_time
FROM orders o
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
  AND (o.updated_at - o.created_at) BETWEEN INTERVAL '1 minute' AND INTERVAL '180 minutes';

20. Items most frequently found in low-rated orders:
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

21. Orders with specific items that have a zero value:
--------------------------------------------------
SELECT 
    o.id AS order_id,
    o.updated_at - INTERVAL '7 hours' AS order_time,
    i.name AS item_name,
    COALESCE(oi.price, 0) AS item_price,
    CASE 
        WHEN oi.price IS NULL OR oi.price = 0 THEN 'Yes' 
        ELSE 'No' 
    END AS is_zero_price
FROM orders o
INNER JOIN order_items oi ON o.id = oi.order_id
INNER JOIN items i ON oi.item_id = i.id
WHERE o.location_id = 62
  AND o.status = 7
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '30 days'
  AND (oi.price IS NULL OR oi.price = 0)
ORDER BY o.updated_at DESC;

22. Time-based analysis of order ratings with complete counts:
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

23. Orders with feedback or comments:
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

24. Comparing ratings across different time periods:
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

25. Daily order ratings with complete counts:
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

26. Detailed order ratings with categorization:
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

27. Daily order ratings with complete counts:
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

28. Detailed order ratings with categorization:
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

29. Order details with correct discount handling:
--------------------------------------------------
SELECT
    l.id,
    l.name as location_name,
    o.id AS order_id,
    o.status AS order_status,
    o.total AS order_total,
    u.id AS user_id,
    u.phone AS user_phone,
    u.email AS user_email,
    o.updated_at - INTERVAL '7 hours' AS order_date,
    o.tip as tip,
    u.first_name || ' ' || u.last_name AS customer,
    d.amount as discount_amount
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
WHERE l.id NOT IN (32,29)
  AND u.id NOT IN (19,644,928,174)
  AND o.status NOT IN (0,6)
  AND (o.updated_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 day';
"""
