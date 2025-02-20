"""Analytics functions for menu suggestions"""
from typing import List, Dict, Any
from datetime import datetime, timedelta

def get_item_suggestions(connection, item_id: int) -> List[Dict[str, Any]]:
    """Get cross-sell suggestions based on order history"""
    try:
        with connection.cursor() as cursor:
            # Find items frequently ordered together
            cursor.execute("""
                WITH item_orders AS (
                    SELECT DISTINCT order_id 
                    FROM order_items 
                    WHERE item_id = %s
                ),
                related_items AS (
                    SELECT 
                        i.id,
                        i.name,
                        i.price,
                        c.name as category,
                        COUNT(*) as co_occurrence,
                        ROUND(COUNT(*) * 100.0 / (
                            SELECT COUNT(DISTINCT order_id) 
                            FROM order_items 
                            WHERE item_id = %s
                        ), 2) as order_percentage
                    FROM order_items oi
                    JOIN item_orders io ON oi.order_id = io.order_id
                    JOIN items i ON oi.item_id = i.id
                    JOIN categories c ON i.category_id = c.id
                    WHERE oi.item_id != %s
                      AND i.disabled = false
                      AND c.disabled = false
                    GROUP BY i.id, i.name, i.price, c.name
                    HAVING COUNT(*) >= 5
                    ORDER BY co_occurrence DESC, order_percentage DESC
                    LIMIT 5
                )
                SELECT 
                    id,
                    name,
                    price,
                    category,
                    co_occurrence as times_ordered_together,
                    order_percentage as percentage_of_orders
                FROM related_items;
            """, (item_id, item_id, item_id))
            
            columns = ['id', 'name', 'price', 'category', 'times_ordered_together', 'percentage_of_orders']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        return []

def get_category_suggestions(connection, category_id: int) -> List[Dict[str, Any]]:
    """Get cross-sell suggestions based on category relationships"""
    try:
        with connection.cursor() as cursor:
            # Find categories frequently ordered together
            cursor.execute("""
                WITH category_orders AS (
                    SELECT DISTINCT o.id as order_id
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN items i ON oi.item_id = i.id
                    WHERE i.category_id = %s
                ),
                related_categories AS (
                    SELECT 
                        c.id,
                        c.name,
                        COUNT(DISTINCT co.order_id) as co_occurrence,
                        ROUND(COUNT(DISTINCT co.order_id) * 100.0 / (
                            SELECT COUNT(*) FROM category_orders
                        ), 2) as order_percentage,
                        ARRAY_AGG(DISTINCT i.name) as popular_items
                    FROM category_orders co
                    JOIN order_items oi ON co.order_id = oi.order_id
                    JOIN items i ON oi.item_id = i.id
                    JOIN categories c ON i.category_id = c.id
                    WHERE c.id != %s
                      AND c.disabled = false
                    GROUP BY c.id, c.name
                    HAVING COUNT(DISTINCT co.order_id) >= 3
                    ORDER BY co_occurrence DESC
                    LIMIT 3
                )
                SELECT 
                    id,
                    name,
                    co_occurrence as times_ordered_together,
                    order_percentage as percentage_of_orders,
                    popular_items
                FROM related_categories;
            """, (category_id, category_id))
            
            columns = ['id', 'name', 'times_ordered_together', 'percentage_of_orders', 'popular_items']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        return []

def format_suggestion_message(item_suggestions: List[Dict[str, Any]], 
                            category_suggestions: List[Dict[str, Any]]) -> str:
    """Format suggestions into a readable message"""
    message_parts = []
    
    if item_suggestions:
        items = "\n".join(
            f"• {item['name']} (${item['price']:.2f}) - "
            f"ordered together {item['times_ordered_together']} times "
            f"({item['percentage_of_orders']}% of orders)"
            for item in item_suggestions
        )
        message_parts.append(f"Suggested items:\n{items}")
    
    if category_suggestions:
        categories = "\n".join(
            f"• {cat['name']} - appears in {cat['percentage_of_orders']}% "
            f"of orders with popular items: {', '.join(cat['popular_items'][:3])}"
            for cat in category_suggestions
        )
        message_parts.append(f"Suggested categories:\n{categories}")
    
    return "\n\n".join(message_parts) if message_parts else "No suggestions available"
