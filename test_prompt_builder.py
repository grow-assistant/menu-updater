"""
Test script to analyze the prompt we use for time period extraction.
"""
import sys
from pathlib import Path

# Make sure we can import from the services directory
sys.path.append(str(Path(__file__).parent))

# Import required modules
from services.classification.prompt_builder import ClassificationPromptBuilder

def test_prompt_builder():
    """Test and display the prompt used for classification with time period extraction."""
    print("Testing classification prompt builder for time period extraction...\n")
    
    # Create the prompt builder
    prompt_builder = ClassificationPromptBuilder()
    
    # Test query for date extraction
    test_query = "How many orders were completed on 2/21/2025?"
    
    # Get the prompt that would be sent to OpenAI
    prompt = prompt_builder.build_classification_prompt(test_query)
    
    # Display the system prompt
    print("=" * 80)
    print("SYSTEM PROMPT:")
    print("=" * 80)
    print(prompt["system"])
    print("\n")
    
    # Display the user prompt
    print("=" * 80)
    print("USER PROMPT:")
    print("=" * 80)
    print(prompt["user"])
    print("\n")
    
    # Provide analysis
    print("=" * 80)
    print("ANALYSIS:")
    print("=" * 80)
    print("This is the prompt that would be sent to OpenAI to extract the date '2/21/2025'.")
    print("Based on the system prompt, OpenAI should:")
    print("1. Classify the query type")
    print("2. Extract the date '2/21/2025'")
    print("3. Convert it to a SQL WHERE clause like: WHERE updated_at = '2025-02-21'")
    print("4. Return a JSON object with both the classification and time period clause")
    
    # Check for examples that handle dates
    date_examples = [
        example for example in prompt["system"] 
        if "date" in example.lower() and "where" in example.lower()
    ]
    
    print("\nDate handling examples in the prompt:")
    if date_examples:
        for i, example in enumerate(date_examples, 1):
            print(f"{i}. {example.strip()}")
    else:
        print("No specific date handling examples found in the prompt.")
    
    print("\nThis prompt should guide OpenAI to generate a structured response with the date formatted as a SQL WHERE clause.")
    
if __name__ == "__main__":
    test_prompt_builder() 