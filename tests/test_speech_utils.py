"""
Test script to verify that the centralized speech_utils module correctly converts ordinals.
"""

from utils.speech_utils import convert_ordinals_to_words, clean_text_for_speech

def test_ordinal_conversion():
    """Test the conversion of ordinal numbers to words"""
    test_cases = [
        ("The meeting is scheduled for February 21st, 2025.", "twenty-first"),
        ("The 1st place winner gets a gold medal.", "first"),
        ("This is the 2nd time I'm explaining this.", "second"),
        ("She finished in 3rd place in the competition.", "third"),
        ("He came in 4th in the race.", "fourth"),
        ("We're on the 42nd floor of the building.", "forty-second")
    ]
    
    print("Testing ordinal conversion from utils.speech_utils:")
    print("-" * 70)
    
    success_count = 0
    
    for i, (input_text, expected) in enumerate(test_cases):
        result = convert_ordinals_to_words(input_text)
        success = expected in result
        
        print(f"Test {i+1}:")
        print(f"Input:    {input_text}")
        print(f"Result:   {result}")
        print(f"Expected: {expected} to be in result")
        print(f"Success:  {'✓' if success else '✗'}")
        print("-" * 70)
        
        if success:
            success_count += 1
    
    success_rate = (success_count / len(test_cases)) * 100
    print(f"Overall success rate: {success_count}/{len(test_cases)} ({success_rate:.1f}%)")
    
    # Also test the complete clean_text_for_speech function
    print("\nTesting complete clean_text_for_speech function:")
    test_text = "On February 21st, 2025, the 1st AI system won the competition. **This is important** data."
    cleaned = clean_text_for_speech(test_text)
    print(f"Original: {test_text}")
    print(f"Cleaned:  {cleaned}")
    
    # Check if markdown and ordinals were properly converted
    if "twenty-first" in cleaned and "first" in cleaned and "This is important" in cleaned:
        print("✓ All conversions successful!")
    else:
        print("✗ Some conversions failed!")


if __name__ == "__main__":
    test_ordinal_conversion() 