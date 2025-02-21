import psycopg2
import re
import json
import streamlit as st
from utils.config import db_credentials
from utils.menu_operations import add_operation_to_history
from utils.query_templates import QUERY_TEMPLATES

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**db_credentials)
        conn.set_session(autocommit=True)
        return conn
    except Exception as e:
        raise ConnectionError(f"Unable to connect to the database due to: {e}")

def get_database_info(connection, schema_names):
    """ Fetches information about the schemas, tables and columns in the database """
    table_dicts = []
    for schema in schema_names:
        for table_name in get_table_names(connection, schema):
            column_names = get_column_names(connection, table_name, schema)
            table_dicts.append({"table_name": table_name, "column_names": column_names, "schema_name": schema})
    return table_dicts

def get_schema_names(database_connection):
    """ Returns a list of schema names """
    cursor = database_connection.cursor()
    cursor.execute("SELECT schema_name FROM information_schema.schemata;")
    schema_names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return schema_names

def get_table_names(connection, schema_name):
    """ Returns a list of table names """
    cursor = connection.cursor()
    cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}';")
    table_names = [table[0] for table in cursor.fetchall()]
    cursor.close()
    return table_names

def get_column_names(connection, table_name, schema_name):
    """ Returns a list of column names """
    cursor = connection.cursor()
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' AND table_schema = '{schema_name}';")
    column_names = [col[0] for col in cursor.fetchall()]
    cursor.close()
    return column_names

# Initialize database schema dict (moved to bottom)
try:
    conn = get_db_connection()
    schemas = ['public']
    database_schema_dict = get_database_info(conn, schemas)
    conn.close()
except Exception as e:
    print(f"Error initializing database schema: {e}")
    database_schema_dict = []

# Initialize database functions
def init_db():
    """Initialize database connection"""
    try:
        conn = get_db_connection()
        if conn and not conn.closed:
            print(f"Connected successfully to {db_credentials['dbname']} database")
            return True
        return False
    except Exception:
        return False

# Database schema info
def get_schema_info():
    """Get database schema information"""
    conn = get_db_connection()
    schemas = ['public']
    database_schema_dict = get_database_info(conn, schemas)
    return "\n".join(
        [
            f"Schema: {table['schema_name']}\nTable: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
            for table in database_schema_dict
        ]
    )

# Add this new property
database_schema_string = get_schema_info()

def ask_postgres_database(connection, query):
    """ Execute the SQL query provided by OpenAI and return the results """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = str(cursor.fetchall())
        return results
    except Exception as e:
        return f"Query failed with error: {e}"

def get_location_settings(connection, location_id):
    """Get location settings including common operations"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT settings FROM locations WHERE id = %s", (location_id,))
            result = cursor.fetchone()
        return json.loads(result[0]) if result and result[0] else {}
    except Exception as e:
        return f"Failed to get location settings: {e}"

def update_location_settings(connection, location_id, settings):
    """Update location settings"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE locations SET settings = %s WHERE id = %s", 
                         (json.dumps(settings), location_id))
        return "Settings updated successfully"
    except Exception as e:
        return f"Failed to update settings: {e}"

def extract_item_id(query):
    """Extract item ID from update query"""
    match = re.search(r'WHERE\s+(?:items\.)?id\s*=\s*(\d+)', query, re.IGNORECASE)
    if not match:
        raise ValueError("Update queries must include item ID in WHERE clause")
    return int(match.group(1))

def validate_time_range(time_str):
    """Validate time range format (0000-2359)"""
    if not re.match(r'^([01]\d|2[0-3])([0-5]\d)$', time_str):
        raise ValueError("Time must be in 24-hour format (0000-2359)")
    return True

