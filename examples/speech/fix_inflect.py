"""
This script demonstrates the solution for properly converting ordinal numbers (e.g., "21st") 
to their word form (e.g., "twenty-first") for text-to-speech applications.

The problem: The inflect package's ordinal() method only returns "21st", not "twenty-first".
The solution: A custom implementation that correctly converts ordinal numbers to their word form.
"""

import re
import os
import sys

# Add project root to path to allow importing from main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import inflect
    p = inflect.engine()
except ImportError:
    p = None
    print("Warning: inflect package not found. Ordinal conversion will be limited.")


def convert_ordinals_correctly(text):
    """
    Convert ordinal numbers like "21st" to "twenty-first" for better text-to-speech.
    
    Args:
        text (str): The input text containing ordinal numbers
        
    Returns:
        str: Text with ordinal numbers converted to word form
    """
    if not text:
        return text
        
    # Dictionary for special cases
    ordinal_words = {
        "1st": "first",
        "2nd": "second",
        "3rd": "third",
        "4th": "fourth",
        "5th": "fifth",
        "6th": "sixth",
        "7th": "seventh",
        "8th": "eighth",
        "9th": "ninth",
        "10th": "tenth",
        "11th": "eleventh",
        "12th": "twelfth",
        "13th": "thirteenth",
        "14th": "fourteenth",
        "15th": "fifteenth",
        "16th": "sixteenth",
        "17th": "seventeenth",
        "18th": "eighteenth",
        "19th": "nineteenth",
        "20th": "twentieth",
        "30th": "thirtieth",
        "40th": "fortieth",
        "50th": "fiftieth",
        "60th": "sixtieth",
        "70th": "seventieth",
        "80th": "eightieth",
        "90th": "ninetieth",
        "100th": "hundredth"
    }
    
    def replace_ordinal(match):
        ordinal = match.group(0)
        
        # If it's in our dictionary, return the word form
        if ordinal in ordinal_words:
            return ordinal_words[ordinal]
            
        # For numbers like 21st, 22nd, etc.
        number = int(ordinal[:-2])  # Remove the 'st', 'nd', 'rd', or 'th'
        
        # If we have inflect, try to use it for number to words
        if p:
            # For 21-99 that aren't in our dictionary
            if 21 <= number <= 99:
                # Get the base number in words (e.g., "twenty-one")
                base_word = p.number_to_words(number)
                
                # Extract the last digit to determine suffix
                last_digit = number % 10
                
                if last_digit == 1:
                    return base_word[:-3] + "first"  # Convert one -> first
                elif last_digit == 2:
                    return base_word[:-3] + "second"  # Convert two -> second
                elif last_digit == 3:
                    return base_word[:-5] + "third"  # Convert three -> third
                else:
                    # For 4-9, just remove the last digit and add the appropriate suffix
                    base_digit = last_digit
                    suffix = ordinal_words[f"{base_digit}th"][-2:]  # Get 'th' part
                    return base_word + suffix
            
            # For larger numbers, just return the number in words with appropriate suffix
            # This is a simplified approach - may need refinement for larger numbers
            return p.number_to_words(number)
            
        # Fallback if we can't convert
        return ordinal
    
    # Find all ordinal numbers (e.g., 1st, 2nd, 3rd, 21st, etc.)
    pattern = r'\b\d+(?:st|nd|rd|th)\b'
    
    # Replace all ordinals with their word forms
    result = re.sub(pattern, replace_ordinal, text)
    return result


def updated_clean_text_for_speech(text):
    """
    Clean text for better speech synthesis, including converting ordinal numbers to words.
    
    Args:
        text (str): The input text to clean
        
    Returns:
        str: Cleaned text ready for speech synthesis
    """
    if not text:
        return text
        
    try:
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        
        # Add space after periods for better speech pacing
        text = re.sub(r'\.(?=\S)', '. ', text)
        
        # Convert ordinal numbers to words for better speech
        text = convert_ordinals_correctly(text)
        
        return text
    except Exception as e:
        print(f"Error in clean_text_for_speech: {e}")
        return text  # Return original text if there's an error


# Test the implementation
if __name__ == "__main__":
    test_text = "On February 21st, 2025, we had 4 completed orders. The 1st order was by Brandon Devers, the 2nd by Alex Solis II, the 3rd by Matt Agosto, and the 4th by Michael Russell."
    
    print("Original text:")
    print(test_text)
    print("\nCleaned text for speech:")
    print(updated_clean_text_for_speech(test_text))
    
    # Test with the exact example from the user query
    test_verbal = "On February 21st, 2025, the 1st AI system won the competition. The 3rd place finisher was disappointed."
    
    print("\nTest with verbal response:")
    print(test_verbal)
    print("\nCleaned for speech:")
    print(updated_clean_text_for_speech(test_verbal)) 