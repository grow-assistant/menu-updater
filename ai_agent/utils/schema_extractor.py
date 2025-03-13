"""
Schema extraction utilities for the test runner.
"""

import os
import re
from pathlib import Path

def extract_schema_info(schema_path=None):
    """
    Extract schema information from the database schema diagram.
    
    Args:
        schema_path: Path to the schema diagram file (optional)
        
    Returns:
        dict: Schema information dictionary
    """
    if schema_path is None:
        # Use default schema path if not specified
        project_root = Path(__file__).parents[2]  # Go up 2 levels from utils/
        schema_path = os.path.join(project_root, "schema_diagram.dot")
    
    if not os.path.exists(schema_path):
        print(f"Warning: Schema diagram not found at {schema_path}")
        return {}
    
    try:
        # Parse the DOT file to extract table and column information
        tables = {}
        relationships = []
        
        with open(schema_path, "r") as f:
            dot_content = f.read()
        
        # Extract table definitions
        table_pattern = r'"([^"]+)"\s+\[label="\{([^}]+)\}"\];'
        table_matches = re.findall(table_pattern, dot_content)
        
        for table_name, table_content in table_matches:
            # Parse columns
            columns = []
            for column_def in table_content.split("\\l"):
                column_def = column_def.strip()
                if not column_def:
                    continue
                
                # Extract column name and type
                parts = column_def.split(":")
                if len(parts) >= 2:
                    col_name = parts[0].strip()
                    col_type = parts[1].strip()
                    
                    # Check for primary key
                    is_pk = "(PK)" in col_type
                    # Check for foreign key
                    is_fk = "(FK)" in col_type
                    
                    # Clean up type
                    col_type = col_type.replace("(PK)", "").replace("(FK)", "").strip()
                    
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "is_primary_key": is_pk,
                        "is_foreign_key": is_fk
                    })
            
            tables[table_name] = {
                "columns": columns
            }
        
        # Extract relationships
        rel_pattern = r'"([^"]+)"\s+->\s+"([^"]+)"\s+\[label="([^"]+)"\];'
        rel_matches = re.findall(rel_pattern, dot_content)
        
        for source, target, label in rel_matches:
            # Parse the relationship (e.g., "column_a -> column_b")
            source_col, target_col = label.split(" -> ")
            
            relationships.append({
                "source_table": source,
                "target_table": target,
                "source_column": source_col,
                "target_column": target_col
            })
        
        # Combine into schema info
        schema_info = {
            "tables": tables,
            "relationships": relationships
        }
        
        # Add specific information about key tables for test scenarios
        schema_info["key_tables"] = {
            "locations": "Contains restaurant location information",
            "menus": "Menus for each location",
            "categories": "Menu categories (e.g. appetizers, mains)",
            "items": "Food and drink items",
            "orders": "Customer orders",
            "order_items": "Items in customer orders"
        }
        
        # Add sample queries for common operations
        schema_info["sample_queries"] = {
            "menu_items": """
                SELECT i.id, i.name, i.description, i.price
                FROM items i
                JOIN categories c ON i.category_id = c.id
                JOIN menus m ON c.menu_id = m.id
                WHERE m.location_id = :location_id
                AND i.disabled = FALSE
                ORDER BY c.seq_num, i.seq_num
            """,
            "active_menus": """
                SELECT m.id, m.name, m.description
                FROM menus m
                WHERE m.location_id = :location_id
                AND m.disabled = FALSE
            """,
            "order_history": """
                SELECT o.id, o.created_at, o.total, o.status
                FROM orders o
                WHERE o.customer_id = :user_id
                ORDER BY o.created_at DESC
                LIMIT 10
            """
        }
        
        return schema_info
        
    except Exception as e:
        print(f"Error extracting schema info: {e}")
        return {} 