import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

def test_openai_connection():
    # Load environment variables from .env file
    base_dir = Path(__file__).resolve().parent.parent  # Go up one directory to find .env
    env_path = base_dir / '.env'
    print(f"Looking for .env file at: {env_path}")
    load_dotenv(env_path)
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("No OpenAI API key found in .env file")
    
    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    print(f"API key loaded: {api_key[:8]}...")  # Only show first 8 chars for security

    print("Testing OpenAI connection...")

    # Build a simple conversation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello!"}
    ]
    
    try:
        # Use the new client.chat.completions.create method
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0
        )
        
        if response.choices:
            print("OpenAI Response:")
            print("-" * 50)
            print(response.choices[0].message.content.strip())  # Access content correctly
            print("-" * 50)
        else:
            print("No response from OpenAI!")

    except Exception as e:
        print(f"Error connecting to OpenAI: {e}")

if __name__ == "__main__":
    test_openai_connection()