def execute_menu_update(connection, query, operation_name=None):
    """Execute menu update with row-level locking and validation"""
    try:
        with connection:  # Auto-commits or rolls back
            with connection.cursor() as cursor:
                # Set transaction isolation level
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                
                # Extract and validate item ID for item updates
                item_id = None
                if "UPDATE items" in query.lower():
                    item_id = extract_item_id(query)
                    # Acquire row-level lock
                    cursor.execute("SELECT * FROM items WHERE id = %s FOR UPDATE", (item_id,))
                    
                    # Validate query plan
                    cursor.execute("EXPLAIN " + query)
                    plan = cursor.fetchall()
                    if not any('Index Scan' in str(row) for row in plan):
                        raise ValueError("Query must use index for updates")
                
                # Validate price updates
                if "UPDATE items SET price" in query.lower():
                    cursor.execute("SELECT COUNT(*) FROM (" + query.replace(";", "") + ") as q WHERE price < 0")
                    if cursor.fetchone()[0] > 0:
                        raise ValueError("Price updates must be non-negative")
                
                # Validate time ranges
                if "UPDATE categories" in query.lower() and ("start_time" in query or "end_time" in query):
                    time_matches = re.findall(r'(?:start|end)_time\s*=\s*(\d{4})', query, re.IGNORECASE)
                    for time_str in time_matches:
                        validate_time_range(time_str)
                
                # Execute update
                cursor.execute(query)
                affected = cursor.rowcount
                
                # Record operation in history if name provided
                if operation_name and "location_id" in st.session_state:
                    settings = get_location_settings(connection, st.session_state["location_id"])
                    settings = add_operation_to_history(settings, {
                        "operation_type": "update",
                        "operation_name": operation_name,
                        "query_template": query,
                        "result_summary": f"Updated {affected} rows"
                    })
                    update_location_settings(connection, st.session_state["location_id"], settings)
                
                return f"Update successful. {affected} rows affected."
    except Exception as e:
        # Transaction will automatically rollback
        return f"Update failed: {e}"

def execute_template_query(connection, template_name: str, params: dict):
    """Execute a predefined query template"""
    try:
        with connection.cursor() as cursor:
            query = QUERY_TEMPLATES[template_name]
            cursor.execute(query, params)
            if template_name.startswith('select'):
                return cursor.fetchall()
            return f"{cursor.rowcount} rows affected"
    except Exception as e:
        return f"Query failed: {e}"

def get_location_hours(connection, location_id: int):
    """Get location hours using template"""
    return execute_template_query(
        connection,
        "view_location_hours",
        {"location_id": location_id}
    )

def update_location_hours(connection, location_id: int, day_of_week: str, 
                        open_time: str, close_time: str):
    """Update location hours using template"""
    return execute_template_query(
        connection,
        "update_location_hours",
        {
            "location_id": location_id,
            "day_of_week": day_of_week,
            "open_time": open_time,
            "close_time": close_time
        }
    )

def get_markers(connection, location_id: int):
    """Get markers using template"""
    return execute_template_query(
        connection,
        "view_markers",
        {"location_id": location_id}
    )

def add_marker(connection, marker_data: dict):
    """Add marker using template"""
    return execute_template_query(
        connection,
        "insert_marker",
        marker_data
    )

def cleanup_menu(connection, location_id: int, item_name: str, option_name: str):
    """Cleanup menu using template"""
    return execute_template_query(
        connection,
        "menu_cleanup",
        {
            "location_id": location_id,
            "item_name": item_name,
            "option_name": option_name
        }
    )

def execute_menu_query(query, params=None):
    """Execute a read-only query and return results with column names"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if cursor.description:  # Check if query returns results
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
                return {
                    "success": True,
                    "results": results,
                    "query": query
                }
            return {
                "success": True,
                "affected_rows": cursor.rowcount,
                "query": query
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }
    finally:
        if conn:
            conn.close()

def process_query_results(results):
    """Convert query results to natural language using OpenAI"""
    import openai
    import os
    import json

    if not results["success"]:
        return f"Error executing query: {results['error']}"

    # Prepare context for OpenAI
    context = {
        "query": results["query"],
        "success": results["success"]
    }
    
    if "results" in results:
        context["data"] = results["results"]
        context["columns"] = results["columns"]
        result_type = "query results"
    else:
        context["affected_rows"] = results["affected_rows"]
        result_type = "update results"

    try:
        # Configure OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("MODEL_FOR_ANALYSIS", "gpt-3.5-turbo")
        temp = float(os.getenv("ANALYSIS_TEMPERATURE", "0.3"))

        # Create system prompt
        system_prompt = f"""You are a helpful assistant that converts database {result_type} into natural language responses.
For query results, describe what was found in a clear, concise way.
For update results, describe what was changed and how many rows were affected.
Be concise but informative."""

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context, indent=2)}
            ],
            temperature=temp,
            max_tokens=150
        )
        
        if not response.choices:
            return "Error: No response generated"
            
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error generating response: {str(e)}"
