"""
Fix script for GeminiSQLGenerator initialization issue.

Based on our diagnostics, we found that:
1. The Gemini API key itself works fine and can be used to make successful API calls
2. The google.generativeai package is installed and working
3. The issue is in the GeminiSQLGenerator class where the client_initialized flag is False

This script shows the issue and how to fix it.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gemini_fix")

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_gemini_sql_generator():
    """Fix the GeminiSQLGenerator initialization issue."""
    logger.info("Starting Gemini SQL Generator fix")
    
    # Load environment variables
    load_dotenv()
    
    # Explain the issue
    logger.info("----- PROBLEM DIAGNOSIS -----")
    logger.info("Found issue: The client_initialized flag in GeminiSQLGenerator is set to False")
    logger.info("This happens in the class initialization but is never updated after the API is configured")
    logger.info("The warning_placeholder_replacement error is not related to the API key issue")
    
    # Find the file
    gemini_path = os.path.join(PROJECT_ROOT, "services", "sql_generator", "gemini_sql_generator.py")
    
    if not os.path.exists(gemini_path):
        logger.error(f"Could not find file at {gemini_path}")
        return False
    
    logger.info(f"Found GeminiSQLGenerator at {gemini_path}")
    logger.info("----- RECOMMENDED FIXES -----")
    
    # Solution 1: Modify the code
    logger.info("Solution 1: Add the missing client_initialized = True line")
    logger.info("In services/sql_generator/gemini_sql_generator.py, after line 29 (genai.configure(api_key=api_key))")
    logger.info("Add: self.client_initialized = True")
    
    # Solution 2: Use OpenAI temporarily
    logger.info("Solution 2: Switch to OpenAI temporarily by changing the SQL_GENERATOR_TYPE in .env")
    logger.info("Change SQL_GENERATOR_TYPE=gemini to SQL_GENERATOR_TYPE=openai")
    
    # Check if we want to implement Solution 1
    logger.info("\n----- FIX IMPLEMENTATION -----")
    implement_fix = input("Do you want to implement the fix now? (y/n): ").lower().strip() == 'y'
    
    if implement_fix:
        logger.info("Attempting to apply the fix...")
        
        # Read the file
        try:
            with open(gemini_path, 'r') as f:
                content = f.read()
            
            # Check if we need to add the fix
            if "genai.configure(api_key=api_key)" in content and "self.client_initialized = True" not in content:
                # Insert the fix after the genai.configure line
                modified_content = content.replace(
                    "genai.configure(api_key=api_key)",
                    "genai.configure(api_key=api_key)\n        self.client_initialized = True"
                )
                
                # Write back to the file
                with open(gemini_path, 'w') as f:
                    f.write(modified_content)
                
                logger.info("Fix applied successfully!")
                logger.info("Added 'self.client_initialized = True' after the genai.configure line")
                return True
            else:
                logger.warning("Could not apply fix - either already fixed or file structure has changed")
                return False
        except Exception as e:
            logger.error(f"Error applying fix: {e}")
            return False
    else:
        logger.info("Skipping automatic fix. You can implement the changes manually.")
        return False
    
if __name__ == "__main__":
    fix_gemini_sql_generator() 