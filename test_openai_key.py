import os
from openai import OpenAI
from dotenv import load_dotenv

def test_openai_key():
    """Test if the OpenAI API key works correctly."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the API key
    api_key = os.environ.get("OPENAI_API_KEY")
    print(f"API key length: {len(api_key) if api_key else 'Not found'}")
    
    try:
        # Try with the client approach
        client = OpenAI(api_key=api_key)
        
        # Simple test call
        models = client.models.list()
        print("Success with client approach! Available models:")
        print(models.data[0:3])  # Just show the first 3 models
        
        return True
    except Exception as e:
        print(f"Error with client approach: {e}")
        return False

if __name__ == "__main__":
    test_openai_key() 