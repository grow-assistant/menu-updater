"""
Real production flow test for order history query.

This test runs the full pipeline with real services and no mocks
to identify where the actual system is failing.
"""

import os
import sys
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    encoding='utf-8'  # Add explicit UTF-8 encoding
)
logger = logging.getLogger(__name__)

# Replace Unicode characters that might cause issues on Windows
def safe_log(logger_fn, message):
    """Wrapper that replaces problematic Unicode symbols with ASCII equivalents"""
    if isinstance(message, str):
        message = message.replace("✅", "[PASS]").replace("❌", "[FAIL]")
    logger_fn(message)

# Augment the logger with safe logging methods
logger.safe_info = lambda msg: safe_log(logger.info, msg)
logger.safe_error = lambda msg: safe_log(logger.error, msg)
logger.safe_warning = lambda msg: safe_log(logger.warning, msg)

# Import services after setting up logging
from services.orchestrator.orchestrator import OrchestratorService
from services.classification.classifier import ClassificationService
from services.sql_generator.openai_sql_generator import OpenAISQLGenerator  # Using OpenAI instead of Gemini
from services.execution.sql_executor import SQLExecutor
from services.response.response_generator import ResponseGenerator
from services.rules.rules_service import RulesService


def run_real_test():
    """Run test with real production flow and no mocks."""
    logger.info("Starting real production flow test")
    
    # Create a configuration using environment variables
    config = {
        "api": {
            "openai": {
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "model": "gpt-4o-mini"
            },
            "gemini": {
                "api_key": os.environ.get("GEMINI_API_KEY"),
                "model": "gemini-2.0-flash"
            },
            "elevenlabs": {
                "api_key": os.environ.get("ELEVENLABS_API_KEY")
            }
        },
        "database": {
            "connection_string": os.environ.get("DB_CONNECTION_STRING"),
            "max_rows": 1000,
            "timeout": 30
        },
        "logging": {
            "level": "INFO"
        },
        # Add default location ID from environment variables
        "DEFAULT_LOCATION_ID": os.environ.get("DEFAULT_LOCATION_ID", 62),
        # Add persona and verbal settings
        "persona": "casual",
        "enable_verbal": True,
        "max_tts_length": 300,
        "services": {
            "rules": {
                "rules_path": os.path.join(PROJECT_ROOT, "services/rules/query_rules"),
                "system_rules_file": os.path.join(PROJECT_ROOT, "resources/system_rules.yml"),
                "business_rules_file": os.path.join(PROJECT_ROOT, "resources/business_rules.yml")
            },
            "classification": {
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "cache_enabled": True
            },
            "sql_generator": {
                "model": "gpt-4o-mini",  # Changed to OpenAI model
                "temperature": 0.2,
                "max_tokens": 2000,
                "prompt_template": os.path.join(PROJECT_ROOT, "services/sql_generator/templates/sql_prompt.txt"),
                "enable_validation": True,
                "enable_optimization": True
            },
            "execution": {
                "max_rows": 1000,
                "timeout": 30,
                "pool_size": 5
            },
            "response": {
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "templates_dir": os.path.join(PROJECT_ROOT, "services/response/templates"),
                "enable_rich_media": True,
                "verbal_model": "gpt-4o-mini",  # Use same model for verbal responses
                "verbal_temperature": 0.4       # Slightly higher temperature for more natural speech
            }
        }
    }
    
    result = False
    try:
        # Initialize the orchestrator
        logger.info("Initializing OrchestratorService")
        orchestrator = OrchestratorService(config)
        
        # Process the first query through the entire pipeline
        first_query = "How many orders were completed on 2/21/2025?"
        logger.info(f"Processing first query: {first_query}")
        first_result = orchestrator.process_query(first_query)
        
        # Log the result without sensitive information
        log_result = first_result.copy() if isinstance(first_result, dict) else first_result
        if isinstance(log_result, dict) and 'verbal_text' in log_result:
            log_result['verbal_text'] = '[VERBAL TEXT REDACTED]'
        
        logger.info(f"First result: {log_result}")
        
        if "response" in first_result:
            logger.info("First query PASSED! The OrchestratorService successfully processed the query.")
            
            # Prepare context for follow-up query
            context = {
                "session_history": [first_result],
                "user_preferences": {},
                "recent_queries": [first_query],
                "enable_verbal": True,
                "persona": "casual"
            }
            
            # Process the follow-up query
            followup_query = "Who placed those orders?"
            logger.info(f"Processing follow-up query: {followup_query}")
            logger.info(f"Context: {context}")
            
            # Detailed logging of context structure
            logger.info("Context session_history keys:")
            if 'session_history' in context and context['session_history']:
                first_history_item = context['session_history'][0]
                logger.info(f"History item keys: {list(first_history_item.keys())}")
                logger.info(f"Category from history: {first_history_item.get('category')}")
                logger.info(f"Query from history: {first_history_item.get('query')}")
            
            # Process the follow-up query with context
            followup_result = orchestrator.process_query(followup_query, context)
            
            # Log the result without sensitive information
            followup_log_result = followup_result.copy() if isinstance(followup_result, dict) else followup_result
            if isinstance(followup_log_result, dict) and 'verbal_text' in followup_log_result:
                followup_log_result['verbal_text'] = '[VERBAL TEXT REDACTED]'
            
            logger.info(f"Follow-up result: {followup_log_result}")
            
            # Check results
            success = False
            if "response" in followup_result and followup_result["response"]:
                logger.info("Follow-up query PASSED!")
                logger.info(f"Follow-up category: {followup_result.get('category')}")
                logger.info(f"Follow-up is_followup: {followup_result.get('is_followup', False)}")
                success = True
            else:
                logger.error("Follow-up query FAILED! No response generated.")
            
            result = success
        else:
            logger.error("Test FAILED! Response not in result for first query.")
            result = False
    except Exception as e:
        logger.error(f"Orchestrator test FAILED: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        result = False
    finally:
        # Ensure proper cleanup of resources
        try:
            logger.info("Cleaning up resources...")
            # Force Python garbage collection
            import gc
            gc.collect()
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.warning(f"Error during final cleanup: {e}")
    
    return result


if __name__ == "__main__":
    run_real_test() 