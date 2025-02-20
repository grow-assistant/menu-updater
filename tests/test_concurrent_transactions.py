"""Test concurrent transactions"""
import sys
import os
import time
import threading
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing bulk_operations
sys.modules['streamlit'] = MagicMock()
from utils.bulk_operations import apply_bulk_updates, update_side_items

def test_concurrent_menu_updates():
    """Test concurrent menu item updates"""
    # Create two connections
    conn1 = psycopg2.connect(
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host=os.environ.get('DB_SERVER')
    )
    conn2 = psycopg2.connect(
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host=os.environ.get('DB_SERVER')
    )
    
    # Set isolation level
    conn1.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
    conn2.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
    
    def transaction1():
        """First transaction"""
        try:
            with conn1.cursor() as cursor:
                print("Transaction 1: Starting")
                cursor.execute("BEGIN")
                cursor.execute(
                    "SELECT * FROM items WHERE name = 'French Fries' FOR UPDATE"
                )
                print("Transaction 1: Got lock, waiting 5 seconds")
                time.sleep(5)
                cursor.execute(
                    "UPDATE items SET price = 4.99 WHERE name = 'French Fries'"
                )
                conn1.commit()
                print("Transaction 1: Committed")
        except Exception as e:
            conn1.rollback()
            print(f"Transaction 1 error: {str(e)}")
    
    def transaction2():
        """Second transaction"""
        try:
            with conn2.cursor() as cursor:
                print("Transaction 2: Starting")
                cursor.execute("BEGIN")
                print("Transaction 2: Trying to get lock")
                cursor.execute(
                    "SELECT * FROM items WHERE name = 'French Fries' FOR UPDATE"
                )
                print("Transaction 2: Got lock")
                cursor.execute(
                    "UPDATE items SET price = 5.99 WHERE name = 'French Fries'"
                )
                conn2.commit()
                print("Transaction 2: Committed")
        except Exception as e:
            conn2.rollback()
            print(f"Transaction 2 error: {str(e)}")
    
    # Run transactions in threads
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    time.sleep(1)  # Give transaction1 time to get lock
    t2.start()
    
    t1.join()
    t2.join()
    
    # Verify final state
    with conn1.cursor() as cursor:
        cursor.execute("SELECT price FROM items WHERE name = 'French Fries'")
        result = cursor.fetchone()
        final_price = result[0] if result else None
        if final_price is not None:
            print(f"Final price: ${final_price:.2f}")
        else:
            print("No price found for French Fries")
    
    # Clean up
    conn1.close()
    conn2.close()

if __name__ == "__main__":
    test_concurrent_menu_updates()
