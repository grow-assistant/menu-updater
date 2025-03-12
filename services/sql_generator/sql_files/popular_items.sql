
        -- Query: What are your most popular items?
        -- Category: popular_items
        SELECT i.name, i.description, i.price, COUNT(oi.id) as order_count
        FROM items i
        JOIN order_items oi ON i.id = oi.item_id
        JOIN orders o ON oi.order_id = o.id
        WHERE i.disabled = FALSE
        GROUP BY i.id, i.name, i.description, i.price
        ORDER BY order_count DESC
        LIMIT 5;
        