import sys
from pathlib import Path
import json
from collections import defaultdict

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

import psycopg2
import streamlit as st
from utils.config import db_credentials

def format_price(price):
    """Format price with 2 decimal places and dollar sign"""
    return f"${price:.2f}" if price else "N/A"

def display_menu_structure(location_id):
    """Display complete menu structure in a collapsible tree format"""
    try:
        conn = psycopg2.connect(**db_credentials)
        
        # Fetch all categories
        with conn.cursor() as cursor:
            categories_query = """
            SELECT c.id, c.name, c.description
            FROM categories c
            JOIN menus m ON c.menu_id = m.id
            WHERE m.location_id = %s
            ORDER BY c.name;
            """
            cursor.execute(categories_query, (location_id,))
            categories = cursor.fetchall()

        # Fetch all items with their options
        with conn.cursor() as cursor:
            items_query = """
            SELECT 
                i.id, 
                i.name, 
                i.description,
                i.price, 
                c.id as category_id,
                o.id as option_id,
                o.name as option_name,
                o.description as option_description,
                o.min as min_selections,
                o.max as max_selections
            FROM items i
            JOIN categories c ON i.category_id = c.id
            JOIN menus m ON c.menu_id = m.id
            LEFT JOIN options o ON o.item_id = i.id
            WHERE m.location_id = %s
            ORDER BY i.name, o.name;
            """
            cursor.execute(items_query, (location_id,))
            items = cursor.fetchall()

        # Fetch all option items
        with conn.cursor() as cursor:
            option_items_query = """
            SELECT 
                oi.id,
                oi.name,
                oi.description,
                oi.price,
                o.id as option_id
            FROM option_items oi
            JOIN options o ON oi.option_id = o.id
            JOIN items i ON o.item_id = i.id
            JOIN categories c ON i.category_id = c.id
            JOIN menus m ON c.menu_id = m.id
            WHERE m.location_id = %s
            ORDER BY oi.name;
            """
            cursor.execute(option_items_query, (location_id,))
            option_items = cursor.fetchall()

        conn.close()

        # Organize the data hierarchically
        items_by_category = defaultdict(list)
        options_by_item = defaultdict(list)
        option_items_by_option = defaultdict(list)

        # Organize option items by option
        for oi in option_items:
            option_items_by_option[oi[4]].append({
                'id': oi[0],
                'name': oi[1],
                'description': oi[2],
                'price': oi[3]
            })

        # Organize options by item
        for item in items:
            if item[5]:  # if there's an option
                options_by_item[item[0]].append({
                    'id': item[5],
                    'name': item[6],
                    'description': item[7],
                    'min_selections': item[8],
                    'max_selections': item[9],
                    'option_items': option_items_by_option.get(item[5], [])
                })

        # Organize items by category
        seen_items = set()
        for item in items:
            if item[0] not in seen_items:
                items_by_category[item[4]].append({
                    'id': item[0],
                    'name': item[1],
                    'description': item[2],
                    'price': item[3],
                    'options': options_by_item.get(item[0], [])
                })
                seen_items.add(item[0])

        # Display the menu structure
        st.title(f"Complete Menu Structure for Location {location_id}")
        
        # Display summary counts
        st.markdown("### Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"📋 Categories: {len(categories)}")
        with col2:
            st.info(f"🍽️ Items: {len(seen_items)}")
        with col3:
            st.info(f"⚙️ Options: {len(set(oi[4] for oi in option_items))}")
        with col4:
            st.info(f"🔸 Option Items: {len(option_items)}")

        # Display the complete menu structure
        st.markdown("### Menu Categories")
        for cat_id, cat_name, cat_desc in categories:
            with st.expander(f"📑 {cat_name}"):
                if cat_desc:
                    st.markdown(f"*{cat_desc}*")
                
                if cat_id in items_by_category:
                    for item in items_by_category[cat_id]:
                        # Display item in a container for better visual grouping
                        with st.container():
                            # Item header with price
                            st.markdown(f"""
                            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
                                <h3 style='margin: 0; color: #0e1117;'>🍽️ {item['name']} - {format_price(item['price'])}</h3>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Item description
                            if item['description']:
                                st.markdown(f"<div style='margin-left: 20px; color: #666;'>{item['description']}</div>", 
                                          unsafe_allow_html=True)
                            
                            # Display options
                            if item['options']:
                                for option in item['options']:
                                    st.markdown(f"""
                                    <div style='margin-left: 20px; margin-top: 10px;'>
                                        <h4 style='color: #444; margin-bottom: 5px;'>
                                            ⚙️ {option['name']} 
                                            <span style='color: #666; font-size: 0.9em;'>
                                                (Select {option['min_selections']}-{option['max_selections']})
                                            </span>
                                        </h4>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    if option['description']:
                                        st.markdown(f"<div style='margin-left: 40px; color: #666;'>{option['description']}</div>", 
                                                  unsafe_allow_html=True)
                                    
                                    if option['option_items']:
                                        # Create a clean table of option items
                                        option_items_data = [{
                                            "Name": oi['name'],
                                            "Description": oi['description'] or "",
                                            "Additional Price": format_price(oi['price']) if oi['price'] else "Included"
                                        } for oi in option['option_items']]
                                        
                                        # Display option items in a styled dataframe
                                        st.markdown("<div style='margin-left: 40px;'>", unsafe_allow_html=True)
                                        st.dataframe(
                                            option_items_data,
                                            column_config={
                                                "Name": st.column_config.TextColumn(
                                                    "Name",
                                                    width="medium",
                                                    help="Option item name"
                                                ),
                                                "Description": st.column_config.TextColumn(
                                                    "Description",
                                                    width="large",
                                                    help="Option item description"
                                                ),
                                                "Additional Price": st.column_config.TextColumn(
                                                    "Price",
                                                    width="small",
                                                    help="Additional cost"
                                                )
                                            },
                                            hide_index=True,
                                            use_container_width=True
                                        )
                                        st.markdown("</div>", unsafe_allow_html=True)
                                    else:
                                        st.markdown(
                                            "<div style='margin-left: 40px; color: #666;'>No option items available</div>", 
                                            unsafe_allow_html=True
                                        )
                            else:
                                st.markdown(
                                    "<div style='margin-left: 20px; color: #666;'>No options available</div>", 
                                    unsafe_allow_html=True
                                )
                            
                            # Add separator between items
                            st.markdown("<hr style='margin: 20px 0; opacity: 0.3;'>", unsafe_allow_html=True)
                else:
                    st.write("No items in this category")

    except Exception as e:
        st.error(f"Error fetching menu structure: {e}")

def main():
    """Main function to run the Streamlit app"""
    st.set_page_config(
        page_title="Complete Menu Structure Viewer",
        page_icon="🍽️",
        layout="wide"
    )

    # Add custom CSS
    st.markdown("""
        <style>
        .stExpander {
            border: 1px solid #e6e6e6;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        .stDataFrame {
            background-color: white;
            border-radius: 5px;
            margin: 10px 0;
        }
        div[data-testid="stExpander"] div[data-testid="stExpanderContent"] {
            background-color: white;
        }
        </style>
    """, unsafe_allow_html=True)

    location_id = 62
    display_menu_structure(location_id)

if __name__ == "__main__":
    main() 