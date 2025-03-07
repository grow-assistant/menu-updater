"""
Test script for the classification service.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

print("Starting classification service test...")

try:
    print("Importing modules...")
    # Import the merged classification service
    from services.classification import ClassificationService, QueryClassifierInterface, classifier_interface, ClassificationPromptBuilder
    
    print("✅ Successfully imported all components from the merged classification service")
    
    # Create an instance of the service
    print("Creating ClassificationService instance...")
    service = ClassificationService()
    print(f"✅ Created ClassificationService instance")
    
    # Get available categories
    categories = service.categories
    print(f"✅ Available categories: {categories}")
    
    # Test the interface
    print("Creating QueryClassifierInterface instance...")
    interface = QueryClassifierInterface()
    print(f"✅ Created QueryClassifierInterface instance")
    
    # Test singleton
    print("Checking singleton instance...")
    print(f"✅ Singleton exists: {bool(classifier_interface)}")
    
    # Test prompt builder
    print("Creating ClassificationPromptBuilder instance...")
    builder = ClassificationPromptBuilder()
    print(f"✅ Created ClassificationPromptBuilder instance")
    
    print("\nAll tests passed successfully!")
    
except Exception as e:
    print(f"❌ Error testing classification service: {str(e)}")
    import traceback
    traceback.print_exc() 