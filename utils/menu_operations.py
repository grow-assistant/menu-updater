from datetime import datetime
import psycopg2
from typing import Dict, List, Optional, Tuple, Union

from typing import Dict, List, Any, Tuple, Union

def add_operation_to_history(
    operation_type: str,
    details: Dict,
    status: str,
    connection
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
            (operation_type, str(details), status, datetime.now())
        )
        connection.commit()
    except Exception as e:
        print(f"Error adding operation to history: {e}")
    finally:
        cursor.close()

def update_menu_item_price(
    item_id: int,
    new_price: float,
    connection
) -> Tuple[bool, str]:
    """
    Update the price of a menu item
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE menu_items SET price = %s WHERE item_id = %s",
            (new_price, item_id)
        )
        connection.commit()
        return True, "Price updated successfully"
    except Exception as e:
        return False, f"Error updating price: {e}"
    finally:
        cursor.close()

def update_category_time_range(
    category_id: int,
    start_time: str,
    end_time: str,
    connection
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
            (start_time, end_time, category_id)
        )
        connection.commit()
        return True, "Time range updated successfully"
    except Exception as e:
        return False, f"Error updating time range: {e}"
    finally:
        cursor.close()

def update_option_limits(
    option_id: int,
    min_selections: int,
    max_selections: int,
    connection
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
            (min_selections, max_selections, option_id)
        )
        connection.commit()
        return True, "Option limits updated successfully"
    except Exception as e:
        return False, f"Error updating option limits: {e}"
    finally:
        cursor.close()

def toggle_item_availability(
    item_id: int,
    is_available: bool,
    connection
) -> Tuple[bool, str]:
    """
    Toggle the availability status of a menu item
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE menu_items SET is_available = %s WHERE item_id = %s",
            (is_available, item_id)
        )
        connection.commit()
        return True, f"Item {'enabled' if is_available else 'disabled'} successfully"
    except Exception as e:
        return False, f"Error toggling item availability: {e}"
    finally:
        cursor.close() 

def disable_by_name(
    connection,
    disable_type: str,
    items: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """Disable items or options by name with transaction safety"""
    try:
        with connection:
            with connection.cursor() as cursor:
                # Set transaction isolation
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                
                # Prepare query based on type
                if disable_type == "Menu Item":
                    table = "items"
                elif disable_type == "Item Option":
                    table = "options"
                else:
                    table = "option_items"
                    
                # Get IDs for locking
                ids = [item["id"] for item in items]
                id_list = ",".join(str(id) for id in ids)
                
                # Lock rows
                cursor.execute(f"SELECT id FROM {table} WHERE id IN ({id_list}) FOR UPDATE")
                
                # Perform update
                cursor.execute(f"""
                    UPDATE {table}
                    SET disabled = true
                    WHERE id IN ({id_list})
                """)
                
                affected = cursor.rowcount
                return True, f"Successfully disabled {affected} {table}"
                
    except Exception as e:
        return False, f"Error disabling {disable_type}: {e}"
