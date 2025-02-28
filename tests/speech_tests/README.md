# Speech Tests

This directory contains test scripts for the text-to-speech functionality, specifically focusing on ordinal number conversion (e.g., converting "21st" to "twenty-first").

## Test Files

### test_inflect.py
Tests the basic functionality of the `inflect` package and explores its capabilities for ordinal number conversion. This script helped identify the limitations of the standard `ordinal()` method, which returns "21st" rather than "twenty-first".

### test_ordinal_fix.py
Demonstrates the improved ordinal number conversion solution that properly converts ordinal numbers like "21st" to their word form "twenty-first". The test includes a variety of test cases covering different ordinal numbers.

### test_prompt_conversion.py
Simulates the complete text-to-speech pipeline, verifying that verbal responses containing ordinal numbers are correctly processed before being sent to speech synthesis. This test ensures that dates like "February 21st" are properly converted to "February twenty-first".

## Running the Tests

To run any of these tests, use the following command from the project root:

```bash
python tests/speech_tests/test_inflect.py
python tests/speech_tests/test_ordinal_fix.py
python tests/speech_tests/test_prompt_conversion.py
```

## Test Results

The tests verify that our implementation correctly converts ordinal numbers to their word forms in various contexts:

- Simple ordinals: 1st → first, 2nd → second, 3rd → third, etc.
- Date-specific ordinals: February 21st → February twenty-first
- Ordinals in sentences: "The 1st order was..." → "The first order was..."

All tests should pass with 100% conversion success rate for the target ordinal numbers. 