"""Menu analytics functions for AI context"""

from datetime import datetime
from typing import Dict, List, Any
from utils.database_functions import get_location_settings


def get_recent_operations(
    connection, location_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent menu operations for a location"""
    try:
        settings = get_location_settings(connection, location_id)
        if isinstance(settings, str):  # Error message returned
            return []
        history = settings.get("operation_history", [])
        return history[:limit]
    except Exception:
        return []


def get_popular_items(connection, location_id: int) -> List[Dict[str, Any]]:
    """Get popular menu items based on analytics"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
            """,
                (location_id,),
            )
            columns = [
                "id",
                "name",
                "price",
                "views",
                "orders",
                "revenue",
                "last_ordered",
            ]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:
        return []


def analyze_time_patterns(connection, location_id: int) -> Dict[str, Any]:
    """Analyze time-based ordering patterns"""
    try:
        with connection.cursor() as cursor:
            # Get items with time restrictions
            cursor.execute(
                """
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
            """,
                (location_id,),
            )

            patterns = []
            for row in cursor.fetchall():
                patterns.append(
                    {
                        "category": row[0],
                        "time_range": f"{row[1]:04d}-{row[2]:04d}",
                        "items": row[3],
                        "orders": row[4],
                    }
                )

            return {
                "time_based_categories": patterns,
                "analysis_date": datetime.now().isoformat(),
            }
    except Exception:
        return {"error": "Failed to analyze time patterns"}


def get_category_relationships(connection, location_id: int) -> Dict[str, List[str]]:
    """Get commonly ordered category combinations"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
            """,
                (location_id,),
            )

            relationships = {}
            for row in cursor.fetchall():
                if row[0] not in relationships:
                    relationships[row[0]] = []
                relationships[row[0]].append({"category": row[1], "frequency": row[2]})

            return relationships
    except Exception:
        return {}


def get_sales_by_menu_category(self, start_date, end_date):
    """Get sales by menu category for a given date range"""
    try:
        query = """
        SELECT
            i.category,
            COUNT(oi.id) as item_count,
            SUM(oi.price) as total_sales
        FROM
            order_items oi
        JOIN
            items i ON oi.item_id = i.id
        JOIN
            orders o ON oi.order_id = o.id
        WHERE
            o.status = 7 AND
            o.updated_at BETWEEN %s AND %s AND
            o.location_id = %s
        GROUP BY
            i.category
        ORDER BY
            total_sales DESC
        """
        return self.db.execute_query(query, (start_date, end_date, self.location_id))
    except Exception:
        # Log error or handle appropriately
        return {"success": False, "error": "Failed to get sales by category"}


def get_sales_by_item(self, start_date, end_date, limit=10):
    """Get sales by menu item for a given date range"""
    try:
        query = """
        SELECT
            i.name,
            i.category,
            COUNT(oi.id) as order_count,
            SUM(oi.price) as total_sales
        FROM
            order_items oi
        JOIN
            items i ON oi.item_id = i.id
        JOIN
            orders o ON oi.order_id = o.id
        WHERE
            o.status = 7 AND
            o.updated_at BETWEEN %s AND %s AND
            o.location_id = %s
        GROUP BY
            i.name, i.category
        ORDER BY
            total_sales DESC
        LIMIT %s
        """
        return self.db.execute_query(
            query, (start_date, end_date, self.location_id, limit)
        )
    except Exception:
        # Log error or handle appropriately
        return {"success": False, "error": "Failed to get sales by item"}


def get_item_performance_metrics(self, start_date, end_date):
    """Get comprehensive performance metrics for menu items"""
    try:
        query = """
        WITH OrderCounts AS (
            SELECT
                i.id as item_id,
                i.name as item_name,
                i.category,
                i.price as current_price,
                COUNT(oi.id) as order_count,
                SUM(oi.price) as total_revenue,
                AVG(oi.price) as avg_price_when_ordered,
                MIN(o.updated_at) as first_ordered,
                MAX(o.updated_at) as last_ordered
            FROM
                items i
            LEFT JOIN
                order_items oi ON i.id = oi.item_id
            LEFT JOIN
                orders o ON oi.order_id = o.id AND o.status = 7
                           AND o.updated_at BETWEEN %s AND %s
                           AND o.location_id = %s
            WHERE
                i.location_id = %s
            GROUP BY
                i.id, i.name, i.category, i.price
        )
        SELECT
            item_id,
            item_name,
            category,
            current_price,
            order_count,
            total_revenue,
            CASE
                WHEN order_count > 0 THEN total_revenue / order_count
                ELSE 0
            END as avg_revenue_per_order,
            avg_price_when_ordered,
            first_ordered,
            last_ordered,
            CASE
                WHEN order_count = 0 THEN 'Never ordered'
                WHEN last_ordered < NOW() - INTERVAL '14 days' THEN 'Inactive'
                WHEN order_count > 10 THEN 'High performer'
                ELSE 'Average'
            END as performance_category
        FROM
            OrderCounts
        ORDER BY
            total_revenue DESC
        """
        return self.db.execute_query(
            query, (start_date, end_date, self.location_id, self.location_id)
        )
    except Exception:
        # Log error or handle appropriately
        return {"success": False, "error": "Failed to get item performance metrics"}
