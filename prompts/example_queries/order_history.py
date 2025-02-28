"""
Example queries for order history related operations.
"""

ORDER_HISTORY_QUERIES = """
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

6. New customers acquired in the last week:
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

7. Percentage of orders from repeat customers:
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

8. Canceled orders in the past month:
--------------------------------------------------
SELECT COUNT(*) as canceled_orders
FROM orders
WHERE location_id = 62
  AND (created_at - INTERVAL '7 hours')::date >= CURRENT_DATE - INTERVAL '1 month'
  AND status IN (6);

9. Average time between first and second order (hours):
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

10. Lifetime value of our average customer:
--------------------------------------------------
SELECT AVG(total_spent) as avg_lifetime_value
FROM (
    SELECT customer_id, SUM(total) as total_spent
    FROM orders
    WHERE location_id = 62
      AND status = 7
    GROUP BY customer_id
) sub;

11. Order details with correct discount handling:
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