from utils.database_functions import database_schema_string

# Specify function descriptions for OpenAI function calling 
functions = [
    {
        "name": "categorize_request",
        "description": "Analyze the user's message and determine the request type, item name, new price, etc. If no known request type applies, set request_type='unknown'.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_type": {
                    "type": "string",
                    "enum": ["update_price", "disable_item", "enable_item", "query_menu", "unknown"],
                    "description": "The type of request being made"
                },
                "item_name": {
                    "type": "string",
                    "description": "Name of the item referenced, if any"
                },
                "new_price": {
                    "type": "number",
                    "description": "New price if request_type=update_price. Otherwise ignore."
                }
            },
            "required": ["request_type"]
        }
    },
    {
        "name": "update_menu_item",
        "description": "Updates menu item properties like price or description.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query for item updates. Price must be non-negative, item_name must match the user's intent."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "toggle_menu_item",
        "description": "Enable or disable a menu item. Sets disabled=true or disabled=false on an item.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to update item.disabled. Example: UPDATE items SET disabled = true WHERE name ILIKE '%French Fries%'"
                }
            },
            "required": ["query"]
        }
    }
]
