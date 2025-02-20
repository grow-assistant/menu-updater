"""Option management operations"""
from typing import Dict, List, Any
import streamlit as st

def get_item_options(connection, item_id: int) -> List[Dict[str, Any]]:
    """Get options for an item"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT o.*, array_agg(oi.*) as option_items
            FROM options o
            LEFT JOIN option_items oi ON o.id = oi.option_id
            WHERE o.item_id = %s AND o.disabled = false
            GROUP BY o.id
            ORDER BY o.name
        """, (item_id,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def copy_options(connection, source_id: int, target_id: int, selected_options: List[int]) -> str:
    """Copy selected options from source to target item"""
    try:
        with connection.cursor() as cursor:
            # Set transaction isolation level
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            
            # Get selected options with their items
            cursor.execute("""
                SELECT o.*, array_agg(oi.*) as option_items
                FROM options o
                LEFT JOIN option_items oi ON o.id = oi.option_id
                WHERE o.id = ANY(%s)
                GROUP BY o.id
            """, (selected_options,))
            options = cursor.fetchall()
            
            # Copy each option and its items
            for option in options:
                # Create new option
                cursor.execute("""
                    INSERT INTO options (name, description, min, max, item_id, disabled)
                    VALUES (%s, %s, %s, %s, %s, false)
                    RETURNING id
                """, (option['name'], option['description'], 
                      option['min'], option['max'], target_id))
                new_option_id = cursor.fetchone()[0]
                
                # Copy option items
                if option['option_items'][0] is not None:  # Check if there are items
                    items_data = []
                    for item in option['option_items']:
                        items_data.append((
                            new_option_id,
                            item['name'],
                            item['description'],
                            item['price'],
                            False  # disabled
                        ))
                    
                    cursor.executemany("""
                        INSERT INTO option_items (option_id, name, description, price, disabled)
                        VALUES (%s, %s, %s, %s, %s)
                    """, items_data)
            
            connection.commit()
            return f"Successfully copied {len(options)} options"
    except Exception as e:
        connection.rollback()
        return f"Error copying options: {str(e)}"

def render_option_copy_interface(connection):
    """Render interface for copying options between items"""
    st.subheader("Copy Options Between Items")
    
    # Get all items
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT i.id, i.name, c.name as category
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.disabled = false
            ORDER BY c.name, i.name
        """)
        items = [dict(zip([desc[0] for desc in cursor.description], row))
                for row in cursor.fetchall()]
    
    if not items:
        st.info("No items available")
        return
    
    # Source item selection
    st.write("Source Item")
    default_source = None
    if source_name := st.session_state.get('source_item_name'):
        # Find item ID by name
        for item in items:
            if item['name'].lower() == source_name.lower():
                default_source = item['id']
                break
    
    source_id = st.selectbox(
        "Copy options from",
        options=[i['id'] for i in items],
        format_func=lambda x: next(i['name'] + f" (Category: {i['category']})" 
                                 for i in items if i['id'] == x),
        key="source_item",
        index=([i['id'] for i in items].index(default_source) if default_source else 0)
    )
    
    # Get source item options
    source_options = get_item_options(connection, source_id)
    if not source_options:
        st.warning("Selected item has no options")
        return
    
    # Option selection
    st.write("Select Options to Copy")
    selected_options = []
    for option in source_options:
        if st.checkbox(f"{option['name']} (Min: {option['min']}, Max: {option['max']})",
                      key=f"option_{option['id']}"):
            selected_options.append(option['id'])
    
    # Target item selection
    st.write("Target Item")
    default_target = None
    if target_name := st.session_state.get('target_item_name'):
        # Find item ID by name
        for item in items:
            if item['name'].lower() == target_name.lower():
                default_target = item['id']
                break
    
    target_id = st.selectbox(
        "Copy options to",
        options=[i['id'] for i in items if i['id'] != source_id],
        format_func=lambda x: next(i['name'] + f" (Category: {i['category']})" 
                                 for i in items if i['id'] == x),
        key="target_item",
        index=([i['id'] for i in items if i['id'] != source_id].index(default_target) if default_target else 0)
    )
    
    # Copy button
    if selected_options and st.button("Copy Selected Options"):
        result = copy_options(connection, source_id, target_id, selected_options)
        if "Error" in result:
            st.error(result)
        else:
            st.success(result)
