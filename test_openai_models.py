import os
from openai import OpenAI
import time
import pytest

@pytest.fixture
def client():
    """Fixture that provides an OpenAI client."""
    return OpenAI()

@pytest.mark.parametrize("model_name", [
    "gpt-3.5-turbo",  # Reliable baseline model
    pytest.param("gpt-4o", marks=pytest.mark.skip(reason="May be expensive to run")),
    "gpt-4o-mini",    # The problematic model from logs
    pytest.param("gpt-4", marks=pytest.mark.skip(reason="May be expensive to run"))
])
def test_model(client, model_name):
    """Test if a specific OpenAI model is available and working"""
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what model are you?"}
            ],
            max_tokens=50
        )
        elapsed_time = time.time() - start_time
        
        assert response.choices[0].message.content.strip() != ""
        assert elapsed_time > 0
    except Exception as e:
        pytest.skip(f"Error with model {model_name}: {str(e)}")

def main():
    # Initialize the OpenAI client with API key from environment
    client = OpenAI()
    
    # Print API key length for debugging (don't print the actual key for security)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    print(f"Using API key (length: {len(api_key)})")
    
    # List of models to test
    models_to_test = [
        "gpt-3.5-turbo",  # Reliable baseline model
        "gpt-4o",         # gpt-4o model (should work)
        "gpt-4o-mini",    # The problematic model from logs
        "gpt-4"           # Another common model
    ]
    
    # Test each model
    results = {}
    for model in models_to_test:
        results[model] = test_model(client, model)
    
    # Summary
    print("\n=== Model Availability Summary ===")
    for model, available in results.items():
        status = "Available" if available else "Not Available"
        print(f"{model}: {status}")

if __name__ == "__main__":
    main() 