#!/usr/bin/env python
"""
Demo script to show the complete flow of a query with date conversion
1. User inputs a query like "How many orders were completed on 2/21/2025?"
2. The system processes it (simulated here)
3. OpenAI generates a response with "February 21st, 2025" (simulated here)
4. SimpleVoice.clean_text_for_speech converts "21st" to "twenty-first"
5. The cleaned text would then be sent to ElevenLabs (not actually done here)
"""

import sys
import os
from datetime import datetime
import time

# Add the project root to sys.path to allow imports from main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the SimpleVoice class from main
try:
    from main import SimpleVoice
    print("✓ Successfully imported SimpleVoice from main.py")
except ImportError:
    print("❌ Could not import SimpleVoice, please run this script from the project root directory")
    sys.exit(1)

def simulate_query_response_flow():
    """Simulate the complete flow from user query to speech output"""
    # Step 1: User query (this would come from the user interface)
    user_query = "How many orders were completed on 2/21/2025?"
    print(f"\n📝 USER QUERY: {user_query}")
    
    # Step 2: Process query (happens in the app)
    print("\n🔄 PROCESSING QUERY...")
    time.sleep(1)  # Simulate processing time
    
    # Step 3: Generate response (this would come from OpenAI API)
    # Here we simulate what OpenAI would return
    openai_response = {
        "VERBAL_ANSWER": "We had four completed orders on February 21st, 2025. That's a solid day for us!",
        "TEXT_ANSWER": "On February 21st, 2025, there were **4 completed orders** at the restaurant. This indicates normal activity for a weekday."
    }
    
    verbal_response = openai_response["VERBAL_ANSWER"]
    text_response = openai_response["TEXT_ANSWER"]
    
    print(f"\n🤖 OPENAI RESPONSE:")
    print(f"  Verbal: \"{verbal_response}\"")
    print(f"  Text:   \"{text_response}\"")
    
    # Step 4: Process for speech (this is the key part)
    voice = SimpleVoice()
    print("\n🔊 PREPARING FOR SPEECH...")
    
    # This is where the ordinal conversion happens
    cleaned_text = voice.clean_text_for_speech(verbal_response)
    
    print("\n📊 TEXT-TO-SPEECH CONVERSION RESULTS:")
    print(f"  Before: \"{verbal_response}\"")
    print(f"  After:  \"{cleaned_text}\"")
    
    # Check for successful conversion
    if "21st" in verbal_response and "twenty-first" in cleaned_text:
        print("\n✅ SUCCESS: \"21st\" was correctly converted to \"twenty-first\"")
    else:
        print("\n❌ FAILURE: \"21st\" was not converted properly")
    
    # Step 5: In the actual app, the cleaned text would be sent to ElevenLabs
    print("\n🎯 RESULT: In the actual app, this text would be sent to ElevenLabs for speech synthesis:")
    print(f"  \"{cleaned_text}\"")
    
    return "twenty-first" in cleaned_text

if __name__ == "__main__":
    print("=== DEMO: COMPLETE QUERY-TO-SPEECH FLOW WITH DATE CONVERSION ===")
    success = simulate_query_response_flow()
    if success:
        print("\n✨ DEMO COMPLETE: The ordinal conversion is working correctly! ✨")
    else:
        print("\n❗ DEMO FAILED: The ordinal conversion is not working correctly.") 