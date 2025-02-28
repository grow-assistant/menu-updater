import os
from dotenv import load_dotenv
import time
from io import BytesIO

# Load environment variables to get the API key
load_dotenv()

# Try to import pygame for audio playback
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
    print("✓ Pygame initialized successfully")
except (ImportError, pygame.error) as e:
    PYGAME_AVAILABLE = False
    print(f"⚠️ Pygame error: {str(e)}")

def test_elevenlabs_v151():
    """Test ElevenLabs with version 1.51.0+ API structure"""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ElevenLabs API key not found in environment variables")
        print("Add ELEVENLABS_API_KEY=your_api_key to your .env file")
        return False
        
    print(f"Found API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    try:
        # Import the required modules for new API structure
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play, stream
        print("✓ Successfully imported ElevenLabs package")
        
        # Create a client with the API key
        client = ElevenLabs(api_key=api_key)
        print("✓ Created ElevenLabs client with API key")
        
        # Get available voices
        print("Fetching available voices...")
        response = client.voices.get_all()
        available_voices = response.voices
        print(f"✓ Found {len(available_voices)} voices")
        
        # Display first 3 voices
        for i, voice in enumerate(available_voices[:3]):
            print(f"  {i+1}. {voice.name}")
        
        # Select the first voice
        if available_voices:
            selected_voice = available_voices[0]
            print(f"Selected voice: {selected_voice.name}")
            
            # Generate speech using text_to_speech.convert method with streaming=False
            print("Generating speech...")
            audio = client.text_to_speech.convert(
                text="Hello, this is a test of the ElevenLabs text to speech system.",
                voice_id=selected_voice.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            # Alternatively, collect audio from stream if convert doesn't work
            if not isinstance(audio, bytes):
                print("Converting audio stream to bytes...")
                # Collect all chunks from the generator into a single bytes object
                all_audio = bytearray()
                for chunk in audio:
                    if isinstance(chunk, bytes):
                        all_audio.extend(chunk)
                audio = bytes(all_audio)
                
            print(f"✓ Generated audio of size: {len(audio)} bytes")
            
            # Play the audio
            if PYGAME_AVAILABLE:
                print("Playing audio with pygame...")
                temp_file = BytesIO()
                temp_file.write(audio)
                temp_file.seek(0)
                
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                # Try to use the built-in play function
                print("Playing audio with ElevenLabs play function...")
                play(audio)
            
            print("✓ Speech generated and played successfully")
            
            # Save the audio to a file for testing
            print("Saving audio to test.mp3...")
            with open("test.mp3", "wb") as f:
                f.write(audio)
            print("✓ Audio saved to test.mp3")
            
            return True
        else:
            print("⚠️ No voices found")
            return False
            
    except Exception as e:
        print(f"⚠️ Error with ElevenLabs v1.51.0 approach: {str(e)}")
        return False

def show_package_info():
    print("\n=== Package Information ===")
    try:
        import pkg_resources
        
        # Check ElevenLabs version
        try:
            elevenlabs_version = pkg_resources.get_distribution("elevenlabs").version
            print(f"ElevenLabs package version: {elevenlabs_version}")
        except pkg_resources.DistributionNotFound:
            print("ElevenLabs package not found")
        
        # Check Pygame version
        try:
            pygame_version = pkg_resources.get_distribution("pygame").version
            print(f"Pygame package version: {pygame_version}")
        except pkg_resources.DistributionNotFound:
            print("Pygame package not found")
            
    except ImportError:
        print("Could not import pkg_resources to check package versions")
    
    print("============================")

def main():
    print("=== Testing ElevenLabs Text-to-Speech ===")
    show_package_info()
    
    # Test with the v1.51.0+ API
    success = test_elevenlabs_v151()
    
    if success:
        print("\n✅ ElevenLabs test completed successfully!")
        print("Now you can update your main application to use this API structure.")
    else:
        print("\n❌ ElevenLabs test failed")
        print("You have two options:")
        print("1. Downgrade to a compatible version: pip install elevenlabs==0.2.26")
        print("2. Update your code to work with the new API structure")

if __name__ == "__main__":
    main() 