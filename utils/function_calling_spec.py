from utils.database_functions import database_schema_string

# Specify function descriptions for OpenAI function calling 
functions = [
    {
        "name": "categorize_request",
        "description": "Analyze the user's message and determine the request type. Accurately categorize queries into appropriate types based on their intent and content.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_type": {
                    "type": "string",
                    "enum": [
                        "order_history", 
                        "update_price", 
                        "disable_item", 
                        "enable_item", 
                        "query_menu", 
                        "query_performance", 
                        "query_ratings", 
                        "unknown"
                    ],
                    "description": "The type of request being made. Use 'order_history' for any queries related to past orders, order counts, order status, revenue, or sales data. Use 'query_menu' for inquiries about the menu structure or items. Use 'query_performance' for metrics about business performance. Use 'query_ratings' for questions about customer ratings and feedback."
                },
                "item_name": {
                    "type": "string",
                    "description": "Name of the item referenced, if any"
                },
                "new_price": {
                    "type": "number",
                    "description": "New price if request_type=update_price. Otherwise ignore."
                },
                "time_period": {
                    "type": "string",
                    "description": "Time period for queries (e.g., 'today', 'yesterday', 'this week', 'last month', 'specific date'). Extract this from the query when available."
                },
                "analysis_type": {
                    "type": "string",
                    "description": "For order_history queries, specify what kind of analysis is being requested (e.g., 'count', 'revenue', 'details', 'trend')"
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
                    "description": "SQL query for item updates. Price must be non-negative, and item_name must match the user's intent."
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
    },
    {
        "name": "query_orders",
        "description": "Query order information from the database including counts and revenue.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_metric": {
                    "type": "string",
                    "enum": [
                        "completed_orders", 
                        "daily_sales", 
                        "order_details", 
                        "revenue_metrics", 
                        "customer_metrics"
                    ],
                    "description": "The specific order metric to query"
                },
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "Specific date to query orders for, in 'YYYY-MM-DD' format. Required for 'completed_orders' and 'order_details' metrics."
                },
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date in YYYY-MM-DD format. Required for 'daily_sales' and 'revenue_metrics' metrics."
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "description": "End date in YYYY-MM-DD format. Required for 'daily_sales' and 'revenue_metrics' metrics."
                }
            },
            "required": ["order_metric"]
        }
    }
]
