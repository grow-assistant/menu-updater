"""
Test script to verify Google Gemini API key functionality.
This script tests the same API key initialization that gemini_sql_generator.py uses.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gemini_api_test")

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_gemini_api():
    """Test the Gemini API key and client initialization."""
    logger.info("Starting Gemini API test")

    # Load environment variables
    logger.info("Loading environment variables from .env file")
    load_dotenv()
    
    # Get API key 
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not found in environment variables!")
        return False
    
    logger.info(f"Found GEMINI_API_KEY (length: {len(gemini_api_key)})")
    
    # Get model name
    gemini_model = os.environ.get("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")
    logger.info(f"Using model: {gemini_model}")
    
    try:
        # Import and configure Google GenAI
        logger.info("Attempting to import google.generativeai package")
        try:
            import google.generativeai as genai
            logger.info("Successfully imported google.generativeai")
        except ImportError as e:
            logger.error(f"Failed to import google.generativeai: {e}")
            logger.error("Try installing the package with: pip install -U google-generativeai")
            return False
        
        # Configure the client
        logger.info("Configuring GenAI client with API key")
        genai.configure(api_key=gemini_api_key)
        
        # Create a model instance
        logger.info(f"Creating model instance for {gemini_model}")
        model = genai.GenerativeModel(gemini_model)
        
        # Test with a simple prompt
        test_prompt = "Write a single sentence about SQL queries."
        logger.info(f"Testing model with prompt: '{test_prompt}'")
        
        # Generate response
        response = model.generate_content(test_prompt)
        
        # Check response
        if response and hasattr(response, 'text'):
            logger.info(f"Received response: {response.text}")
            logger.info("Gemini API test SUCCESSFUL! ✅")
            return True
        else:
            logger.error(f"Received invalid response format: {response}")
            logger.error("Gemini API test FAILED! ❌")
            return False
            
    except Exception as e:
        logger.error(f"Error during Gemini API test: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(traceback.format_exc())
        logger.error("Gemini API test FAILED! ❌")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1) 