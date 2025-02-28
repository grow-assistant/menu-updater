# Speech Examples and Demos

This directory contains examples and demonstrations related to the speech functionality, specifically focusing on ordinal number conversion for text-to-speech.

## Files

- `demo_complete_flow.py` - Demonstrates the complete flow from user query to speech output, showing how "21st" is converted to "twenty-first" before being sent to ElevenLabs.
- `fix_inflect.py` - Contains the implementation of the ordinal conversion solution, with test cases and commentary on the approach.

## Running the Examples

From the project root directory:

```bash
python examples/speech/demo_complete_flow.py
```

This will simulate a complete query-to-speech flow, showing how ordinal numbers are correctly converted to their word form before speech synthesis.

## Background

These examples were created to address an issue where ordinal numbers like "21st" were not being properly converted to their word form ("twenty-first") in the speech output. The solution implemented in the `SimpleVoice.clean_text_for_speech` method in `main.py` now correctly handles these conversions. 