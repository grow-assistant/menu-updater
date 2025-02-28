from datetime import datetime
from typing import Dict, List, Any, Tuple, Union


def add_operation_to_history(
    operation_type: str, details: Dict, status: str, connection
) -> None:
    """
    Add an operation to the history table
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO operation_history
            (operation_type, operation_details, status, timestamp)
            VALUES (%s, %s, %s, %s)
            """,
            (operation_type, str(details), status, datetime.now()),
        )
        connection.commit()
    except Exception as e:
        print(f"Error adding operation to history: {e}")
    finally:
        cursor.close()


def update_menu_item_price(
    item_id: int, new_price: float, connection
) -> Tuple[bool, str]:
    """
    Update the price of a menu item
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE menu_items SET price = %s WHERE item_id = %s", (new_price, item_id)
        )
        connection.commit()
        return True, "Price updated successfully"
    except Exception as e:
        return False, f"Error updating price: {e}"
    finally:
        cursor.close()


def update_category_time_range(
    category_id: int, start_time: str, end_time: str, connection
) -> Tuple[bool, str]:
    """
    Update the time range for a category
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE categories
            SET available_start_time = %s, available_end_time = %s
            WHERE category_id = %s
            """,
            (start_time, end_time, category_id),
        )
        connection.commit()
        return True, "Time range updated successfully"
    except Exception as e:
        return False, f"Error updating time range: {e}"
    finally:
        cursor.close()


def update_option_limits(
    option_id: int, min_selections: int, max_selections: int, connection
) -> Tuple[bool, str]:
    """
    Update the minimum and maximum selections for an option group
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE option_groups
            SET min_selections = %s, max_selections = %s
            WHERE option_group_id = %s
            """,
            (min_selections, max_selections, option_id),
        )
        connection.commit()
        return True, "Option limits updated successfully"
    except Exception as e:
        return False, f"Error updating option limits: {e}"
    finally:
        cursor.close()


def toggle_menu_item(
    item_name: str, disabled: bool = True, connection=None
) -> Tuple[bool, str]:
    """Toggle menu item enabled/disabled state

    Args:
        item_name: Name of the menu item
        disabled: True to disable, False to enable
        connection: Optional database connection

    Returns:
        Tuple of (success, message)
    """
    try:
        # Use existing disable_by_name function for transaction safety
        items = [{"id": None, "name": item_name}]
        success, message = disable_by_name(connection, "Menu Item", items)

        if success:
            action = "disabled" if disabled else "enabled"
            return True, f"Successfully {action} menu item: {item_name}"
        # Wrap error message to maintain consistent format
        return False, f"Error toggling menu item: {message.split(': ')[1]}"

    except Exception as e:
        return False, f"Error toggling menu item: {str(e)}"


def disable_by_name(
    connection, disable_type: str, items: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """Disable items or options by name with transaction safety"""
    # Prepare table name based on type
    if disable_type == "Menu Item":
        table = "items"
    elif disable_type == "Item Option":
        table = "options"
    else:
        table = "option_items"

    try:
        with connection:
            with connection.cursor() as cursor:
                # Set transaction isolation
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

                # Get IDs for locking
                ids = [item["id"] for item in items]
                id_list = ",".join(str(id) for id in ids)

                # Lock rows
                cursor.execute(
                    f"SELECT id FROM {table} WHERE id IN ({id_list}) FOR UPDATE"
                )

                # Perform update
                cursor.execute(
                    f"UPDATE {table} SET disabled = true WHERE id IN ({id_list})"
                )

                affected = cursor.rowcount
                return True, f"Successfully disabled {affected} {table}"

    except Exception as e:
        return False, f"Error disabling {table}: {str(e)}"


def disable_by_pattern(connection, pattern: str) -> Tuple[bool, str]:
    """Disable items matching a pattern with transaction safety"""
    try:
        with connection:
            with connection.cursor() as cursor:
                # Set transaction isolation
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

                # Find matching items
                cursor.execute(
                    """
                    SELECT i.id, i.name, c.name as category
                    FROM items i
                    JOIN categories c ON i.category_id = c.id
                    WHERE LOWER(i.name) LIKE %s
                    AND i.deleted_at IS NULL
                    AND i.disabled = false
                    FOR UPDATE
                """,
                    (f"%{pattern.lower()}%",),
                )
                items = cursor.fetchall()

                if not items:
                    return False, f"No active items found matching '{pattern}'"

                # Format items for confirmation
                items_str = "\n".join(f"- {item[1]} (in {item[2]})" for item in items)

                # Disable matching items
                cursor.execute(
                    """
                    UPDATE items
                    SET disabled = true
                    WHERE id = ANY(%s)
                """,
                    ([item[0] for item in items],),
                )

                return True, f"Disabled {len(items)} items:\n{items_str}"

    except Exception as e:
        return False, f"Error disabling items: {str(e)}"


def disable_options_by_pattern(connection, pattern: str) -> Tuple[bool, str]:
    """Disable options for items matching a pattern with transaction safety"""
    try:
        with connection:
            with connection.cursor() as cursor:
                # Set transaction isolation
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

                # Find matching options
                cursor.execute(
                    """
                    SELECT o.id, o.name, i.name as item
                    FROM options o
                    JOIN items i ON o.item_id = i.id
                    WHERE LOWER(i.name) LIKE %s
                    AND o.deleted_at IS NULL
                    AND o.disabled = false
                    FOR UPDATE
                """,
                    (f"%{pattern.lower()}%",),
                )
                options = cursor.fetchall()

                if not options:
                    return (
                        False,
                        f"No active options found for items matching '{pattern}'",
                    )

                # Format options for confirmation
                options_str = "\n".join(
                    f"- {option[1]} (for {option[2]})" for option in options
                )

                # Disable matching options
                cursor.execute(
                    """
                    UPDATE options
                    SET disabled = true
                    WHERE id = ANY(%s)
                """,
                    ([option[0] for option in options],),
                )

                return True, f"Disabled {len(options)} options:\n{options_str}"

    except Exception as e:
        return False, f"Error disabling options: {str(e)}"


def disable_option_items_by_pattern(connection, pattern: str) -> Tuple[bool, str]:
    """Disable option items for items matching a pattern with transaction safety"""
    try:
        with connection:
            with connection.cursor() as cursor:
                # Set transaction isolation
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

                # Find matching option items
                cursor.execute(
                    """
                    SELECT oi.id, oi.name, o.name as option, i.name as item
                    FROM option_items oi
                    JOIN options o ON oi.option_id = o.id
                    JOIN items i ON o.item_id = i.id
                    WHERE LOWER(i.name) LIKE %s
                    AND oi.deleted_at IS NULL
                    AND oi.disabled = false
                    FOR UPDATE
                """,
                    (f"%{pattern.lower()}%",),
                )
                option_items = cursor.fetchall()

                if not option_items:
                    return (
                        False,
                        f"No active option items found for items matching '{pattern}'",
                    )

                # Format option items for confirmation
                items_str = "\n".join(
                    f"- {item[1]} (in {item[2]} for {item[3]})" for item in option_items
                )

                # Disable matching option items
                cursor.execute(
                    """
                    UPDATE option_items
                    SET disabled = true
                    WHERE id = ANY(%s)
                """,
                    ([item[0] for item in option_items],),
                )

                return True, f"Disabled {len(option_items)} option items:\n{items_str}"

    except Exception as e:
        return False, f"Error disabling option items: {str(e)}"
