#!/usr/bin/env python3
"""
Debugging script to test Text-to-Speech (TTS) functionality directly.
This helps diagnose issues with verbal response generation.
"""
import os
import sys
import logging
import json
import yaml
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("logs", "tts_debug.log"))
    ]
)
logger = logging.getLogger("tts_debug")

# Import project modules
from services.orchestrator.orchestrator import OrchestratorService
from services.response.response_generator import ResponseGenerator

def test_elevenlabs_directly():
    """Test ElevenLabs API directly without going through the orchestrator."""
    try:
        import elevenlabs
        
        # Load API key from .env or config
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            # Try to load from .env file
            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('ELEVENLABS_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            logger.error("No ElevenLabs API key found in environment or .env file")
            return False
            
        logger.info(f"Setting ElevenLabs API key (length: {len(api_key)})")
        elevenlabs.set_api_key(api_key)
        
        # Test voice listing
        try:
            logger.info("Fetching available voices from ElevenLabs...")
            voices = elevenlabs.voices()
            voice_count = len(voices) if hasattr(voices, '__len__') else 0
            logger.info(f"Successfully fetched {voice_count} voices from ElevenLabs")
            
            if voice_count > 0:
                # Print the first voice for reference
                voice_sample = voices[0]
                logger.info(f"Sample voice: {voice_sample.name} (ID: {voice_sample.voice_id})")
        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return False
        
        # Test generating audio
        sample_text = "This is a test of the ElevenLabs text to speech API."
        logger.info(f"Generating speech for text: '{sample_text}'")
        
        try:
            # Use default voice if we didn't get any from the API
            voice_id = voices[0].voice_id if voice_count > 0 else "EXAVITQu4vr4xnSDxMaL"
            
            start_time = time.time()
            audio_data = elevenlabs.generate(
                text=sample_text,
                voice=voice_id,
                model="eleven_multilingual_v2"
            )
            generation_time = time.time() - start_time
            
            if audio_data:
                logger.info(f"Successfully generated {len(audio_data)} bytes of audio in {generation_time:.2f}s")
                
                # Save audio for verification
                output_dir = os.path.join("test_output")
                os.makedirs(output_dir, exist_ok=True)
                audio_path = os.path.join(output_dir, "test_tts.mp3")
                
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                    
                logger.info(f"Audio saved to {audio_path}")
                return True
            else:
                logger.error("ElevenLabs returned empty audio data")
                return False
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return False
            
    except ImportError:
        logger.error("Failed to import elevenlabs module. Is it installed?")
        return False
        
def test_orchestrator_tts():
    """Test TTS through the orchestrator service."""
    try:
        # Load configuration
        config_path = os.path.join("config", "config.yaml")
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at {config_path}")
            return False
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure TTS is enabled
        if not config.get("features", {}).get("enable_tts", False):
            logger.warning("TTS is disabled in configuration, enabling it for the test")
            if "features" not in config:
                config["features"] = {}
            config["features"]["enable_tts"] = True
            
        # Create orchestrator
        logger.info("Initializing orchestrator with configuration")
        orchestrator = OrchestratorService(config)
        
        # Test TTS directly
        test_text = "This is a test of the verbal response generator functionality."
        logger.info(f"Testing TTS with text: '{test_text}'")
        
        tts_result = orchestrator.test_tts(test_text, save_to_file=True)
        
        if tts_result.get("success", False):
            logger.info("TTS test successful")
            logger.info(f"Audio file: {tts_result.get('file_path', 'unknown')}")
            return True
        else:
            logger.error(f"TTS test failed: {tts_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error in orchestrator TTS test: {str(e)}")
        return False

def debug_response_generator_initialization():
    """Debug the ResponseGenerator initialization process."""
    try:
        # Load configuration
        config_path = os.path.join("config", "config.yaml")
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at {config_path}")
            return False
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check API keys
        openai_api_key = config.get("api", {}).get("openai", {}).get("api_key")
        elevenlabs_api_key = config.get("api", {}).get("elevenlabs", {}).get("api_key")
        
        logger.info(f"OpenAI API key configured: {bool(openai_api_key)}")
        logger.info(f"ElevenLabs API key configured: {bool(elevenlabs_api_key)}")
        
        # Check TTS config
        logger.info(f"TTS enabled in config: {config.get('features', {}).get('enable_tts', False)}")
        
        # Initialize ResponseGenerator
        logger.info("Initializing ResponseGenerator")
        response_generator = ResponseGenerator(config)
        
        # Check initialization
        logger.info(f"ResponseGenerator initialized: {response_generator is not None}")
        logger.info(f"ElevenLabs API key in ResponseGenerator: {hasattr(response_generator, 'elevenlabs_api_key') and bool(response_generator.elevenlabs_api_key)}")
        logger.info(f"ElevenLabs client in ResponseGenerator: {hasattr(response_generator, 'elevenlabs_client') and response_generator.elevenlabs_client is not None}")
        
        # Test generating a verbal response
        query = "What's on the menu today?"
        category = "MENU_QUERY"
        response_rules = {"max_length": 200, "include_descriptions": True}
        query_results = [{"item": "Pizza", "price": 12.99}]
        context = {"enable_verbal": True}
        
        logger.info(f"Testing verbal response generation with query: '{query}'")
        verbal_response = response_generator.generate_verbal_response(
            query=query,
            category=category,
            response_rules=response_rules,
            query_results=query_results,
            context=context
        )
        
        if verbal_response:
            # Removed logging about verbal response size
            
            # Save audio for verification without logging
            output_dir = os.path.join("test_output")
            os.makedirs(output_dir, exist_ok=True)
            audio_path = os.path.join(output_dir, "response_generator_test.mp3")
            
            with open(audio_path, "wb") as f:
                f.write(verbal_response)
            
            # Removed audio path logging
            return True
        else:
            logger.error("Failed to generate verbal response")
            return False
            
    except Exception as e:
        logger.error(f"Error in ResponseGenerator debugging: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run diagnostic tests for TTS functionality."""
    logger.info("=" * 80)
    logger.info("STARTING TTS DEBUGGING")
    logger.info("=" * 80)
    
    os.makedirs("logs", exist_ok=True)
    
    # Test direct ElevenLabs API
    logger.info("\n" + "-" * 40)
    logger.info("TESTING ELEVENLABS API DIRECTLY")
    logger.info("-" * 40)
    elevenlabs_success = test_elevenlabs_directly()
    
    # Test orchestrator TTS
    logger.info("\n" + "-" * 40)
    logger.info("TESTING ORCHESTRATOR TTS")
    logger.info("-" * 40)
    orchestrator_success = test_orchestrator_tts()
    
    # Debug response generator
    logger.info("\n" + "-" * 40)
    logger.info("DEBUGGING RESPONSE GENERATOR")
    logger.info("-" * 40)
    response_generator_success = debug_response_generator_initialization()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TTS DEBUGGING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"ElevenLabs direct test: {'SUCCESS' if elevenlabs_success else 'FAILED'}")
    logger.info(f"Orchestrator TTS test: {'SUCCESS' if orchestrator_success else 'FAILED'}")
    logger.info(f"ResponseGenerator test: {'SUCCESS' if response_generator_success else 'FAILED'}")
    
    # Overall result
    if elevenlabs_success and orchestrator_success and response_generator_success:
        logger.info("\nAll TTS tests PASSED")
        return 0
    else:
        logger.info("\nSome TTS tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 