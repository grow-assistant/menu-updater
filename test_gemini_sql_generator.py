"""
Test script to diagnose issues with GeminiSQLGenerator initialization.
This helps identify what's causing the 'GenAI client not initialized' error.
"""
import os
import sys
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gemini_sql_generator_test")

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_config():
    """Load configuration from config.yaml with environment variable substitution."""
    logger.info("Loading configuration from config.yaml")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Load configuration
    config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    
    try:
        with open(config_path, 'r') as f:
            # Load the raw YAML
            raw_config = f.read()
            
            # Replace environment variables in the format ${VAR_NAME}
            for env_var in os.environ:
                placeholder = "${" + env_var + "}"
                if placeholder in raw_config:
                    raw_config = raw_config.replace(placeholder, os.environ[env_var])
            
            # Parse the YAML with substitutions
            config = yaml.safe_load(raw_config)
            
            logger.info("Configuration loaded successfully")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

def test_gemini_sql_generator():
    """Test the GeminiSQLGenerator initialization."""
    logger.info("Starting GeminiSQLGenerator initialization test")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return False
    
    # Check API key in config
    gemini_api_key = config.get("api", {}).get("gemini", {}).get("api_key")
    if not gemini_api_key:
        logger.error("Gemini API key not found in configuration")
        env_key = os.environ.get("GEMINI_API_KEY")
        logger.info(f"GEMINI_API_KEY in environment: {'Yes (length: ' + str(len(env_key)) + ')' if env_key else 'No'}")
        return False
    
    logger.info(f"Found Gemini API key in config (length: {len(gemini_api_key)})")
    
    try:
        # Import the GeminiSQLGenerator
        logger.info("Importing GeminiSQLGenerator")
        try:
            from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
            logger.info("Successfully imported GeminiSQLGenerator")
        except ImportError as e:
            logger.error(f"Failed to import GeminiSQLGenerator: {e}")
            return False
        
        # Try importing the Google GenAI package
        logger.info("Checking google.generativeai package")
        try:
            import google.generativeai as genai
            logger.info("Successfully imported google.generativeai")
        except ImportError as e:
            logger.error(f"Failed to import google.generativeai: {e}")
            logger.error("Try installing the package with: pip install -U google-generativeai")
            return False
        
        # Test direct package configuration
        logger.info("Testing direct GenAI client configuration")
        try:
            genai.configure(api_key=gemini_api_key)
            logger.info("Direct GenAI client configuration successful")
        except Exception as e:
            logger.error(f"Error configuring GenAI client directly: {e}")
            return False
            
        # Initialize the generator
        logger.info("Initializing GeminiSQLGenerator")
        try:
            # Skip verification and pass None for db_service as in the factory
            generator = GeminiSQLGenerator(config, db_service=None, skip_verification=True)
            logger.info("GeminiSQLGenerator initialized successfully")
            
            # Check client_initialized flag
            logger.info(f"client_initialized flag: {generator.client_initialized}")
            
            # Test health check
            health_check_result = generator.health_check()
            logger.info(f"Health check result: {health_check_result}")
            
            return health_check_result
        except Exception as e:
            logger.error(f"Error initializing GeminiSQLGenerator: {e}")
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error during test: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_gemini_sql_generator()
    sys.exit(0 if success else 1) 