"""
Simple test to verify that the ClassificationService has a classify method.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.classification.classifier import ClassificationService


class TestClassifierFix(unittest.TestCase):
    """Test the fix for ClassificationService.classify method."""
    
    def test_classify_method_exists(self):
        """Test that ClassificationService has a classify method."""
        classifier = ClassificationService()
        
        # Check if the classify method exists
        self.assertTrue(hasattr(classifier, 'classify'), 
                       "ClassificationService should have a classify method")
        
        # Check if the method is callable
        self.assertTrue(callable(getattr(classifier, 'classify')), 
                       "classify should be a callable method")


if __name__ == "__main__":
    unittest.main() 