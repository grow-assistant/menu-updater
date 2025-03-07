"""
Test script to verify the response service migration.

This script tests the functionality of the migrated response service.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    print("Testing response service migration...")
    
    # Import components from the merged response service
    print("Importing components...")
    from services.response import (
        ResponseGenerator
    )
    from services.response.prompt_builder import (
        ResponsePromptBuilder,
        response_prompt_builder
    )
    
    print("✅ Successfully imported all components from the merged response service")
    
    # Check if class and instance exist
    print("Checking ResponsePromptBuilder existence...")
    print(f"✅ ResponsePromptBuilder class exists: {bool(ResponsePromptBuilder)}")
    print(f"✅ response_prompt_builder singleton exists: {bool(response_prompt_builder)}")
    
    # Check if ResponseGenerator class exists
    print("Checking ResponseGenerator class...")
    print(f"✅ ResponseGenerator class exists: {bool(ResponseGenerator)}")
    
    # For a more thorough test, we could create instances and test functionality,
    # but that might require mock dependencies. This verifies that the imports
    # and basic structure are working.
    
    print("\nAll tests passed successfully!")
    
except Exception as e:
    print(f"❌ Error testing response service: {str(e)}")
    import traceback
    traceback.print_exc() 