import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv
from prompts.example_queries import EXAMPLE_QUERIES

def load_schema():
    """Load the database schema from the markdown file"""
    try:
        # Get the project root directory using the absolute path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(project_root, 'prompts', 'database_schema.md')
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("Error: database_schema.md not found in prompts directory")
        sys.exit(1)

def create_prompt(schema: str, user_query: str) -> str:
    """Create a prompt for Gemini combining the schema and user query"""
    return f"""You are an expert SQL developer specializing in restaurant order systems. Your task is to generate precise SQL queries for a restaurant management system.

DATABASE CONTEXT:
- PostgreSQL database with restaurant orders, menus, and customer info
- Timezone adjustment: Always use (created_at/updated_at - INTERVAL '7 hours')::date in date filters
- Location filtering: Always include location_id = [ACTUAL_LOCATION_ID] in the WHERE clause
- For completed orders, always use status = 7 (representing "Completed")
- For order history queries, typically join orders with users, locations, and other relevant tables

DATABASE SCHEMA:
{schema}

BUSINESS RULES:
- Order statuses: 0=Open, 1=Pending, 2=Confirmed, 3=In Progress, 4=Ready, 5=In Transit, 6=Cancelled, 7=Completed, 8=Refunded
- Order types: 1=Delivery, 2=Pickup, 3=Dine-In
- Active orders are those with status NOT IN (6, 7, 8)
- Problematic orders are completed orders (status=7) with ratings less than 4
- IMPORTANT: When a user asks about "orders" in general without specifying a status, ALWAYS assume they mean COMPLETED orders (status = 7)

QUERY GUIDELINES:
1. Always include explicit JOINs with proper table aliases (e.g., 'o' for orders, 'u' for users)
2. Always filter by location_id = [ACTUAL_LOCATION_ID]
3. When querying orders without a specific status mentioned, include status = 7 (completed orders)
4. Use COALESCE for nullable numeric fields to handle NULL values
5. Handle division operations safely with NULLIF to prevent division by zero
6. For date filtering, use the timezone adjusted timestamp: (created_at - INTERVAL '7 hours')::date
7. When aggregating data, use appropriate GROUP BY clauses
8. For improved readability, structure complex queries with CTEs (WITH clauses)
9. When counting or summing, ensure proper handling of NULL values

USER QUESTION: {user_query}

THINKING STEP-BY-STEP:
1. What tables do I need to query for this information?
2. What filters should be applied (location, date, status)?
3. Do I need to handle special edge cases like NULL values?
4. Is this a simple count/sum or a more complex analytical query?
5. Does the question mention a specific order status? If not, default to status = 7 (completed orders).

Now, generate a properly formatted SQL query that precisely answers the user's question. Do not include any explanations in your output - only return the SQL query.
"""

def generate_sql_query(prompt: str, model):
    """Generate SQL query using Gemini"""
    try:
        response = model.generate_content(prompt)
        if response.text:
            # Remove any markdown code block syntax
            sql_query = response.text.strip()
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            return sql_query
        else:
            return "Error: No response generated"
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"

def generate_sql_from_user_query(user_query: str, location_id: int, base_sql_query: str = None) -> str:
    """
    Uses Gemini AI to generate an SQL statement based on the user's query, location ID, and optional base query.
    """
    schema = load_schema()
    prompt = create_prompt(schema, user_query)
    
    # Include previous query context if available
    if base_sql_query:
        prompt += f"\n\nPrevious Query Context:\n{base_sql_query}"

    # Setup Gemini
    api_key = os.getenv("GOOGLE_GEMINI_API")
    model_id = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-pro")
    
    if not api_key:
        raise Exception("Error: GOOGLE_GEMINI_API environment variable not set.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    
    generated_sql = generate_sql_query(prompt, model)
    
    # Replace [ACTUAL_LOCATION_ID] placeholder with actual location ID
    generated_sql = generated_sql.replace("[ACTUAL_LOCATION_ID]", str(location_id))
    
    # Validate that the placeholder was replaced
    if "[ACTUAL_LOCATION_ID]" in generated_sql:
        raise ValueError("Location ID placeholder was not replaced in generated SQL")
    
    return generated_sql

def generate_sql_with_custom_prompt(custom_prompt, location_id):
    """Generate SQL using a custom prompt that includes conversation history
    
    Args:
        custom_prompt (str): The complete custom prompt with all context
        location_id (int): The location ID to filter data
        
    Returns:
        str: The generated SQL query
    """
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv
    
    # Load environment variables to get API key
    load_dotenv()
    
    # Get API key from environment variables - use the correct key name from .env
    api_key = os.getenv("GOOGLE_GEMINI_API")
    if not api_key:
        raise ValueError("GOOGLE_GEMINI_API not found in environment variables")
    
    # Get model name from environment variables
    model_name = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-pro")
    
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # Set up the model
    generation_config = {
        "temperature": 0.1,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 2048,
    }
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config
    )
    
    # Generate the SQL query
    response = model.generate_content(custom_prompt)
    
    # Extract and clean the SQL query
    sql_query = response.text.strip()
    
    # Remove markdown code block formatting if present
    if sql_query.startswith("```sql"):
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    elif sql_query.startswith("```"):
        sql_query = sql_query.replace("```", "").strip()
    
    # Replace any remaining [LOCATION_ID] placeholders with the actual location_id
    sql_query = sql_query.replace('[LOCATION_ID]', str(location_id))
    
    return sql_query

def main():
    # Load environment variables
    load_dotenv()
    
    print("\nSQL Query Generator")
    print("------------------")
    print("Type 'exit' to quit")
    print("Enter your question about the database:\n")
    
    while True:
        # Get user input
        user_query = input("> ").strip()
        
        # Check for exit command
        if user_query.lower() in ['exit', 'quit']:
            print("\nGoodbye!")
            break
        
        if not user_query:
            continue
            
        print("\nGenerating SQL query...\n")
        sql_query = generate_sql_from_user_query(user_query, 1)  # Assuming location_id is 1
        print(sql_query)
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    main() 