from dotenv import load_dotenv
import os
import psycopg2
from pathlib import Path

def test_db_connection():
    # Get the directory containing the script
    base_dir = Path(__file__).resolve().parent
    
    # Load environment variables from .env file
    env_path = base_dir / '.env'
    print(f"Looking for .env file at: {env_path}")
    load_dotenv(env_path)
    
    # Print all environment variables (excluding sensitive data)
    print("\nEnvironment variables loaded:")
    print(f"DB_NAME: {os.getenv('DB_NAME')}")
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_SERVER: {os.getenv('DB_SERVER')}")
    
    # Get database credentials from environment variables
    db_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_SERVER'),
        'port': '5432'  # Explicitly set port
    }
    
    try:
        print("\nAttempting to connect with parameters:", {k: v for k, v in db_params.items() if k != 'password'})
        conn = psycopg2.connect(**db_params)
        print("Successfully connected to the database!")
        
        # Create a cursor and test a simple query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        print("Connection closed successfully.")
        
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")

if __name__ == "__main__":
    test_db_connection() 