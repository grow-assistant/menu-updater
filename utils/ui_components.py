from typing import Dict, Any, List, Optional

"""UI components for menu operations with validation"""
import re
import streamlit as st

from utils.database_functions import execute_menu_query


def validate_menu_update(data: Dict[str, Any]) -> List[str]:
    """Validate menu updates in real-time"""
    errors = []

    # Price validation
    if "price" in data:
        try:
            price = float(data["price"])
            if price < 0:
                errors.append("Price must be non-negative")
            if price > 500:
                errors.append("Price cannot exceed $500.00")
            if len(str(price).split(".")[-1]) > 2:
                errors.append("Price cannot have more than 2 decimal places")
        except ValueError:
            errors.append("Invalid price format")

    # Time range validation
    if "start_time" in data or "end_time" in data:
        for key in ["start_time", "end_time"]:
            if key in data and data[key]:
                time_str = str(data[key])
                if not re.match(r"^([01]\d|2[0-3])([0-5]\d)$", time_str):
                    errors.append(
                        f"{key.replace('_', ' ').title()} must be in 24-hour format (0000-2359)"
                    )

    # Option limits validation
    if "min_selections" in data and "max_selections" in data:
        min_val = data["min_selections"]
        max_val = data["max_selections"]
        if min_val > max_val:
            errors.append("Minimum selections cannot exceed maximum")
        if max_val > 10:
            errors.append("Maximum selections cannot exceed 10")
        if min_val < 0:
            errors.append("Minimum selections cannot be negative")

    return errors


def render_price_input(label: str, key: str, default: float = 0.0) -> float:
    """Render price input with validation"""
    col1, col2 = st.columns([3, 1])
    with col1:
        price = st.number_input(
            label,
            min_value=0.0,
            max_value=500.0,
            value=default,
            step=0.01,
            key=key,
            help="Enter price (0.00 - 500.00)",
        )
    with col2:
        st.markdown(
            """
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Price Rules:
                • Must be non-negative
                • Maximum $500.00
                • Two decimal places
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )
    return price


def render_time_input(label: str, key: str, default: str = "") -> str:
    """Render time input with 24-hour format validation"""
    col1, col2 = st.columns([3, 1])
    with col1:
        time = st.text_input(
            label,
            value=default,
            key=key,
            help="Enter time in 24-hour format (0000-2359)",
        )
    with col2:
        st.markdown(
            """
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Time Format:
                • 24-hour format (0000-2359)
                • Examples: 0900, 1430, 2200
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    if time and not re.match(r"^([01]\d|2[0-3])([0-5]\d)$", time):
        st.error("Time must be in 24-hour format (0000-2359)")
    return time


def render_option_limits(
    min_label: str, max_label: str, key_prefix: str
) -> tuple[int, int]:
    """Render min/max selection limits with validation"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        min_val = st.number_input(
            min_label,
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"{key_prefix}_min",
        )

    with col2:
        max_val = st.number_input(
            max_label,
            min_value=min_val,
            max_value=10,
            value=max(min_val, 1),
            step=1,
            key=f"{key_prefix}_max",
        )

    with col3:
        st.markdown(
            """
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Selection Limits:
                • Min: 0-10 items
                • Max: Must be ≥ Min
                • Used for option groups
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    return min_val, max_val


def render_location_hours_editor():
    """Render UI for location hours management"""
    st.subheader("Location Hours Management")

    location_id = st.number_input("Location ID", min_value=1)
    day_of_week = st.selectbox(
        "Day of Week",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    )

    col1, col2 = st.columns(2)
    with col1:
        open_time = st.text_input("Open Time (HH:MM:SS)")
    with col2:
        close_time = st.text_input("Close Time (HH:MM:SS)")

    if st.button("Update Hours"):
        if not all([location_id, day_of_week, open_time, close_time]):
            st.error("All fields are required")
        else:
            return {
                "operation": "update_location_hours",
                "params": {
                    "location_id": location_id,
                    "day_of_week": day_of_week,
                    "open_time": open_time,
                    "close_time": close_time,
                },
            }
    return None


def render_marker_management():
    """Render UI for marker management"""
    st.subheader("Marker Management")

    location_id = st.number_input("Location ID", min_value=1, key="marker_loc_id")
    marker_name = st.text_input("Marker Name")
    disabled = st.checkbox("Disabled")

    if st.button("Add Marker"):
        if not all([location_id, marker_name]):
            st.error("Location ID and Marker Name are required")
        else:
            return {
                "operation": "add_marker",
                "params": {
                    "id": None,  # Will be auto-generated
                    "name": marker_name,
                    "disabled": disabled,
                    "location_id": location_id,
                    "deleted_at": None,
                },
            }
    return None


def render_disable_interface(connection) -> Dict[str, Any]:
    """Render interface for disabling items/options by name"""
    st.subheader("Disable Item/Option")

    # Item/Option selection
    disable_type = st.radio(
        "Select type to disable",
        ["Menu Item", "Item Option", "Option Item"],
        help="Choose whether to disable a menu item, an option, or an option item",
    )

    # Name input
    item_name = st.text_input(
        f"Enter {disable_type.lower()} name", help="Enter the exact name to disable"
    )

    if not item_name:
        return None

    # Query current state
    if disable_type == "Menu Item":
        query = """
            SELECT i.id, i.name, i.disabled, c.name as category
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.name ILIKE %s AND i.deleted_at IS NULL
        """
    elif disable_type == "Item Option":
        query = """
            SELECT o.id, o.name, o.disabled, i.name as item
            FROM options o
            JOIN items i ON o.item_id = i.id
            WHERE o.name ILIKE %s AND o.deleted_at IS NULL
        """
    else:  # Option Item
        query = """
            SELECT oi.id, oi.name, oi.disabled, o.name as option, i.name as item
            FROM option_items oi
            JOIN options o ON oi.option_id = o.id
            JOIN items i ON o.item_id = i.id
            WHERE oi.name ILIKE %s AND oi.deleted_at IS NULL
        """

    results = execute_menu_query(query, (item_name,))

    if not results:
        st.error(f"No {disable_type.lower()} found with name: {item_name}")
        return None

    # Show current state
    st.write("Current state:")
    for item in results:
        status = "Disabled" if item["disabled"] else "Enabled"
        if disable_type == "Menu Item":
            st.info(f"Item: {item['name']} ({status}) in category: {item['category']}")
        elif disable_type == "Item Option":
            st.info(f"Option: {item['name']} ({status}) for item: {item['item']}")
        else:
            st.info(
                f"Option Item: {item['name']} ({status}) for option: {item['option']} on item: {item['item']}"
            )

    # Confirmation
    if st.button(
        f"Disable {disable_type}", type="primary", help=f"Click to disable {item_name}"
    ):
        return {"type": disable_type, "name": item_name, "items": results}

    return None
