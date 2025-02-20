"""Bulk operations for menu items"""
from typing import Dict, List, Any
import streamlit as st
from utils.ui_components import render_price_input, render_time_input

def render_bulk_editor(items: List[Dict[str, Any]], operation: str) -> Dict[int, Any]:
    """Render bulk editor for menu items
    
    Args:
        items: List of menu items
        operation: Type of update ('price' or 'time')
    
    Returns:
        Dict mapping item IDs to their new values
    """
    if not items:
        st.info("No items available for bulk update")
        return {}
    
    st.write("Select items to update:")
    updates = {}
    
    # Group items by category
    categories = {}
    for item in items:
        cat = item.get('category_name', 'Uncategorized')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # Create tabs for each category
    tabs = st.tabs(list(categories.keys()))
    for tab, (category, cat_items) in zip(tabs, categories.items()):
        with tab:
            # Select all checkbox for category
            select_all = st.checkbox(f"Select all in {category}", key=f"select_all_{category}")
            
            # Create columns for layout
            cols = st.columns([3, 2, 2])
            with cols[0]:
                st.write("Item")
            with cols[1]:
                st.write("Current Value")
            with cols[2]:
                st.write("New Value")
            
            # Render items
            for item in cat_items:
                cols = st.columns([3, 2, 2])
                
                # Item name and selection
                with cols[0]:
                    selected = st.checkbox(
                        item['name'],
                        value=select_all,
                        key=f"item_{item['id']}"
                    )
                
                # Current value
                with cols[1]:
                    if operation == 'price':
                        st.write(f"${item['price']:.2f}")
                    elif operation == 'time':
                        st.write(f"{item.get('start_time', 'N/A')} - {item.get('end_time', 'N/A')}")
                
                # New value input
                with cols[2]:
                    if selected:
                        if operation == 'price':
                            new_val = render_price_input("", f"price_{item['id']}")
                            if new_val is not None:
                                updates[item['id']] = new_val
                        elif operation == 'time':
                            new_val = render_time_input("", f"time_{item['id']}")
                            if new_val:
                                updates[item['id']] = new_val
    
    # Preview changes
    if updates:
        st.subheader("Preview Changes")
        for item in items:
            if item['id'] in updates:
                if operation == 'price':
                    st.write(f"• {item['name']}: ${item['price']:.2f} → ${updates[item['id']]:.2f}")
                elif operation == 'time':
                    st.write(f"• {item['name']}: {item.get('start_time', 'N/A')} → {updates[item['id']]}")
    
    return updates

def apply_bulk_updates(connection, updates: Dict[int, Any], operation: str) -> str:
    """Apply bulk updates to menu items
    
    Args:
        connection: Database connection
        updates: Dict mapping item IDs to new values
        operation: Type of update ('price' or 'time')
    
    Returns:
        Status message
    """
    try:
        with connection.cursor() as cursor:
            # Set transaction isolation level
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            
            # Build update query
            if operation == 'price':
                query = """
                    UPDATE items 
                    SET price = CASE id 
                        {}
                    END
                    WHERE id IN ({})
                """.format(
                    ' '.join(f"WHEN {id} THEN {val}" for id, val in updates.items()),
                    ','.join(str(id) for id in updates.keys())
                )
            elif operation == 'time':
                query = """
                    UPDATE categories 
                    SET start_time = CASE id 
                        {}
                    END
                    WHERE id IN ({})
                """.format(
                    ' '.join(f"WHEN {id} THEN {val}" for id, val in updates.items()),
                    ','.join(str(id) for id in updates.keys())
                )
            
            # Execute update with row-level locking
            cursor.execute(f"SELECT id FROM items WHERE id IN ({','.join(str(id) for id in updates.keys())}) FOR UPDATE")
            cursor.execute(query)
            affected = cursor.rowcount
            
            connection.commit()
            return f"Successfully updated {affected} items"
    except Exception as e:
        connection.rollback()
        return f"Error applying updates: {str(e)}"
