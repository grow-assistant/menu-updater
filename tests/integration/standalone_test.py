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
    message = message.replace("✅", "[PASS]").replace("❌", "[FAIL]")
    logger_fn(message)

# Augment the logger with safe logging methods
logger.safe_info = lambda msg: safe_log(logger.info, msg)
logger.safe_error = lambda msg: safe_log(logger.error, msg)
logger.safe_warning = lambda msg: safe_log(logger.warning, msg)

# Import services after setting up logging
from services.orchestrator.orchestrator import OrchestratorService
from services.classification.classifier import ClassificationService
from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
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
                "model": "gemini-1.5-Flash"
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
                "model": "gemini-1.5-Flash",
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
        # Verify our fix has been applied
        logger.info("Creating ClassificationService instance")
        classifier = ClassificationService()
        logger.info(f"ClassificationService has classify method: {hasattr(classifier, 'classify')}")
        
        # Initialize individual services for debugging
        try:
            logger.info("Testing individual services:")
            
            # Initialize ServiceRegistry for independent tests
            from services.utils.service_registry import ServiceRegistry
            ServiceRegistry.initialize(config)
            
            # Test ClassificationService
            logger.info("1. Testing ClassificationService...")
            classifier_service = ClassificationService(config)
            if hasattr(classifier_service, 'classify'):
                logger.safe_info("[PASS] ClassificationService has the classify method")
                test_query = "How many orders were completed on 2/21/2025?"
                classification_result = classifier_service.classify(test_query)
                logger.info(f"Classification result: {classification_result}")
            else:
                logger.safe_error("[FAIL] ClassificationService is missing the classify method")
                return False
            
            # Test RulesService
            logger.info("2. Testing RulesService...")
            rules_service = RulesService(config)
            ServiceRegistry.register("rules", lambda cfg: rules_service)
            logger.info("Loading rules...")
            rules_result = rules_service.get_rules_and_examples(classification_result.get("category"))
            logger.info(f"Rules loaded: {len(rules_result.get('examples', []))} examples found")
            
            # Test GeminiSQLGenerator
            logger.info("3. Testing GeminiSQLGenerator...")
            sql_generator = GeminiSQLGenerator(config)
            ServiceRegistry.register("sql_generator", lambda cfg: sql_generator)
            logger.info("Generating SQL...")
            sql_result = sql_generator.generate(
                test_query, 
                classification_result.get("category"), 
                rules_result
            )
            logger.info(f"SQL generated: {sql_result.get('query', 'No SQL generated')}")
            
            # Test SQLExecutor
            logger.info("4. Testing SQLExecutor...")
            sql_executor = SQLExecutor(config)
            if sql_result.get('query'):
                logger.info("Executing SQL...")
                try:
                    # Preprocess SQL query to replace placeholders with actual values
                    sql_query = sql_result.get('query')
                    
                    # Use the _preprocess_sql_query method from SQLExecutor
                    processed_sql, _ = sql_executor._preprocess_sql_query(sql_query, {})
                    
                    execution_result = sql_executor.execute(
                        processed_sql,
                        {}  # Empty params since we've directly substituted values
                    )
                    if execution_result.get('success', False):
                        logger.info(f"SQL executed successfully: {execution_result.get('results')}")
                    else:
                        logger.warning(f"SQL execution failed: {execution_result.get('error')}")
                except Exception as e:
                    logger.error(f"Individual service test failed: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning("Skipping SQL execution as no SQL was generated")
            
            # Test ResponseGenerator
            logger.info("5. Testing ResponseGenerator...")
            response_generator = ResponseGenerator(config)
            response_result = response_generator.generate(
                test_query,
                classification_result.get('category'),
                rules_result.get('response_rules', {}),
                execution_result.get('results') if sql_result.get('query') and execution_result.get('success', False) else None,
                {}
            )
            logger.info(f"Response generated: {response_result.get('text', 'No response generated')}")
            
            logger.info("All services tested individually")
        except Exception as e:
            logger.error(f"Individual service test failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info("\n\nRunning complete orchestrator test:")
        try:
            # Initialize the orchestrator
            logger.info("Initializing OrchestratorService")
            orchestrator = OrchestratorService(config)
            
            # Process the query through the entire pipeline
            query = "How many orders were completed on 2/21/2025?"
            logger.info(f"Processing query: {query}")
            result = orchestrator.process_query(query)
            
            # Check the result but hide verbal response
            # Create a copy of the result without verbal text for logging
            log_result = result.copy() if isinstance(result, dict) else result
            if isinstance(log_result, dict) and 'verbal_text' in log_result:
                log_result['verbal_text'] = '[VERBAL TEXT REDACTED]'
            
            logger.info(f"Result: {log_result}")
            if "response" in result:
                logger.info("Test PASSED! The OrchestratorService successfully processed the query.")
                logger.info(f"Generated SQL: {result.get('sql_query', 'No SQL generated')}")
                # Log the response but mask its content if it might contain the verbal response
                logger.info(f"Response: [TEXT RESPONSE CONTENT REDACTED]")
                
                # Check for verbal response
                if result.get("has_verbal", False):
                    logger.info("Verbal response was generated successfully!")
                    audio_size = len(result.get("verbal_audio", b""))
                    verbal_text_length = len(result.get("verbal_text", ""))
                    logger.info(f"Verbal audio size: {audio_size} bytes, Verbal text length: {verbal_text_length} chars")
                else:
                    logger.warning("No verbal response was generated")
                
                result = True
            else:
                logger.error("Test FAILED! Response not in result.")
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
            # Clean up Gemini API resources
            import google.generativeai as genai
            
            # Force Python garbage collection
            import gc
            gc.collect()
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.warning(f"Error during final cleanup: {e}")
    
    return result


if __name__ == "__main__":
    run_real_test() 