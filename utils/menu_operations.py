"""Common menu operations and queries stored per location."""

DEFAULT_COMMON_OPERATIONS = {
    "queries": [
        {
            "name": "View all active menu items",
            "description": "Show all enabled menu items with prices",
            "query_template": """
                SELECT i.name, i.description, i.price, c.name as category
                FROM items i
                JOIN categories c ON i.category_id = c.id
                WHERE i.disabled = false
                AND c.disabled = false
                AND c.menu_id = {menu_id}
                ORDER BY c.seq_num, i.seq_num
            """
        },
        {
            "name": "Find items by name",
            "description": "Search for menu items by name",
            "query_template": """
                SELECT i.name, i.description, i.price, c.name as category
                FROM items i
                JOIN categories c ON i.category_id = c.id
                WHERE i.name ILIKE '%{search_term}%'
                AND c.menu_id = {menu_id}
                ORDER BY c.seq_num, i.seq_num
            """
        },
        {
            "name": "View items by category",
            "description": "Show all items in a specific category",
            "query_template": """
                SELECT i.name, i.description, i.price
                FROM items i
                WHERE i.category_id = {category_id}
                AND i.disabled = false
                ORDER BY i.seq_num
            """
        },
        {
            "name": "View time-based menu items",
            "description": "Show items available during specific hours",
            "query_template": """
                SELECT i.name, i.description, i.price, 
                       c.name as category,
                       c.start_time, c.end_time
                FROM items i
                JOIN categories c ON i.category_id = c.id
                WHERE c.start_time IS NOT NULL
                AND c.menu_id = {menu_id}
                ORDER BY c.start_time
            """
        }
    ],
    "updates": [
        {
            "name": "Update item price",
            "description": "Change the price of a menu item",
            "query_template": """
                UPDATE items
                SET price = {new_price}
                WHERE id = {item_id}
                AND price >= 0
                RETURNING name, price as new_price
            """
        },
        {
            "name": "Disable menu item",
            "description": "Temporarily remove item from menu",
            "query_template": """
                UPDATE items
                SET disabled = true
                WHERE id = {item_id}
                RETURNING name
            """
        },
        {
            "name": "Enable menu item",
            "description": "Add item back to menu",
            "query_template": """
                UPDATE items
                SET disabled = false
                WHERE id = {item_id}
                RETURNING name
            """
        },
        {
            "name": "Update item description",
            "description": "Change the description of a menu item",
            "query_template": """
                UPDATE items
                SET description = '{new_description}'
                WHERE id = {item_id}
                RETURNING name, description as new_description
            """
        }
    ]
}

def get_location_operations(location_settings):
    """Get common operations for a location, falling back to defaults if not customized."""
    if not location_settings or 'common_operations' not in location_settings:
        return DEFAULT_COMMON_OPERATIONS
    return location_settings['common_operations']

def add_operation_to_location(location_settings, operation_type, operation):
    """Add a new common operation to a location's settings."""
    if not location_settings:
        location_settings = {}
    if 'common_operations' not in location_settings:
        location_settings['common_operations'] = DEFAULT_COMMON_OPERATIONS.copy()
    
    if operation_type not in ['queries', 'updates']:
        raise ValueError("Operation type must be 'queries' or 'updates'")
    
    required_fields = ['name', 'description', 'query_template']
    if not all(field in operation for field in required_fields):
        raise ValueError(f"Operation must include: {', '.join(required_fields)}")
    
    location_settings['common_operations'][operation_type].append(operation)
    return location_settings
