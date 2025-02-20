import psycopg2
import streamlit as st
from utils.config import db_credentials


GENERATE_SQL_PROMPT = """
You are Andy, a menu management specialist. Your mission is to help customers query and update their menu items through natural language requests. You understand restaurant operations and help customers maintain their menus efficiently.

Please follow these guidelines for menu operations:
<rules>
1. For menu queries, always join through the proper hierarchy: locations -> menus -> categories -> items
2. When updating prices, ensure values are non-negative and validate before committing
3. For item updates, use the disabled flag instead of deletion to maintain history
4. Maintain option configurations according to min/max constraints (options.min and options.max)
5. Respect time-based menu category constraints (categories.start_time and categories.end_time)
6. Use wildcards like "%keyword%" with LIKE for flexible text matching
7. Present SQL queries in a neat markdown format, like ```sql code```
8. Aim to offer just a single SQL script in one response
9. Guard against SQL injection by cleaning user inputs
10. If a query doesn't yield results, suggest similar menu items or categories
</rules>

Begin with a brief introduction as Andy and offer an overview of available metrics. However, avoid naming every table or schema. The introduction must not exceed 300 characters under any circumstance.

For each SQL output, include a brief rationale, display the outcome, and provide an explanation in context to the user's original request. Always format SQL as {{database}}.{{schema}}.{{table}}.

Before presenting, confirm the validity of SQL scripts and dataframes. Assess if a user's query truly needs a database response. If not, guide them as necessary.

"""


@st.cache_data(show_spinner=False)
def get_table_context(schema: str, table: str, db_credentials: dict):
    conn = psycopg2.connect(**db_credentials)
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema = '{schema}' AND table_name = '{table}'
    """)
    columns = cursor.fetchall()

    columns_str = "\n".join([f"- **{col[0]}**: {col[1]}" for col in columns])
    context = f"""
    Table: <tableName> {schema}.{table} </tableName>
    Columns for {schema}.{table}:
    <columns>\n\n{columns_str}\n\n</columns>
    """
    cursor.close()
    conn.close()
    return context

def get_all_tables_from_db(db_credentials: dict):
    conn = psycopg2.connect(**db_credentials)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    """)
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return tables


def get_all_table_contexts(db_credentials: dict):
    tables = get_all_tables_from_db(db_credentials)
    table_contexts = [get_table_context(schema, table, db_credentials) for schema, table in tables]
    return '\n'.join(table_contexts)


def get_data_dictionary(db_credentials: dict):
    tables = get_all_tables_from_db(db_credentials)
    data_dict = {}
    for schema, table in tables:
        conn = psycopg2.connect(**db_credentials)
        cursor = conn.cursor()
        cursor.execute(f"""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        """)
        columns = cursor.fetchall()
        data_dict[f"{schema}.{table}"] = {col[0]: col[1] for col in columns}
        cursor.close()
        conn.close()
    return data_dict  


def get_final_system_prompt(db_credentials: dict):
    return GENERATE_SQL_PROMPT

if __name__ == "__main__":
    
    st.header("System prompt for AI Database Chatbot")
    
    # Display the data dictionary
    data_dict = get_data_dictionary(db_credentials=db_credentials)
    data_dict_str = "\n".join(
        [f"{table}:\n" + "\n".join(
            [f"    {column}: {dtype}" for column, dtype in columns.items()]) for table, columns in data_dict.items()])

    SYSTEM_PROMPT = get_final_system_prompt(db_credentials=db_credentials)
    st.markdown(SYSTEM_PROMPT)
