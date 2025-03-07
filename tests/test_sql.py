"""
Test script to verify the SQL service migration.

This script simply tests if we can import the classes from the new location
without actually initializing them.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    print("Testing SQL service migration...")
    
    # Just try to import the SQLPromptBuilder class
    print("Checking if required classes can be imported...")
    # This only checks if the classes exist and can be imported
    from services.sql_generator.prompt_builder import SQLPromptBuilder
    
    print("✅ SQLPromptBuilder class can be imported")
    
    print("\nSQL service migration test passed!")
    
except Exception as e:
    print(f"❌ Error testing SQL service: {str(e)}")
    import traceback
    traceback.print_exc() 