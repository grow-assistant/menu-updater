"""Menu analytics functions for AI context"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from utils.database_functions import get_location_settings

def get_recent_operations(connection, location_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent menu operations for a location"""
    try:
        settings = get_location_settings(connection, location_id)
        if isinstance(settings, str):  # Error message returned
            return []
        history = settings.get('operation_history', [])
        return history[:limit]
    except Exception as e:
        return []

def get_popular_items(connection, location_id: int) -> List[Dict[str, Any]]:
    """Get popular menu items based on analytics"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT i.id, i.name, i.price, 
                       a.views, a.orders, a.revenue,
                       a.last_ordered
                FROM items i
                JOIN menu_item_analytics a ON i.id = a.item_id
                JOIN categories c ON i.category_id = c.id
                JOIN menus m ON c.menu_id = m.id
                WHERE m.location_id = %s
                  AND i.disabled = false
                ORDER BY a.orders DESC, a.revenue DESC
                LIMIT 10
            """, (location_id,))
            columns = ['id', 'name', 'price', 'views', 'orders', 'revenue', 'last_ordered']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        return []

def analyze_time_patterns(connection, location_id: int) -> Dict[str, Any]:
    """Analyze time-based ordering patterns"""
    try:
        with connection.cursor() as cursor:
            # Get items with time restrictions
            cursor.execute("""
                SELECT c.name as category,
                       c.start_time,
                       c.end_time,
                       COUNT(DISTINCT i.id) as item_count,
                       SUM(a.orders) as total_orders
                FROM categories c
                JOIN items i ON i.category_id = c.id
                JOIN menu_item_analytics a ON i.id = a.item_id
                WHERE c.menu_id IN (
                    SELECT id FROM menus WHERE location_id = %s
                )
                AND c.start_time IS NOT NULL
                GROUP BY c.name, c.start_time, c.end_time
                ORDER BY c.start_time
            """, (location_id,))
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'category': row[0],
                    'time_range': f"{row[1]:04d}-{row[2]:04d}",
                    'items': row[3],
                    'orders': row[4]
                })
            
            return {
                'time_based_categories': patterns,
                'analysis_date': datetime.now().isoformat()
            }
    except Exception as e:
        return {'error': str(e)}

def get_category_relationships(connection, location_id: int) -> Dict[str, List[str]]:
    """Get commonly ordered category combinations"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH order_categories AS (
                    SELECT DISTINCT o.id as order_id,
                           c.name as category_name
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN items i ON oi.item_id = i.id
                    JOIN categories c ON i.category_id = c.id
                    JOIN menus m ON c.menu_id = m.id
                    WHERE m.location_id = %s
                ),
                category_pairs AS (
                    SELECT a.category_name as cat1,
                           b.category_name as cat2,
                           COUNT(*) as frequency
                    FROM order_categories a
                    JOIN order_categories b ON a.order_id = b.order_id
                    WHERE a.category_name < b.category_name
                    GROUP BY a.category_name, b.category_name
                    HAVING COUNT(*) >= 5
                    ORDER BY COUNT(*) DESC
                )
                SELECT cat1, cat2, frequency
                FROM category_pairs
                LIMIT 10
            """, (location_id,))
            
            relationships = {}
            for row in cursor.fetchall():
                if row[0] not in relationships:
                    relationships[row[0]] = []
                relationships[row[0]].append({
                    'category': row[1],
                    'frequency': row[2]
                })
            
            return relationships
    except Exception as e:
        return {}
