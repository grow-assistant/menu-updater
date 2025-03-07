#!/usr/bin/env python
"""
ElevenLabs Audio Test Script

This script tests ElevenLabs audio generation and playback.
It creates a simple audio file and provides multiple ways to play it.
"""

import os
import sys
import base64
import time
from pathlib import Path
from dotenv import load_dotenv
import webbrowser
import tempfile

# Load environment variables from .env file
load_dotenv()

# Get ElevenLabs API key from environment
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("❌ ERROR: ELEVENLABS_API_KEY not found in environment variables or .env file.")
    print("Please set your ElevenLabs API key in the .env file or as an environment variable.")
    sys.exit(1)

try:
    import elevenlabs
    from elevenlabs import generate, voices
except ImportError:
    print("❌ ERROR: elevenlabs module not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "elevenlabs"])
    import elevenlabs
    from elevenlabs import generate, voices

# Set ElevenLabs API key
elevenlabs.set_api_key(ELEVENLABS_API_KEY)

def main():
    """Main test function for ElevenLabs audio generation and playback."""
    print("🔊 ElevenLabs Audio Test")
    print("-----------------------")
    
    # Test connection to ElevenLabs API
    print("\n🔍 Testing API connection...")
    try:
        all_voices = voices()
        print(f"✅ Successfully connected to ElevenLabs API. Found {len(all_voices)} voices.")
    except Exception as e:
        print(f"❌ Error connecting to ElevenLabs API: {str(e)}")
        sys.exit(1)
    
    # Generate test audio
    print("\n🔍 Generating test audio...")
    test_text = "This is a test of the ElevenLabs text-to-speech system. If you can hear this message, audio playback is working correctly."
    
    try:
        # Default voice: "Adam" - but you can change to any available voice
        voice_id = "EXAVITQu4vr4xnSDxMaL"  # Adam voice
        audio_data = generate(
            text=test_text,
            voice=voice_id,
            model="eleven_multilingual_v2"
        )
        print(f"✅ Successfully generated {len(audio_data)} bytes of audio data.")
    except Exception as e:
        print(f"❌ Error generating audio: {str(e)}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("./test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Save audio to file
    audio_file_path = output_dir / "test_audio.mp3"
    with open(audio_file_path, "wb") as f:
        f.write(audio_data)
    print(f"✅ Saved audio to {audio_file_path}")
    
    # Create HTML file with audio player
    html_content = create_html_player(audio_data)
    html_file_path = output_dir / "audio_player.html"
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Created HTML audio player at {html_file_path}")
    
    # Open the HTML file in the default browser
    print("\n🔍 Opening audio player in browser...")
    try:
        webbrowser.open(f"file://{html_file_path.absolute()}")
    except Exception as e:
        print(f"❌ Could not open browser automatically: {str(e)}")
        print(f"Please open {html_file_path} manually in your browser.")
    
    print("\n🔍 Testing audio in a temporary Streamlit app...")
    try:
        create_temp_streamlit_app(audio_data)
    except Exception as e:
        print(f"❌ Error creating Streamlit test app: {str(e)}")
    
    print("\n✅ Test completed!")
    print("\nIf you can hear the audio in the browser, the issue is likely with the Streamlit integration.")
    print("If you can't hear audio in both the browser and Streamlit, the issue might be with ElevenLabs API or your browser settings.")

def create_html_player(audio_data):
    """Create an HTML page with an audio player using the provided audio data."""
    audio_base64 = base64.b64encode(audio_data).decode()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ElevenLabs Audio Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        h1 {{ color: #333; }}
        .audio-container {{ padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; }}
        button {{ background-color: #4CAF50; color: white; border: none; padding: 10px 15px; 
                border-radius: 4px; cursor: pointer; margin-right: 10px; font-size: 14px; }}
        button.stop {{ background-color: #f44336; }}
        .message {{ margin-top: 10px; padding: 10px; border-radius: 4px; }}
        .success {{ background-color: #d4edda; color: #155724; }}
        .error {{ background-color: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔊 ElevenLabs Audio Test</h1>
        <p>This page tests if the ElevenLabs audio can be played in your browser.</p>
        
        <div class="audio-container">
            <h2>Standard Audio Player</h2>
            <audio id="audio-player" controls style="width:100%;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Your browser does not support the audio element.
            </audio>
            <div style="margin-top: 15px;">
                <button onclick="document.getElementById('audio-player').play()">Play</button>
                <button class="stop" onclick="document.getElementById('audio-player').pause()">Pause</button>
            </div>
            <div id="message" class="message"></div>
        </div>
        
        <div class="audio-container">
            <h2>Auto-Play Test</h2>
            <p>Testing auto-play capabilities of your browser.</p>
            <audio id="autoplay-audio" autoplay>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
            <button onclick="testAutoplay()">Test Autoplay</button>
            <div id="autoplay-message" class="message"></div>
        </div>
    </div>
    
    <script>
        // Check if audio can be played
        document.addEventListener('DOMContentLoaded', function() {{
            const audioElement = document.getElementById('audio-player');
            const messageDiv = document.getElementById('message');
            
            audioElement.addEventListener('canplaythrough', function() {{
                messageDiv.className = 'message success';
                messageDiv.innerHTML = '✅ Audio loaded successfully. Click play to hear it.';
            }});
            
            audioElement.addEventListener('error', function() {{
                messageDiv.className = 'message error';
                messageDiv.innerHTML = '❌ Error loading audio. Please check the console for details.';
                console.error('Audio playback error:', audioElement.error);
            }});
        }});
        
        // Test autoplay capabilities
        function testAutoplay() {{
            const audioElement = document.getElementById('autoplay-audio');
            const messageDiv = document.getElementById('autoplay-message');
            
            const playPromise = audioElement.play();
            
            if (playPromise !== undefined) {{
                playPromise.then(_ => {{
                    messageDiv.className = 'message success';
                    messageDiv.innerHTML = '✅ Autoplay is supported in your browser!';
                }}).catch(e => {{
                    messageDiv.className = 'message error';
                    messageDiv.innerHTML = '❌ Autoplay is blocked by your browser. This is likely why the Streamlit app audio doesn\'t play automatically.';
                    console.error('Autoplay error:', e);
                }});
            }}
        }}
    </script>
</body>
</html>
"""
    return html

def create_temp_streamlit_app(audio_data):
    """Create a temporary Streamlit app to test audio playback."""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save audio to a file
        audio_path = os.path.join(temp_dir, "test_audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            
        # Create Streamlit app file
        app_path = os.path.join(temp_dir, "streamlit_test_app.py")
        with open(app_path, "w", encoding="utf-8") as f:
            f.write("""
import streamlit as st
import base64
from pathlib import Path

st.set_page_config(page_title="ElevenLabs Audio Test", layout="centered")

st.title("🔊 ElevenLabs Audio Streamlit Test")

# Load the audio file
audio_file = Path("test_audio.mp3")
with open(audio_file, "rb") as f:
    audio_bytes = f.read()

# Create audio player
audio_base64 = base64.b64encode(audio_bytes).decode()
audio_html = f'''
<div style="padding: 10px; background-color: #f8f9fa; border-radius: 8px; margin: 10px 0;">
    <audio id="audio-player" autoplay="true" controls style="width:100%;">
        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
        Your browser does not support the audio element.
    </audio>
    <div style="display: flex; justify-content: center; margin-top: 8px;">
        <button onclick="document.getElementById('audio-player').play()" 
                style="background-color: #4CAF50; color: white; border: none; padding: 5px 15px; 
                border-radius: 4px; cursor: pointer; margin-right: 5px;">
            Play Audio
        </button>
        <button onclick="document.getElementById('audio-player').pause()" 
                style="background-color: #f44336; color: white; border: none; padding: 5px 15px; 
                border-radius: 4px; cursor: pointer;">
            Pause
        </button>
    </div>
    <script>
        // Ensure the audio plays automatically
        document.addEventListener('DOMContentLoaded', function() {{
            const audioElement = document.getElementById('audio-player');
            if(audioElement) {{
                const playPromise = audioElement.play();
                
                if (playPromise !== undefined) {{
                    playPromise.then(_ => {{
                        // Automatic playback started!
                        console.log("Audio playback started successfully");
                    }}).catch(e => {{
                        // Auto-play was prevented
                        console.log("Audio autoplay was prevented: " + e);
                        // Show a message
                        const messageDiv = document.createElement('div');
                        messageDiv.innerHTML = '<div style="color: #856404; background-color: #fff3cd; padding: 8px; border-radius: 4px; margin-top: 8px; text-align: center;">Autoplay blocked by browser. Please click the play button.</div>';
                        audioElement.parentNode.appendChild(messageDiv);
                    }});
                }}
            }}
        }});
    </script>
</div>
'''

st.markdown("<h3>🔊 Voice Response Test</h3>", unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)

# Also use the native Streamlit audio player as a fallback
st.write("### Native Streamlit Audio Player (Fallback)")
st.audio(audio_bytes, format="audio/mp3")
            """)
        
        # Run the Streamlit app
        # We just create it - it's up to the user to run it if they want
        print(f"✅ Created Streamlit test app at {app_path}")
        print(f"Run it with: streamlit run {app_path}")

if __name__ == "__main__":
    main() 