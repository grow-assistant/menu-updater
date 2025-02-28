UPDATE location_hours
SET 
    updated_at = CURRENT_TIMESTAMP,
    open_time = '11:00:00',
    close_time = '21:00:00'
WHERE 
    location_id = 62
    AND day_of_week = 'Monday';
