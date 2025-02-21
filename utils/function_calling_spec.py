from utils.database_functions import database_schema_string

# Specify function descriptions for OpenAI function calling 
functions = [
    {
        "name": "query_menu_items",
        "description": "Query menu items and their details",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """SQL query to fetch menu items. Available tables and relationships:
                        - locations (id, name, description, disabled)
                        - menus (id, name, description, location_id, disabled)
                        - categories (id, name, description, menu_id, disabled, start_time, end_time)
                        - items (id, name, description, price, category_id, disabled)
                        - options (id, name, description, min, max, item_id, disabled)
                        - option_items (id, name, description, price, option_id, disabled)
                        
                        Join through proper hierarchy: locations -> menus -> categories -> items.
                        Write SQL only, no JSON. No line breaks."""
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "update_menu_item",
        "description": "Update menu item properties like price or description",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """SQL query to update menu items. Validation rules:
                        - Prices must be non-negative
                        - Items should be disabled rather than deleted
                        - Time-based menu categories must have valid time ranges (0-2359)
                        
                        Example: UPDATE items SET price = 12.99 WHERE id = 123 AND price >= 0
                        Write SQL only, no JSON. No line breaks."""
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "toggle_menu_item",
        "description": "Enable or disable menu items and their options",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """SQL query to update item.disabled flag. Rules:
                        - Use UPDATE items SET disabled = true/false
                        - Must include WHERE clause for safety
                        - Can enable/disable both items and their options
                        
                        Examples: 
                        - UPDATE items SET disabled = true WHERE id = 123
                        - UPDATE items SET disabled = false WHERE name LIKE '%French Fries%'
                        Write SQL only, no JSON. No line breaks."""
                }
            },
            "required": ["query"]
        }
    }
]
