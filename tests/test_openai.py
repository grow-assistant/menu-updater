"""
Test script to verify OpenAI API connectivity.
This script will try to connect to OpenAI and make a simple query.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def test_v1_openai():
    """Test OpenAI v1.x API"""
    try:
        from openai import OpenAI

        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OpenAI API key not found in environment variables.")
            return False

        # Initialize client
        client = OpenAI(api_key=api_key)

        # Make a simple query
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello!"}],
            max_tokens=10,
        )

        # Print response
        print(f"OpenAI v1.x API Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"Error with OpenAI v1.x API: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing OpenAI API connectivity...")
    success = test_v1_openai()

    if success:
        print("\nOpenAI connectivity test successful!")
    else:
        print("\nOpenAI connectivity test failed. See error messages above.")
