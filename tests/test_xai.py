import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path

def load_env():
    """Load environment variables from .env file"""
    # Get the project root directory (assuming tests is one level down)
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    
    print(f"Looking for .env file at: {env_path}")  # Debug print
    
    # Check if file exists
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")
        
    # Load the .env file with override=True to ensure values are updated
    if not load_dotenv(env_path, override=True):
        raise ValueError(f"Could not load .env file at {env_path}")
    
    # Verify environment variables are loaded
    required_vars = ['XAI_TOKEN', 'XAI_API_URL', 'XAI_MODEL']
    loaded_vars = {}
    
    # Try to load each variable and print its value
    for var in required_vars:
        value = os.getenv(var)
        loaded_vars[var] = value
        if value:
            masked_value = value[:8] + '...' if len(value) > 8 else value
            print(f"Loaded {var}: {masked_value}")
        else:
            print(f"Failed to load {var} from environment")
            # Print all environment variables for debugging (mask sensitive data)
            print("\nAvailable environment variables:")
            for key, val in os.environ.items():
                if any(secret in key.lower() for secret in ['token', 'key', 'password', 'secret']):
                    masked_val = val[:8] + '...' if val else 'None'
                else:
                    masked_val = val
                print(f"{key}: {masked_val}")
    
    # Check if all required variables are present
    missing_vars = [var for var, value in loaded_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return loaded_vars

def call_xai(club_name, city, state):
    """
    Simulate an xAI call for club amenities information
    """
    # Load and verify environment variables
    env_vars = load_env()
    
    # Construct the payload
    payload = {
        "messages": [{
            "role": "system",
            "content": "You are a helpful assistant that provides a brief overview of a club's location and amenities."
        }, {
            "role": "user",
            "content": f"Please provide a concise overview about {club_name} in {city}, {state}. Is it private or public? Keep it to under 3 sentences."
        }],
        "model": env_vars['XAI_MODEL'],
        "stream": False,
        "temperature": 0.0
    }

    # Log the request (mask sensitive data)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    masked_payload = payload.copy()
    masked_payload['model'] = f"{masked_payload['model'][:8]}..."
    print(f"{timestamp} - DEBUG - xAI request payload={json.dumps(masked_payload)}")

    try:
        response = requests.post(
            env_vars['XAI_API_URL'],
            json=payload,
            headers={
                "Authorization": f"Bearer {env_vars['XAI_TOKEN']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        # Check for successful response
        response.raise_for_status()
        
        # Log the response
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        print(f"{timestamp} - DEBUG - xAI response status code={response.status_code}")
        
        return response.json()['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        print(f"Error calling xAI API: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return None

def main():
    print("Starting xAI test...")
    
    # Test cases
    clubs = [
        {
            "name": "Beacon Hill Country Club",
            "city": "Summit",
            "state": "NJ"
        },
        {
            "name": "Pine Valley Golf Club",
            "city": "Pine Valley",
            "state": "NJ"
        }
    ]
    
    for club in clubs:
        print(f"\nTesting club: {club['name']}")
        print("-" * 50)
        try:
            response = call_xai(club["name"], club["city"], club["state"])
            if response:
                print(f"Response: {response}")
            else:
                print("No response received")
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
        print("-" * 50)

if __name__ == "__main__":
    main()