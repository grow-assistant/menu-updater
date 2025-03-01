"""
Test file for audio input functionality.
This script tests if your microphone and speech recognition libraries are working properly.
"""

import time
import os
import streamlit as st

def test_speech_recognition():
    """Test if speech recognition is working properly"""
    try:
        import speech_recognition as sr
        st.success("✅ Successfully imported speech_recognition library")
        
        # Create a recognizer
        recognizer = sr.Recognizer()
        st.success("✅ Successfully created recognizer")
        
        # Test microphone access
        try:
            with sr.Microphone() as source:
                st.success("✅ Successfully accessed microphone")
                return True
        except Exception as e:
            st.error(f"❌ Error accessing microphone: {str(e)}")
            st.error("This might be due to missing PyAudio or hardware issues")
            return False
            
    except ImportError:
        st.error("❌ Could not import speech_recognition library")
        st.error("Install it with: pip install SpeechRecognition")
        return False

def test_pyaudio():
    """Test if PyAudio is properly installed"""
    try:
        import pyaudio
        st.success("✅ Successfully imported PyAudio")
        
        # Try to initialize PyAudio
        pa = pyaudio.PyAudio()
        st.success("✅ Successfully initialized PyAudio")
        
        # Get default input device info
        try:
            default_input = pa.get_default_input_device_info()
            st.success(f"✅ Default input device: {default_input['name']}")
        except Exception as e:
            st.warning(f"⚠️ Could not get default input device: {str(e)}")
            
        # List available devices
        st.write("### Available Audio Devices:")
        device_count = pa.get_device_count()
        input_devices = []
        
        for i in range(device_count):
            try:
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(f"Device {i}: {device_info['name']} (Channels: {device_info['maxInputChannels']})")
            except Exception as e:
                st.error(f"Error getting device {i} info: {str(e)}")
                
        if input_devices:
            for device in input_devices:
                st.write(device)
        else:
            st.warning("⚠️ No input devices found")
            
        # Clean up
        pa.terminate()
        return True
        
    except ImportError:
        st.error("❌ Could not import PyAudio")
        st.error("Install it with: pip install PyAudio")
        return False

def listen_and_recognize():
    """Attempt to listen to microphone and recognize speech"""
    try:
        import speech_recognition as sr
        
        # Create a recognizer
        recognizer = sr.Recognizer()
        
        # Message to user
        st.write("### Speech Recognition Test")
        st.write("When you click the button below, I'll listen for speech...")
        
        # Start listening when button is clicked
        if st.button("🎤 Start Listening"):
            try:
                with st.spinner("Listening... Please speak into your microphone"):
                    # Use microphone as source
                    with sr.Microphone() as source:
                        # Adjust for ambient noise
                        st.write("Adjusting for ambient noise...")
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        
                        # Listen for audio
                        st.write("Listening... Please speak now")
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        
                        st.write("Processing speech...")
                        
                    # Recognize speech
                    text = recognizer.recognize_google(audio)
                    st.success(f"Recognized: {text}")
                    return True
                    
            except sr.WaitTimeoutError:
                st.warning("No speech detected within timeout period")
            except sr.UnknownValueError:
                st.warning("Could not understand audio. Please try again.")
            except sr.RequestError as e:
                st.error(f"Speech recognition service error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                
        return False
            
    except Exception as e:
        st.error(f"Error in speech recognition test: {str(e)}")
        return False

def troubleshooting_guide():
    """Display troubleshooting guide for common issues"""
    st.write("## Troubleshooting Guide")
    
    st.write("### Common Issues:")
    
    with st.expander("PyAudio Installation Problems"):
        st.write("""
        **Windows:**
        ```
        pip install pipwin
        pipwin install pyaudio
        ```
        
        **macOS:**
        ```
        brew install portaudio
        pip install pyaudio
        ```
        
        **Linux (Ubuntu/Debian):**
        ```
        sudo apt-get install python3-pyaudio
        ```
        """)
        
    with st.expander("No Microphone Detected"):
        st.write("""
        1. Check if your microphone is properly connected
        2. Make sure your microphone is not muted in your OS settings
        3. Check if other applications can access your microphone
        4. Try restarting your computer
        5. On Windows, check 'Privacy & Security' settings to ensure browser has microphone access
        """)
        
    with st.expander("Recognition Not Working"):
        st.write("""
        1. Check your internet connection (Google recognition requires internet)
        2. Speak clearly and not too quickly
        3. Reduce background noise
        4. Try a different microphone if available
        """)
        
    with st.expander("Alternative Speech Recognition Engines"):
        st.write("""
        If Google's speech recognition isn't working, try:
        
        1. Using local recognition with Sphinx:
        ```
        pip install pocketsphinx
        ```
        
        2. Other services with API keys:
        - Microsoft Azure Speech
        - Amazon Transcribe
        - IBM Watson Speech to Text
        """)

def main():
    st.title("Audio Input Test Tool")
    st.write("This tool checks if your audio input (microphone) is correctly configured.")
    
    # System info
    st.write("## System Information")
    import platform
    st.write(f"Operating System: {platform.system()} {platform.version()}")
    st.write(f"Python Version: {platform.python_version()}")
    
    # Dependencies section
    st.write("## Checking Dependencies")
    sr_available = test_speech_recognition()
    pyaudio_available = test_pyaudio()
    
    # Only test speech recognition if dependencies are available
    if sr_available and pyaudio_available:
        st.write("## Testing Speech Recognition")
        listen_and_recognize()
    else:
        st.error("Please fix the dependency issues above before testing speech recognition")
    
    # Always show troubleshooting guide
    troubleshooting_guide()

if __name__ == "__main__":
    main() 