-- Customer order frequency analysis (customer_order_frequency)
-- Identifies frequency patterns in customer ordering behavior

WITH customer_orders AS (
    SELECT
        o.customer_id,
        u.first_name || ' ' || u.last_name AS customer_name,
        u.phone,
        u.email,
        COUNT(o.id) AS total_orders,
        MIN(o.updated_at) AS first_updated_at,
        MAX(o.updated_at) AS last_updated_at,
        AVG(o.total) AS avg_order_value,
        SUM(o.total) AS total_spent
    FROM
        orders o
    JOIN
        users u ON o.customer_id = u.id
    WHERE
        o.location_id = 62
        AND o.status = 7
        AND o.updated_at >= CURRENT_DATE - INTERVAL '180 days'
    GROUP BY
        o.customer_id, u.first_name, u.last_name, u.phone, u.email
    HAVING
        COUNT(o.id) >= 3
),
frequency_metrics AS (
    SELECT
        co.*,
        (last_updated_at - first_updated_at) AS customer_lifespan,
        CASE 
            WHEN (last_updated_at - first_updated_at) > INTERVAL '0 days' 
            THEN total_orders / EXTRACT(EPOCH FROM (last_updated_at - first_updated_at)) * 86400 
            ELSE 0 
        END AS orders_per_day,
        CASE 
            WHEN (last_updated_at - first_updated_at) > INTERVAL '0 days' 
            THEN EXTRACT(EPOCH FROM (last_updated_at - first_updated_at)) / total_orders / 86400
            ELSE 0 
        END AS avg_days_between_orders
    FROM 
        customer_orders co
)
SELECT
    customer_name,
    phone,
    email,
    total_orders,
    first_updated_at,
    last_updated_at,
    EXTRACT(DAY FROM customer_lifespan)::integer AS days_as_customer,
    ROUND(avg_order_value::numeric, 2) AS avg_order_value,
    ROUND(total_spent::numeric, 2) AS total_spent,
    ROUND(avg_days_between_orders::numeric, 1) AS avg_days_between_orders,
    CASE
        WHEN avg_days_between_orders <= 7 THEN 'Weekly Customer'
        WHEN avg_days_between_orders <= 14 THEN 'Bi-Weekly Customer'
        WHEN avg_days_between_orders <= 30 THEN 'Monthly Customer'
        ELSE 'Occasional Customer'
    END AS frequency_segment,
    -- Days since last order
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - last_updated_at))::integer AS days_since_last_order,
    -- At risk flag (if last order was more than 2x their average interval)
    CASE 
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - last_updated_at))::integer > 
             (avg_days_between_orders * 2) 
        THEN 'At Risk'
        ELSE 'Active'
    END AS status
FROM
    frequency_metrics
ORDER BY
    avg_days_between_orders; 