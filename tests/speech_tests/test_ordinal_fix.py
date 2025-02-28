#!/usr/bin/env python
import re
import os
import sys

# Add the project root to sys.path to allow imports from main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def convert_ordinals_to_words(text):
    """Test function to convert ordinal numbers to their word form"""
    # Import inflect
    try:
        import inflect
        p = inflect.engine()
        
        # Dictionary of special cases for common ordinals
        ordinal_words = {
            1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
            11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 
            15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 
            19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fortieth",
            50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth", 
            90: "ninetieth", 100: "hundredth", 1000: "thousandth"
        }
        
        # Function to convert ordinal numbers to words
        def replace_ordinal(match):
            # Extract the number part (e.g., "21" from "21st")
            num = int(match.group(1))
            suffix = match.group(2)  # st, nd, rd, th
            
            # Check for special cases first
            if num in ordinal_words:
                return ordinal_words[num]
            
            # For numbers 21-99 that aren't in our special cases
            if 21 <= num < 100:
                tens = (num // 10) * 10
                ones = num % 10
                
                if ones == 0:  # For 30, 40, 50, etc.
                    return ordinal_words[tens]
                else:
                    # Convert the base number to words (e.g., 21 -> twenty-one)
                    base_word = p.number_to_words(num)
                    
                    # If ones digit has a special ordinal form
                    if ones in ordinal_words:
                        # Replace last word with its ordinal form
                        base_parts = base_word.split("-")
                        if len(base_parts) > 1:
                            return f"{base_parts[0]}-{ordinal_words[ones]}"
                        else:
                            return ordinal_words[ones]
            
            # For other numbers, fallback to converting to words then adding suffix
            word_form = p.number_to_words(num)
            return word_form
        
        # Replace ordinal numbers (1st, 2nd, 3rd, 21st, etc.) with word equivalents
        text = re.sub(r'(\d+)(st|nd|rd|th)', replace_ordinal, text)
        return text
    except ImportError:
        print("Inflect package not available. Skipping ordinal conversion.")
        return text

# Test with different ordinal numbers
test_cases = [
    "On February 21st, we celebrate the event.",
    "The 1st place winner gets a gold medal.",
    "This is the 2nd time I'm explaining this.",
    "She finished in 3rd place in the competition.",
    "He came in 4th in the race.",
    "The 22nd amendment limits presidential terms.",
    "The 33rd day of the year is usually February 2nd.",
    "We're on the 42nd floor of the building.",
    "The 101st anniversary will be celebrated next year."
]

print("Testing ordinal conversion:")
print("-" * 50)

for test in test_cases:
    converted = convert_ordinals_to_words(test)
    print(f"Original: {test}")
    print(f"Converted: {converted}")
    print("-" * 50)

# Also test the specific case mentioned by the user (21st)
print("\nSpecific test for '21st':")
specific_test = "The meeting is scheduled for February 21st."
converted_specific = convert_ordinals_to_words(specific_test)
print(f"Original: {specific_test}")
print(f"Converted: {converted_specific}") 