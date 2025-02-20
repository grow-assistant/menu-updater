from utils.database_functions import database_schema_string
from utils.menu_operations import DEFAULT_COMMON_OPERATIONS

# Specify function descriptions for OpenAI function calling 
functions = [
    {
        "name": "manage_common_operations",
        "description": "Add or update common operations for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "ID of the location"
                },
                "operation_type": {
                    "type": "string",
                    "enum": ["queries", "updates"],
                    "description": "Type of operation to manage"
                },
                "operation": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "query_template": {"type": "string"}
                    },
                    "required": ["name", "description", "query_template"]
                }
            },
            "required": ["location_id", "operation_type", "operation"]
        }
    },
    {
        "name": "get_common_operations",
        "description": "Get the list of common menu operations for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "ID of the location to get operations for"
                }
            },
            "required": ["location_id"]
        }
    },
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
        "description": "Enable or disable menu items",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """SQL query to update item.disabled flag. Rules:
                        - Use UPDATE items SET disabled = true/false
                        - Must include WHERE clause for safety
                        
                        Example: UPDATE items SET disabled = true WHERE id = 123
                        Write SQL only, no JSON. No line breaks."""
                }
            },
            "required": ["query"]
        }
    }
]
