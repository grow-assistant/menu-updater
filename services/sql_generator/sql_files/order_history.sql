
        -- Query: What did I order last time?
        -- Category: order_history
        SELECT i.name, oi.quantity, i.price, o.created_at
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN items i ON oi.item_id = i.id
        WHERE o.customer_id = 123 -- This would be replaced with the actual user_id
        ORDER BY o.created_at DESC
        LIMIT 10;
        