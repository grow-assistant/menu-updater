"""
Simple test script to verify the langchain integration works correctly.
"""

import os
from dotenv import load_dotenv
from utils.langchain_integration import create_simple_chain

# Load environment variables
load_dotenv()

def main():
    # Check if OPENAI_API_KEY is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in your .env file or environment.")
        return
    
    try:
        print("Creating a simple LangChain conversation chain...")
        # Use a simpler approach with fewer parameters
        chain = create_simple_chain(
            model_name="gpt-3.5-turbo",  # Using a cheaper model for testing
            temperature=0.7,
            streaming=False  # Disable streaming for simpler testing
        )
        
        # Test the chain with a simple query
        print("Sending a test query to the chain...")
        response = chain.predict(input="Hello! Can you tell me what LangChain is?")
        print("\nResponse from LangChain:")
        print(response)
        print("\nIntegration test successful!")
        
    except Exception as e:
        print(f"\nError during integration test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 