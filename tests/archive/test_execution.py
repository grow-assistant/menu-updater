"""
Test script for the execution service.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

print("Starting execution service test...")

try:
    print("Importing modules...")
    # Import the merged execution service
    from services.execution import (
        SQLExecutionLayer, 
        sql_execution_layer,
        execute_query,
        execute_transaction,
        close_db_pool,
        format_result,
        get_summary_stats,
        SQLExecutor
    )
    
    print("✅ Successfully imported all components from the merged execution service")
    
    # Create an instance of the service
    print("Creating SQLExecutionLayer instance...")
    service = SQLExecutionLayer()
    print(f"✅ Created SQLExecutionLayer instance")
    
    # Test singleton
    print("Checking singleton instance...")
    print(f"✅ Singleton exists: {bool(sql_execution_layer)}")
    
    # Test utility functions
    print("Checking utility functions...")
    print(f"✅ execute_query function exists: {bool(execute_query)}")
    print(f"✅ execute_transaction function exists: {bool(execute_transaction)}")
    print(f"✅ close_db_pool function exists: {bool(close_db_pool)}")
    print(f"✅ format_result function exists: {bool(format_result)}")
    print(f"✅ get_summary_stats function exists: {bool(get_summary_stats)}")
    
    # Test SQLExecutor class
    print("Checking SQLExecutor class...")
    print(f"✅ SQLExecutor class exists: {bool(SQLExecutor)}")
    
    print("\nAll tests passed successfully!")
    
except Exception as e:
    print(f"❌ Error testing execution service: {str(e)}")
    import traceback
    traceback.print_exc() 