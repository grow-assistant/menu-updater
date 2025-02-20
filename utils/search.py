"""Search functionality for menu items"""
from typing import Dict, List, Any
import streamlit as st

def render_search_filters() -> Dict[str, Any]:
    """Render search filters"""
    st.sidebar.subheader("🔍 Search Filters")
    
    filters = {}
    
    # Text search
    filters['query'] = st.sidebar.text_input(
        "Search Items",
        help="Search by name or description"
    )
    
    # Price range
    price_col1, price_col2 = st.sidebar.columns(2)
    with price_col1:
        filters['price_min'] = st.number_input(
            "Min Price",
            min_value=0.0,
            value=0.0,
            step=0.01
        )
    with price_col2:
        filters['price_max'] = st.number_input(
            "Max Price",
            min_value=filters['price_min'],
            value=100.0,
            step=0.01
        )
    
    # Category filter
    filters['category'] = st.sidebar.multiselect(
        "Categories",
        options=[],  # Will be populated from database
        help="Filter by category"
    )
    
    # Time range filter
    time_col1, time_col2 = st.sidebar.columns(2)
    with time_col1:
        filters['time_start'] = st.number_input(
            "Start Time",
            min_value=0,
            max_value=2359,
            step=100,
            help="24-hour format (0000-2359)"
        )
    with time_col2:
        filters['time_end'] = st.number_input(
            "End Time",
            min_value=filters['time_start'],
            max_value=2359,
            step=100,
            help="24-hour format (0000-2359)"
        )
    
    # Status filter
    filters['status'] = st.sidebar.selectbox(
        "Status",
        options=["All", "Enabled", "Disabled"],
        help="Filter by item status"
    )
    
    return filters

def search_menu_items(connection, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search menu items with filters"""
    try:
        query = """
            SELECT 
                i.id,
                i.name,
                i.description,
                i.price,
                i.disabled,
                c.name as category_name,
                c.start_time,
                c.end_time,
                COALESCE(a.orders, 0) as order_count
            FROM items i
            JOIN categories c ON i.category_id = c.id
            LEFT JOIN menu_item_analytics a ON i.id = a.item_id
            WHERE 1=1
        """
        params = []
        
        # Text search
        if filters.get('query'):
            query += " AND (i.name ILIKE %s OR i.description ILIKE %s)"
            search_term = f"%{filters['query']}%"
            params.extend([search_term, search_term])
        
        # Price range
        if filters.get('price_min') is not None:
            query += " AND i.price >= %s"
            params.append(filters['price_min'])
        if filters.get('price_max') is not None:
            query += " AND i.price <= %s"
            params.append(filters['price_max'])
        
        # Category filter
        if filters.get('category'):
            query += " AND c.name = ANY(%s)"
            params.append(filters['category'])
        
        # Time range filter
        if filters.get('time_start') is not None:
            query += " AND c.start_time >= %s"
            params.append(filters['time_start'])
        if filters.get('time_end') is not None:
            query += " AND c.end_time <= %s"
            params.append(filters['time_end'])
        
        # Status filter
        if filters.get('status') == "Enabled":
            query += " AND i.disabled = false"
        elif filters.get('status') == "Disabled":
            query += " AND i.disabled = true"
        
        # Add sorting
        sort_by = filters.get('sort_by', 'name')
        sort_order = "DESC" if filters.get('sort_desc', False) else "ASC"
        query += f" ORDER BY {sort_by} {sort_order}"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Search failed: {str(e)}")
        return []

def render_search_results(items: List[Dict[str, Any]]):
    """Render search results with sorting options"""
    if not items:
        st.info("No items found matching your criteria")
        return
    
    # Sorting options
    col1, col2 = st.columns([3, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            options=["name", "price", "order_count"],
            format_func=lambda x: {
                "name": "Name",
                "price": "Price",
                "order_count": "Popularity"
            }[x]
        )
    with col2:
        sort_desc = st.checkbox("Sort Descending")
    
    # Display results in a table
    st.dataframe(
        items,
        column_config={
            "name": "Name",
            "price": st.column_config.NumberColumn(
                "Price",
                format="$%.2f"
            ),
            "category_name": "Category",
            "order_count": "Orders",
            "disabled": "Disabled"
        },
        hide_index=True
    )
    
    # Show relationship diagram for filtered items
    if len(items) > 1:
        st.subheader("Item Relationships")
        from utils.visualization import render_category_relationships
        with st.spinner("Loading relationships..."):
            fig = render_category_relationships({
                item['category_name']: [{'category': i['category_name'], 'frequency': i['order_count']}
                                      for i in items if i['category_name'] != item['category_name']]
                for item in items
            })
            if fig:
                st.plotly_chart(fig, use_container_width=True)
