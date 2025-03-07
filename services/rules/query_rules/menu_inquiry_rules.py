"""
Rules specific to querying menu items.
"""

from typing import Dict, Any
from services.rules.base_rules import get_base_rules
from services.rules.query_rules import (
    replace_placeholders,
    load_all_sql_files_from_directory,
)
from services.rules.business_rules import DEFAULT_LOCATION_ID, TIMEZONE_OFFSET

# Schema information for menu inquiry queries
MENU_INQUIRY_SCHEMA = {
    "menus": {
        "description": "Top-level menus that contain categories",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "location_id": "INTEGER - Foreign key to locations table",
            "name": "TEXT - Name of the menu",
            "description": "TEXT - Description of the menu",
            "disabled": "BOOLEAN - Whether the menu is disabled"
        },
        "relationships": ["FOREIGN KEY (location_id) REFERENCES locations(id)"],
    },
    "categories": {
        "description": "Menu categories that contain items",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "menu_id": "INTEGER - Foreign key to menus table",
            "name": "TEXT - Name of the category",
            "description": "TEXT - Description of the category",
            "disabled": "BOOLEAN - Whether the category is disabled",
            "start_time": "TIME - Time when category becomes available",
            "end_time": "TIME - Time when category becomes unavailable",
            "seq_num": "INTEGER - Display sequence number"
        },
        "relationships": ["FOREIGN KEY (menu_id) REFERENCES menus(id)"],
    },
    "items": {
        "description": "Menu items that belong to categories",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "category_id": "INTEGER - Foreign key to categories table",
            "name": "TEXT - Name of the item",
            "description": "TEXT - Description of the item",
            "price": "NUMERIC - Price of the item",
            "disabled": "BOOLEAN - Whether the item is disabled",
            "seq_num": "INTEGER - Display sequence number"
        },
        "relationships": ["FOREIGN KEY (category_id) REFERENCES categories(id)"],
    },
    "options": {
        "description": "Option groups for menu items (e.g., 'Size', 'Toppings')",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "item_id": "INTEGER - Foreign key to items table",
            "name": "TEXT - Name of the option group",
            "description": "TEXT - Description of the option group",
            "min": "INTEGER - Minimum number of selections required",
            "max": "INTEGER - Maximum number of selections allowed",
            "disabled": "BOOLEAN - Whether the option is disabled"
        },
        "relationships": ["FOREIGN KEY (item_id) REFERENCES items(id)"],
    },
    "option_items": {
        "description": "Individual choices within an option group",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "option_id": "INTEGER - Foreign key to options table",
            "name": "TEXT - Name of the option item",
            "price": "NUMERIC - Additional price for this option",
            "seq_num": "INTEGER - Display sequence number",
        },
        "relationships": ["FOREIGN KEY (option_id) REFERENCES options(id)"],
    },
}

# Menu inquiry rules
MENU_INQUIRY_RULES = {
    "general": {
        "table_structure": "Menu data is organized in a hierarchy: menus → categories → items → options → option_items",
        "primary_joins": "To query menu items: 1) JOIN items i ON i.category_id = c.id 2) JOIN categories c ON c.menu_id = m.id 3) JOIN menus m ON m.location_id = [LOCATION_ID]",
        "location_filter": "ALWAYS filter by m.location_id = [LOCATION_ID] in the WHERE clause (never directly on items table)",
        "disabled_items": "To exclude disabled items, add 'AND i.disabled = FALSE' to the WHERE clause",
        "price_formatting": "Format prices with dollar sign and two decimal places: '$' || to_char(i.price, 'FM999990.00')",
        "sorting": "For menu listings, sort by 1) category sequence (c.seq_num) 2) item sequence (i.seq_num), or 3) alphabetically (i.name)",
        "options": "To include item options: LEFT JOIN options o ON i.id = o.item_id",
        "option_items": "For option choices: LEFT JOIN option_items oi ON o.id = oi.option_id"
    }
}

def get_rules(rules_service=None) -> Dict[str, Any]:
    """
    Get rules for menu inquiry queries.
    
    Args:
        rules_service: Optional reference to the RulesService instance
    
    Returns:
        Dictionary containing rules, patterns, and examples for menu inquiry queries
    """
    base_rules = get_base_rules()
    
    # Load SQL patterns from file system
    sql_patterns = load_all_sql_files_from_directory("menu_inquiry")
    
    # Replace placeholders in patterns
    for pattern_name, pattern_text in sql_patterns.items():
        if rules_service:
            # Use the service's replace_placeholders method that takes a dictionary
            temp_dict = {pattern_name: pattern_text}
            result_dict = rules_service.replace_placeholders(temp_dict, {
                "DEFAULT_LOCATION_ID": str(DEFAULT_LOCATION_ID),
                "TIMEZONE_OFFSET": str(TIMEZONE_OFFSET),
            })
            sql_patterns[pattern_name] = result_dict[pattern_name]
        else:
            # Use the local replace_placeholders function that takes a string
            sql_patterns[pattern_name] = replace_placeholders(
                pattern_text,
                {
                    "DEFAULT_LOCATION_ID": str(DEFAULT_LOCATION_ID),
                    "TIMEZONE_OFFSET": str(TIMEZONE_OFFSET),
                }
            )
    
    return {
        "name": "menu_inquiry",
        "description": "Rules for menu inquiry queries",
        "schema": MENU_INQUIRY_SCHEMA,
        "query_rules": MENU_INQUIRY_RULES,
        "base_rules": base_rules,
        "query_patterns": sql_patterns,
    }
