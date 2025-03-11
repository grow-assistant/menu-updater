"""
Simple test for follow-up detection.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
)
logger = logging.getLogger(__name__)

# Import the classifier
from services.classification.classifier import ClassificationService

def test_followup_detection():
    """Test follow-up detection directly."""
    
    # Create a classifier instance
    classifier = ClassificationService({"api": {"openai": {"api_key": "test-key"}}})
    
    # Create a conversation context with a previous query about orders
    conversation_context = {
        "current_topic": "order_history",
        "last_query": "How many orders were completed on 2/21/2025?",
        "session_history": [
            {
                "query": "How many orders were completed on 2/21/2025?",
                "category": "order_history",
                "response": "There were 4 orders completed on 2/21/2025."
            }
        ]
    }
    
    # Use the fallback classification for the query without context
    basic_result = classifier._fallback_classification("Who placed those orders?")
    logger.info(f"Basic classification result: {basic_result}")
    
    # Now enhance with context
    enhanced_result = classifier._enhance_with_context(basic_result, conversation_context)
    logger.info(f"Enhanced classification result: {enhanced_result}")
    
    # Check if the follow-up detection worked
    is_followup = enhanced_result.get("is_followup", False)
    category = enhanced_result.get("category", enhanced_result.get("query_type", "unknown"))
    
    logger.info(f"Follow-up detection result:")
    logger.info(f"- Is follow-up: {is_followup}")
    logger.info(f"- Category: {category}")
    
    if is_followup and category == "order_history":
        logger.info("✓ Follow-up detection is working correctly!")
    else:
        logger.error("✗ Follow-up detection failed!")

if __name__ == "__main__":
    test_followup_detection() 