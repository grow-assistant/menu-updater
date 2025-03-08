"""
Main entry point for the AI Restaurant Assistant application.

This file launches the Streamlit interface and initializes logging.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from frontend import run_app
from services.utils.logging import setup_logging, setup_ai_api_logging

# Environment variables will be loaded from .env file via load_dotenv()
# No need to set them programmatically here

def main():
    """Initialize and run the AI Restaurant Assistant."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Setup logging
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    setup_logging(log_file=log_file)
    
    # Setup AI API logging to capture OpenAI interactions
    setup_ai_api_logging()
    
    # Ensure environment variables are loaded
    required_env_vars = [
        "OPENAI_API_KEY", 
        "GEMINI_API_KEY", 
        "DB_CONNECTION_STRING",
        "ELEVENLABS_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Run the Streamlit application
    run_app()


if __name__ == "__main__":
    main() 