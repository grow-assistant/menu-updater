SET myvars.location_id_var = 61;
SET myvars.location_id_var_2 = 66;

WITH order_level_data AS (
    SELECT 
        o.id AS order_id,
        o.location_id,
        o.status,
        1 AS order_quantity,
        m.name AS order_location,
        o.updated_at - INTERVAL '4 hours' AS order_date,
        DATE(o.updated_at - INTERVAL '4 hours') AS order_day,
        EXTRACT(HOUR FROM (o.updated_at - INTERVAL '4 hours')) AS order_hour
    FROM orders o
    LEFT JOIN markers m ON o.marker_id = m.id
    WHERE o.location_id IN (current_setting('myvars.location_id_var')::integer,current_setting('myvars.location_id_var_2')::integer)
        AND o.status > 0
        AND o.status != 6
),

daily_peaks AS (
    SELECT 
        'Daily Peak' as peak_type,
        order_location,
        order_day as peak_date,
        NULL as peak_hour,
        COUNT(*) as order_count
    FROM order_level_data
    GROUP BY order_location, order_day
    ORDER BY COUNT(*) DESC
    LIMIT 1
),

hourly_peaks AS (
    SELECT 
        'Hourly Peak' as peak_type,
        order_location,
        order_day as peak_date,
        order_hour as peak_hour,
        COUNT(*) as order_count
    FROM order_level_data
    GROUP BY order_location, order_day, order_hour
    ORDER BY COUNT(*) DESC
    LIMIT 1
)

SELECT * FROM daily_peaks
UNION ALL
SELECT * FROM hourly_peaks
ORDER BY peak_type; 