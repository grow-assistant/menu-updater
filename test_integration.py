"""
Simple test script for the refactored AI Menu Updater application.
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Get the logger
logger = logging.getLogger("ai_menu_updater")
logger.info("Starting test of refactored AI Menu Updater")

# Import the required modules
try:
    from config.settings import DEFAULT_LOCATION_ID
    from tools.tool_factory import create_tools_for_agent
    from main_integration import categorize_query, integrate_with_existing_flow
    from utils.database import check_database_connection
    
    logger.info("Successfully imported refactored modules")
    
    # Check database connection
    db_status = check_database_connection()
    logger.info(f"Database connection status: {db_status}")
    
    # Create tools for agent
    tools = create_tools_for_agent(location_id=DEFAULT_LOCATION_ID)
    logger.info(f"Created {len(tools)} tools for agent")
    
    # Test query categorization
    test_queries = [
        "How many orders did we have yesterday?",
        "Show me all menu items",
        "Update the price of French Fries to $5.99",
        "Disable the Club Sandwich"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting query: '{query}'")
        
        # Test categorization
        categorization = categorize_query(query)
        logger.info(f"Categorization result: {categorization}")
        
        # Create sample context
        context = {
            "selected_location_id": DEFAULT_LOCATION_ID,
            "selected_location_ids": [DEFAULT_LOCATION_ID],
        }
        
        # Test integration with mock callback handler
        class MockCallbackHandler:
            def __init__(self):
                self.responses = []
                
            def on_text(self, text):
                self.responses.append(text)
                logger.info(f"Callback received: {text[:30]}..." if len(text) > 30 else f"Callback received: {text}")
                
            def on_llm_start(self, *args, **kwargs):
                pass
                
            def on_llm_new_token(self, token, **kwargs):
                pass
                
            def on_llm_end(self, *args, **kwargs):
                pass
                
            def empty(self):
                pass
                
            def markdown(self, text):
                logger.info(f"Markdown received: {text[:30]}..." if len(text) > 30 else f"Markdown received: {text}")
                
            def error(self, text):
                logger.error(f"Error received: {text}")
                
            def info(self, text):
                logger.info(f"Info received: {text}")
                
            def success(self, text):
                logger.info(f"Success received: {text}")
            
            def status(self, text, state):
                logger.info(f"Status received: {text} ({state})")
                return self
                
            def write(self, text):
                logger.info(f"Write received: {text[:30]}..." if len(text) > 30 else f"Write received: {text}")
                
        # Create mock callback handler
        callback_handler = MockCallbackHandler()
        
        try:
            # Test integration
            result = integrate_with_existing_flow(
                query=query,
                tools=tools,
                context=context,
                callback_handler=callback_handler
            )
            
            # Log result summary
            if result.get("success", False):
                logger.info(f"Integration successful for query type: {result.get('query_type', 'unknown')}")
                logger.info(f"Verbal answer: {result.get('verbal_answer', 'N/A')}")
                if "sql_query" in result:
                    logger.info(f"SQL query: {result.get('sql_query', 'N/A')}")
            else:
                logger.error(f"Integration failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error testing integration: {str(e)}", exc_info=True)
    
    logger.info("\nAll tests completed!")
    
except ImportError as e:
    logger.error(f"Error importing modules: {str(e)}")
    logger.error("Please make sure you have created all the required modules")
    
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True) 