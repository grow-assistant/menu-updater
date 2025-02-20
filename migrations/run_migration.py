import psycopg2
from utils.config import db_credentials

def run_migration():
    """Execute analytics tables migration"""
    try:
        with open('migrations/001_add_analytics_tables.sql', 'r') as f:
            sql = f.read()
            
        with psycopg2.connect(**db_credentials) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("Migration successful")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
