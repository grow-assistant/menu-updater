"""Test concurrent transactions with mock database"""
import sys
import os
import time
import threading
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing bulk_operations
sys.modules['streamlit'] = MagicMock()
from utils.bulk_operations import apply_bulk_updates, update_side_items

def setup_mock_db():
    """Set up mock database"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            price REAL,
            category_id INTEGER,
            disabled BOOLEAN
        )
    """)
    
    # Add test data
    cursor.execute("""
        INSERT INTO items (name, price, category_id, disabled)
        VALUES ('French Fries', 3.99, 1, 0)
    """)
    
    conn.commit()
    return conn

def test_concurrent_updates():
    """Test concurrent updates with mock database"""
    conn = setup_mock_db()
    
    # Track transaction order
    transaction_log = []
    
    def transaction1():
        """First transaction"""
        try:
            cursor = conn.cursor()
            print("Transaction 1: Starting")
            transaction_log.append("T1 Start")
            
            # Get initial lock
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("SELECT * FROM items WHERE name = 'French Fries'")
            transaction_log.append("T1 Lock")
            
            # Wait to simulate work
            time.sleep(2)
            
            # Update price
            cursor.execute(
                "UPDATE items SET price = ? WHERE name = 'French Fries'",
                (4.99,)
            )
            transaction_log.append("T1 Update")
            
            conn.commit()
            transaction_log.append("T1 Commit")
            print("Transaction 1: Committed")
        except Exception as e:
            print(f"Transaction 1 error: {str(e)}")
            conn.rollback()
    
    def transaction2():
        """Second transaction"""
        try:
            cursor = conn.cursor()
            print("Transaction 2: Starting")
            transaction_log.append("T2 Start")
            
            # Try to get lock
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("SELECT * FROM items WHERE name = 'French Fries'")
            transaction_log.append("T2 Lock")
            
            # Update price
            cursor.execute(
                "UPDATE items SET price = ? WHERE name = 'French Fries'",
                (5.99,)
            )
            transaction_log.append("T2 Update")
            
            conn.commit()
            transaction_log.append("T2 Commit")
            print("Transaction 2: Committed")
        except Exception as e:
            print(f"Transaction 2 error: {str(e)}")
            conn.rollback()
    
    # Run transactions in threads
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    time.sleep(0.5)  # Give transaction1 time to get lock
    t2.start()
    
    t1.join()
    t2.join()
    
    # Verify transaction order
    print("\nTransaction Log:")
    for entry in transaction_log:
        print(f"- {entry}")
    
    # Verify final state
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM items WHERE name = 'French Fries'")
    final_price = cursor.fetchone()[0]
    print(f"\nFinal price: ${final_price:.2f}")
    
    # Clean up
    conn.close()

if __name__ == "__main__":
    test_concurrent_updates()
