"""
Database schema information for SQL generation.
"""

# Define the restaurant database schema for SQL generation
RESTAURANT_SCHEMA = """
DATABASE SCHEMA:

Table: orders
- id (integer, primary key)
- order_number (varchar, unique)
- status (integer): 7=completed, 6=cancelled, 3-5=in progress
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- total_amount (numeric)
- tax_amount (numeric)
- tip_amount (numeric)
- location_id (integer, foreign key to locations.id)
- customer_id (integer, foreign key to users.id) - The customer who placed the order
- user_id (integer, foreign key to users.id) - Alternative name for customer_id
- payment_method (varchar)
- delivery_address (varchar, nullable)
- is_delivery (boolean)
- notes (text, nullable)
- source (varchar)

Table: users
- id (integer, primary key)
- first_name (varchar)
- last_name (varchar)
- email (varchar, unique)
- phone (varchar)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- location_id (integer) - The primary location for this user
- status (integer)

Table: order_items
- id (integer, primary key)
- order_id (integer, foreign key to orders.id)
- menu_item_id (integer, foreign key to menu_items.id)
- quantity (integer)
- price (numeric)
- notes (text, nullable)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)

Table: menu_items
- id (integer, primary key)
- name (varchar)
- description (text)
- price (numeric)
- category_id (integer, foreign key to categories.id)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- is_active (boolean)
- location_id (integer) - The location this menu item belongs to
- image_url (varchar, nullable)

Table: categories
- id (integer, primary key)
- name (varchar)
- description (text, nullable)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- location_id (integer) - The location this category belongs to
- display_order (integer)

Table: locations
- id (integer, primary key)
- name (varchar)
- address (varchar)
- city (varchar)
- state (varchar)
- zip (varchar)
- phone (varchar)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- timezone (varchar)
- status (integer)

Table: order_ratings
- id (integer, primary key)
- order_id (integer, foreign key to orders.id)
- rating (integer) - 1 to 5 stars
- comment (text, nullable)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
"""

# Define schema hints for the SQL generator
SCHEMA_HINTS = """
IMPORTANT SCHEMA HINTS:
1. To get customer names, join the orders table with users: orders o JOIN users u ON o.customer_id = u.id
2. Do NOT reference the 'customers' table - it doesn't exist. Customer data is in the 'users' table.
3. The order status values are integers: 7=completed, 6=cancelled, 3-5=in progress
4. All timestamps are stored with timezone information. For date comparisons, use: (updated_at - INTERVAL '7 hours')::date
5. For date filtering, use the pattern: WHERE (updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025', 'MM/DD/YYYY')
6. Always include location filtering: WHERE location_id = 62
7. For follow-up queries about orders, make sure to maintain all filters from the previous query.
8. When asked about "who placed those orders" use: SELECT u.first_name || ' ' || u.last_name AS customer_name FROM orders o JOIN users u ON o.customer_id = u.id
"""

def get_database_schema():
    """Return the database schema for SQL generation."""
    return RESTAURANT_SCHEMA

def get_schema_hints():
    """Return the schema hints for SQL generation."""
    return SCHEMA_HINTS 