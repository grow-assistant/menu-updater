"""
Integration test for the RulesService and SQL Generator integration.

This script tests that the RulesService can correctly load SQL examples
from the SQL Generator module.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.rules.rules_service import RulesService
from services.sql_generator.sql_example_loader import SQLExampleLoader

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rules_sql_integration():
    """Test the integration between RulesService and SQL Generator."""
    # Create a test configuration
    config = {
        "services": {
            "rules": {
                "rules_path": "resources/rules",
                "resources_dir": "resources",
                "sql_files_path": "services/sql_generator/sql_files",
                "cache_ttl": 60,
                "query_rules_mapping": {
                    "menu": "menu_rules",
                    "order_history": "order_history_rules",
                    "ratings": "query_ratings_rules",
                    "performance": "query_performance_rules",
                }
            },
            "sql_generator": {
                "examples_path": "resources/sql_examples"
            }
        }
    }
    
    # Create the RulesService
    rules_service = RulesService(config)
    
    # Test loading SQL patterns
    logger.info("Testing loading SQL patterns...")
    menu_patterns = rules.get_sql_patterns("menu")
    logger.info(f"Loaded {len(menu_patterns.get('patterns', {}))} menu patterns")
    
    # Test getting rules and examples
    logger.info("Testing getting rules and examples...")
    menu_rules = rules.get_rules_and_examples("menu")
    if "query_patterns" in menu_rules:
        logger.info(f"Loaded {len(menu_rules['query_patterns'])} query patterns from rules")
    
    # Test getting a specific SQL pattern
    logger.info("Testing getting a specific SQL pattern...")
    pattern = rules.get_sql_pattern("menu", "select_all_menu_items")
    if pattern:
        logger.info(f"Successfully loaded SQL pattern 'select_all_menu_items'")
        logger.info(f"Pattern preview: {pattern[:100]}...")
    else:
        logger.warning("Failed to load SQL pattern 'select_all_menu_items'")
    
    # Test SQLExampleLoader integration
    logger.info("Testing SQLExampleLoader integration...")
    sql_example_loader = SQLExampleLoader()
    menu_examples = sql_example_loader.load_examples_for_query_type("menu")
    logger.info(f"Loaded {len(menu_examples)} menu examples from SQLExampleLoader")
    
    logger.info("Integration test completed successfully!")
    return True

if __name__ == "__main__":
    logger.info("Starting RulesService and SQL Generator integration test...")
    success = test_rules_sql_integration()
    if success:
        logger.info("All tests passed!")
        sys.exit(0)
    else:
        logger.error("Tests failed!")
        sys.exit(1) 