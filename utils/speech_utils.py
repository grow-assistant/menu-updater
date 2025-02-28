"""
Utility functions for speech and text processing.
Centralizes the ordinal number conversion functionality.
"""

import re

def convert_ordinals_to_words(text):
    """
    Convert ordinal numbers like "21st" to "twenty-first" for better text-to-speech.
    
    Args:
        text (str): The input text containing ordinal numbers
        
    Returns:
        str: Text with ordinal numbers converted to word form
    """
    if not text:
        return text
        
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
            
            # Fallback: for other numbers, just convert to words
            return p.number_to_words(num)
        
        # Replace ordinal numbers (1st, 2nd, 3rd, 21st, etc.) with word equivalents
        return re.sub(r'(\d+)(st|nd|rd|th)\b', replace_ordinal, text)
    except ImportError:
        # If inflect is not available, return original text
        return text

def clean_text_for_speech(text):
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
        
        # Remove markdown bullet points and replace with natural pauses
        text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)
        
        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        
        # Replace newlines with spaces to make it flow better in speech
        text = re.sub(r"\n+", " ", text)
        
        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()
        
        # Replace common abbreviations with full words
        text = text.replace("vs.", "versus")
        text = text.replace("etc.", "etcetera")
        text = text.replace("e.g.", "for example")
        text = text.replace("i.e.", "that is")
        
        # Convert ordinal numbers to words for better speech - do this BEFORE adding commas
        text = convert_ordinals_to_words(text)
        
        # Improve speech timing with commas for complex sentences
        # Exclude ordinal suffixes to prevent breaking them
        text = re.sub(r"(\d+)([a-zA-Z])", r"\1, \2", text)  # Put pauses after numbers before words
        
        # Add a pause after periods that end sentences
        text = re.sub(r"\.(\s+[A-Z])", r". \1", text)
        
        return text
    except Exception as e:
        print(f"Error in clean_text_for_speech: {str(e)}")
        return text  # Return original text if there's an error 