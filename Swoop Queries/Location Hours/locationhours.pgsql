
SELECT 
	l.id AS location_id,
	l.name AS location_name
FROM locations l 
INNER JOIN location_hours lh on l.id = lh.location_id
WHERE 
	l.id IN (61)
	
