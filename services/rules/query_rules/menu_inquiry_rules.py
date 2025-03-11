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
        "description": "Top-level menu containers for restaurant locations",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "location_id": "INTEGER - Foreign key to locations table",
            "name": "TEXT - Name of the menu",
            "description": "TEXT - Description of the menu",
            "disabled": "BOOLEAN - Whether the menu is currently available",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the menu was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the menu was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the menu was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (location_id) REFERENCES locations(id)"],
        "primary_key": "id",
        "indexes": ["location_id", "disabled"],
        "referenced_by": {
            "categories": "menu_id"
        }
    },
    "categories": {
        "description": "Menu categories (sections) within a menu",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "menu_id": "INTEGER - Foreign key to menus table",
            "name": "TEXT - Name of the category",
            "description": "TEXT - Description of the category",
            "disabled": "BOOLEAN - Whether the category is disabled",
            "start_time": "SMALLINT - Time when category becomes available",
            "end_time": "SMALLINT - Time when category becomes unavailable",
            "seq_num": "INTEGER - Display sequence number (default 0)",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the category was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the category was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the category was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (menu_id) REFERENCES menus(id)"],
        "primary_key": "id",
        "indexes": ["menu_id", "disabled", "seq_num"],
        "referenced_by": {
            "items": "category_id"
        }
    },
    "items": {
        "description": "Menu items within a category",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "category_id": "INTEGER - Foreign key to categories table",
            "name": "TEXT - Name of the menu item",
            "description": "TEXT - Description of the menu item",
            "price": "NUMERIC - Price of the item",
            "disabled": "BOOLEAN - Whether the item is currently available",
            "seq_num": "INTEGER - Display sequence number (default 0)",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the item was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the item was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the item was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (category_id) REFERENCES categories(id)"],
        "primary_key": "id",
        "indexes": ["category_id", "disabled", "seq_num"],
        "referenced_by": {
            "options": "item_id",
            "order_items": "item_id"
        }
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
            "disabled": "BOOLEAN - Whether the option group is disabled",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the option was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the option was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the option was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (item_id) REFERENCES items(id)"],
        "primary_key": "id",
        "indexes": ["item_id", "disabled"],
        "referenced_by": {
            "option_items": "option_id"
        }
    },
    "option_items": {
        "description": "Individual options within an option group",
        "columns": {
            "id": "INTEGER PRIMARY KEY - Unique identifier",
            "option_id": "INTEGER - Foreign key to options table",
            "name": "TEXT - Name of the option item",
            "description": "TEXT - Description of the option item",
            "price": "NUMERIC - Additional price for this option",
            "disabled": "BOOLEAN - Whether the option item is disabled",
            "created_at": "TIMESTAMP WITH TIME ZONE - When the option item was created",
            "updated_at": "TIMESTAMP WITH TIME ZONE - When the option item was last updated",
            "deleted_at": "TIMESTAMP WITH TIME ZONE - When the option item was deleted (if applicable)"
        },
        "relationships": ["FOREIGN KEY (option_id) REFERENCES options(id)"],
        "primary_key": "id",
        "indexes": ["option_id", "disabled"],
        "referenced_by": {
            "order_option_items": "option_item_id"
        }
    }
}

# Menu inquiry rules
MENU_INQUIRY_RULES = {
    "general": {
        "table_structure": "Menu data is organized in a hierarchy: menus → categories → items → options → option_items",
        "primary_joins": "To query menu items: 1) JOIN items ON items.category_id = categories.id 2) JOIN categories ON categories.menu_id = menus.id 3) JOIN menus ON menus.location_id = [LOCATION_ID]",
        "location_filter": "ALWAYS filter by menus.location_id = [LOCATION_ID] in the WHERE clause (never directly on items table)",
        "disabled_items": "To exclude disabled items, add 'AND items.disabled = FALSE' to the WHERE clause",
        "price_formatting": "Format prices with dollar sign and two decimal places: '$' || to_char(items.price, 'FM999990.00')",
        "sorting": "For menu listings, sort by 1) category sequence (categories.seq_num) 2) item sequence (items.seq_num), or 3) alphabetically (items.name)",
        "options": "To include item options: LEFT JOIN options ON options.item_id = items.id",
        "option_items": "For option choices: LEFT JOIN option_items ON option_items.option_id = options.id"
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
