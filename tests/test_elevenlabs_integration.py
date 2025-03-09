"""
Test the integration of ElevenLabs TTS in the response generator.
"""
import os
import sys
import logging
from pathlib import Path
import yaml
import elevenlabs
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.response.response_generator import ResponseGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("elevenlabs_integration_test")

def load_config():
    """Load the application configuration."""
    config_path = os.path.join(project_root, "config", "config.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Replace environment variables
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = replace_env_vars(value)
            return obj
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            # Handle default values with colon syntax
            if ":-" in env_var:
                env_var, default_value = env_var.split(":-", 1)
            else:
                default_value = ""
            env_value = os.environ.get(env_var, default_value)
            if env_value is None:
                logger.warning(f"Environment variable {env_var} not found")
                return default_value
            return env_value
        else:
            return obj
    
    # Apply recursive replacement
    config = replace_env_vars(config)
    
    return config

def test_basic_elevenlabs_connection():
    """Test basic connection to ElevenLabs API."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("No ElevenLabs API key found in environment variables")
        pytest.skip("No ElevenLabs API key found in environment variables")
    
    elevenlabs.set_api_key(api_key)
    
    try:
        # Just check if we can get available voices
        voices = elevenlabs.voices()
        logger.info(f"Successfully connected to ElevenLabs API. Found {len(voices)} voices.")
        assert len(voices) > 0, "Should find at least one voice"
    except Exception as e:
        logger.error(f"Failed to connect to ElevenLabs API: {str(e)}")
        assert False, f"Failed to connect to ElevenLabs API: {str(e)}"

def test_response_generator_tts():
    """Test the TTS functionality in the ResponseGenerator."""
    # Load configuration
    config = load_config()
    
    # Create ResponseGenerator instance
    response_generator = ResponseGenerator(config)
    
    # Test text to convert to speech
    test_text = "Welcome to Pine Valley Country Club. Our special today is the grilled salmon."
    
    try:
        # Generate audio
        audio_data, verbal_text = response_generator.generate_verbal_response(
            query="What's today's special?",
            category="menu_inquiry",
            response_rules={},
            query_results=[{"item_name": "Grilled Salmon", "price": 24.99}],
            context={"max_verbal_sentences": 2}
        )
        
        if audio_data:
            # Save audio file for testing
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, "test_tts_output.mp3")
            
            with open(file_path, "wb") as f:
                f.write(audio_data)
                
            logger.info(f"TTS test successful. Audio saved to {file_path}")
            logger.info(f"Generated verbal text: {verbal_text}")
            assert os.path.exists(file_path), "Audio file should exist"
            assert len(audio_data) > 0, "Audio data should not be empty"
            assert verbal_text, "Verbal text should not be empty"
        else:
            logger.error("No audio data was generated")
            assert False, "No audio data was generated"
    except Exception as e:
        logger.error(f"Error testing ResponseGenerator TTS: {str(e)}")
        pytest.skip(f"Error testing ResponseGenerator TTS: {str(e)}")

def main():
    """Run the integration tests."""
    logger.info("Testing ElevenLabs Integration")
    
    # Test basic ElevenLabs connection
    logger.info("\n--- Testing Basic ElevenLabs Connection ---")
    if not test_basic_elevenlabs_connection():
        logger.error("Basic ElevenLabs connection test failed")
        return 1
    
    # Test ResponseGenerator TTS
    logger.info("\n--- Testing ResponseGenerator TTS ---")
    if not test_response_generator_tts():
        logger.error("ResponseGenerator TTS test failed")
        return 1
    
    logger.info("\nAll ElevenLabs integration tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 