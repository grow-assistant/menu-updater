-- Query low rated items (less than 5 rating) with detailed order and rating information
-- Using DISTINCT ON to eliminate duplicates based on feedback_id
SELECT DISTINCT ON (f.id)
    l.name as location_name,
    o.id AS order_id,
    o.status AS order_status,
    u.id AS user_id,
    o.updated_at - INTERVAL '7 hours' AS order_date,
    u.first_name || ' ' || u.last_name AS customer,
    r.id AS rating_id,
    r.created_at AS rating_created_at,
    r.updated_at AS rating_updated_at,
    r.acknowledged AS rating_acknowledged,
    f.id AS feedback_id,
    CASE 
        WHEN rc.label = 'How was your service?' THEN 'Service'
        WHEN rc.label = 'How was your order experience?' THEN 'Order Experience' 
        WHEN rc.label = 'How was your food?' THEN 'Food' 
        ELSE NULL 
    END as feedback_category,
    f.value AS rating,
    COALESCE(rr.label,'') AS reason,
    COALESCE(f.notes,'') as feedback_notes
FROM orders o
INNER JOIN users u ON o.customer_id = u.id
INNER JOIN locations l ON l.id = o.location_id
LEFT JOIN discounts d on d.order_id = o.id
INNER JOIN order_ratings r on r.order_id = o.id 
INNER JOIN order_ratings_feedback f on f.rating_id = r.id
LEFT JOIN order_ratings_feedback_responses fr on fr.feedback_id = f.id
LEFT JOIN rating_responses rr on rr.id = fr.response_id
LEFT JOIN rating_categories rc ON rc.id = f.category_id
WHERE 
    l.id = 62
    AND o.status <> 0
    AND r.acknowledged IS NOT NULL
    AND f.value < 5
ORDER BY 
    f.id DESC,
    COALESCE(rr.label,'') DESC, 
    COALESCE(f.notes,'') DESC;