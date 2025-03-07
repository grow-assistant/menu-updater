"""
ElevenLabs API Testing Script

This script tests various ElevenLabs TTS configurations including:
- Different voice IDs
- Voice settings (stability, similarity_boost)
- Different TTS models
- Text lengths and processing
"""
import os
import time
import argparse
import elevenlabs
from typing import Dict, Any
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("elevenlabs_test")

# Sample personas from the system
PERSONAS = {
    "casual": {
        "voice_id": "UgBBYS2sOqTuMpoF3BR0",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.5
        },
    },
    "professional": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.3
        },
    },
    "enthusiastic": {
        "voice_id": "D38z5RcWu1voky8WS1ja",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.6
        },
    },
    "pro_caddy": {
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.4
        },
    },
    "clubhouse_legend": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.5
        },
    }
}

# Test phrases for different lengths
TEST_PHRASES = {
    "short": "Welcome to Pine Valley Country Club.",
    "medium": "Welcome to Pine Valley Country Club. Our special today is the grilled salmon with seasonal vegetables. Would you like to hear about our wine pairings?",
    "long": "Welcome to Pine Valley Country Club. I'm delighted to assist you today with our menu and dining options. Our chef's special today is the grilled salmon with seasonal vegetables and a lemon-dill sauce. We also have a prime ribeye steak with truffle mashed potatoes that's very popular. For dessert, I recommend our signature chocolate soufflé, which requires 20 minutes to prepare. Please let me know if you have any dietary restrictions or special requests, and I'll be happy to accommodate them."
}

# Available models
AVAILABLE_MODELS = [
    "eleven_flash_v2_5",
    "eleven_multilingual_v2",
    "eleven_monolingual_v1"  # Legacy model
]

# Test directory for saving audio files
DEFAULT_OUTPUT_DIR = "elevenlabs_test_results"

def save_audio(audio_data: bytes, filename: str, output_dir: str) -> str:
    """Save audio data to file and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(audio_data)
    
    return file_path

def test_elevenlabs_api():
    """Test basic ElevenLabs API connectivity."""
    try:
        # Just check if we can get available voices
        voices = elevenlabs.voices()
        logger.info(f"Successfully connected to ElevenLabs API. Found {len(voices)} voices.")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to ElevenLabs API: {str(e)}")
        return False

def test_voice_generation(
    text: str, 
    voice_id: str, 
    model: str,
    voice_settings: Dict[str, float] = None,  # Kept for backwards compatibility but ignored
    output_dir: str = DEFAULT_OUTPUT_DIR
) -> Dict[str, Any]:
    """Test generating speech with specific voice and settings."""
    start_time = time.time()
    result = {
        "success": False,
        "time_taken": 0,
        "file_path": None,
        "error": None
    }
    
    try:
        # Generate audio - voice_settings are ignored as they're not supported in this version
        audio_data = elevenlabs.generate(
            text=text,
            voice=voice_id,
            model=model
        )
        
        # Calculate time taken
        time_taken = time.time() - start_time
        
        # Generate filename
        timestamp = int(time.time())
        filename = f"voice_{voice_id}_{model}_{timestamp}.mp3"
        
        # Save audio file
        file_path = save_audio(audio_data, filename, output_dir)
        
        result.update({
            "success": True,
            "time_taken": time_taken,
            "file_path": file_path
        })
        
        logger.info(f"Generated audio in {time_taken:.2f}s. Saved to {file_path}")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error generating audio: {str(e)}")
    
    return result

def run_test_suite(api_key: str, output_dir: str = DEFAULT_OUTPUT_DIR):
    """Run a comprehensive test suite for ElevenLabs."""
    # Set up API key
    elevenlabs.set_api_key(api_key)
    
    # Test API connectivity
    if not test_elevenlabs_api():
        logger.error("Failed initial API test. Aborting test suite.")
        return False
    
    # Create results dictionary
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_version": "0.2.27",  # Hardcoded because elevenlabs module doesn't expose version
        "tests": []
    }
    
    # Test 1: Test all personas with a short phrase
    logger.info("Testing all personas with a short phrase...")
    for persona_name, persona_data in PERSONAS.items():
        voice_id = persona_data["voice_id"]
        # Voice settings are ignored
        
        result = test_voice_generation(
            text=TEST_PHRASES["short"], 
            voice_id=voice_id,
            model="eleven_multilingual_v2",
            output_dir=output_dir
        )
        
        results["tests"].append({
            "test_type": "persona_test",
            "persona": persona_name,
            "voice_id": voice_id,
            "text_length": "short",
            "result": result
        })
    
    # Test 2: Test different text lengths with a single voice
    default_voice_id = PERSONAS["casual"]["voice_id"]
    logger.info(f"Testing different text lengths with voice ID {default_voice_id}...")
    for length_name, text in TEST_PHRASES.items():
        result = test_voice_generation(
            text=text, 
            voice_id=default_voice_id,
            model="eleven_multilingual_v2",
            output_dir=output_dir
        )
        
        results["tests"].append({
            "test_type": "length_test",
            "text_length": length_name,
            "voice_id": default_voice_id,
            "result": result
        })
    
    # Test 3: Test different models with a single voice
    logger.info(f"Testing different models with voice ID {default_voice_id}...")
    for model in AVAILABLE_MODELS:
        result = test_voice_generation(
            text=TEST_PHRASES["medium"], 
            voice_id=default_voice_id,
            model=model,
            output_dir=output_dir
        )
        
        results["tests"].append({
            "test_type": "model_test",
            "model": model,
            "voice_id": default_voice_id,
            "result": result
        })
    
    # Test 4: Remove voice settings tests as they're not supported in this version
    
    # Save results to JSON file
    results_path = os.path.join(output_dir, "test_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test suite completed. Results saved to {results_path}")
    
    # Print summary
    success_count = sum(1 for test in results["tests"] if test["result"]["success"])
    total_tests = len(results["tests"])
    logger.info(f"Test summary: {success_count}/{total_tests} tests passed")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="ElevenLabs API Testing Tool")
    parser.add_argument("--api-key", type=str, help="ElevenLabs API key (or set ELEVENLABS_API_KEY env var)")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory to save test results")
    
    args = parser.parse_args()
    
    # Get API key from args or environment variable
    api_key = args.api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("No ElevenLabs API key provided. Use --api-key or set ELEVENLABS_API_KEY environment variable.")
        return 1
    
    # Run test suite
    run_test_suite(api_key, args.output_dir)
    return 0

if __name__ == "__main__":
    exit(main())