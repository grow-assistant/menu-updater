-- Query items with specific dietary restrictions (dietary_restrictions)
-- Finds items matching dietary keywords in their descriptions since item_tags table doesn't exist

SELECT 
    i.id, 
    i.name AS item_name, 
    i.description,
    i.price, 
    c.name AS category,
    CASE
        WHEN i.description ILIKE '%vegetarian%' THEN 'Vegetarian'
        WHEN i.description ILIKE '%vegan%' THEN 'Vegan'
        WHEN i.description ILIKE '%gluten-free%' OR i.description ILIKE '%gluten free%' THEN 'Gluten-Free'
        WHEN i.description ILIKE '%dairy-free%' OR i.description ILIKE '%dairy free%' THEN 'Dairy-Free'
        ELSE 'No dietary tag found'
    END AS primary_dietary_tag,
    -- Create an array of applicable tags for each item
    ARRAY_REMOVE(ARRAY[
        CASE WHEN i.description ILIKE '%vegetarian%' THEN 'Vegetarian' ELSE NULL END,
        CASE WHEN i.description ILIKE '%vegan%' THEN 'Vegan' ELSE NULL END,
        CASE WHEN i.description ILIKE '%gluten-free%' OR i.description ILIKE '%gluten free%' THEN 'Gluten-Free' ELSE NULL END,
        CASE WHEN i.description ILIKE '%dairy-free%' OR i.description ILIKE '%dairy free%' THEN 'Dairy-Free' ELSE NULL END,
        CASE WHEN i.description ILIKE '%nut-free%' OR i.description ILIKE '%nut free%' THEN 'Nut-Free' ELSE NULL END
    ], NULL) AS dietary_tags
FROM 
    items i
JOIN 
    categories c ON i.category_id = c.id
JOIN 
    menus m ON c.menu_id = m.id
WHERE 
    m.location_id = 62
    AND i.disabled = FALSE
    AND (
        i.description ILIKE '%vegetarian%' 
        OR i.description ILIKE '%vegan%' 
        OR i.description ILIKE '%gluten-free%'
        OR i.description ILIKE '%gluten free%'
        OR i.description ILIKE '%dairy-free%'
        OR i.description ILIKE '%dairy free%'
    )
ORDER BY 
    c.name, i.name; 