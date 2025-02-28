import inflect
import os
import sys

# Add the project root to sys.path if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

p = inflect.engine()

print("Testing inflect package ordinal conversions:")
print(f"Number to words: {p.number_to_words(21)}")
print(f"Ordinal: {p.ordinal(21)}")  # This gives 21st

# Let's see what methods are available
methods = [method for method in dir(p) if not method.startswith('_')]
print(f"\nAvailable methods: {methods}")

# Try different approaches
print("\nTesting different approaches:")

# This matches what's in the SimpleVoice.clean_text_for_speech function
def replace_ordinal(match):
    num = int(match.group(1))
    return p.ordinal(num)  # This is what the code uses

print(f"Current code using p.ordinal(21): {p.ordinal(21)}")  

# Try alternatives
if hasattr(p, 'number_to_words'):
    print(f"Number to words (21): {p.number_to_words(21)}")
    
# Try the correct way with available methods
if hasattr(p, 'ordinal_noun'):
    print(f"Ordinal noun: {p.ordinal_noun(21)}")

# Try another approach - combine number_to_words with ordinal
if hasattr(p, 'number_to_words') and hasattr(p, 'ordinal'):
    # Try to get the word form of the ordinal (this might work)
    try:
        ordinal_as_number = p.ordinal(21)  # This gives "21st"
        ordinal_num = ''.join([c for c in ordinal_as_number if c.isdigit()])  # Extract just the number part
        ordinal_word = p.number_to_words(ordinal_num) + p.ordinal(ordinal_num)[-2:]  # Combine words with suffix
        print(f"Combined approach: {ordinal_word}")  # Should give "twenty-onest" which isn't ideal
    except Exception as e:
        print(f"Error with combined approach: {e}") 