# Utility Modules

This directory contains utility modules used throughout the application.

## Files

### `speech_utils.py`

Utility functions for speech and text processing:

- `convert_ordinals_to_words(text)`: Converts ordinal numbers (e.g., "21st") to their word form (e.g., "twenty-first") for better text-to-speech output.
- `clean_text_for_speech(text)`: Comprehensive text cleaning for speech synthesis, including:
  - Removing markdown formatting
  - Converting ordinal numbers to words
  - Improving speech pacing with strategic spaces and pauses
  - Replacing abbreviations with full words

### `langchain_integration.py`

Utility functions for integrating with LangChain, including:

- Setting up logging for LangChain
- Configuring LangChain agents and tools
- Handling context for prompt generation

## Usage

These utilities are designed to be imported and used throughout the application to avoid code duplication and ensure consistent functionality.

Example:

```python
from utils.speech_utils import clean_text_for_speech

# Clean text for speech synthesis
original_text = "The meeting is scheduled for February 21st, 2025."
cleaned_text = clean_text_for_speech(original_text)
# Result: "The meeting is scheduled for February twenty-first, 2025."
``` 