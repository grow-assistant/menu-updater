"""
Command-line tool to test audio input functionality.
This script tests if your microphone and speech recognition libraries are working correctly.
Run it directly from the command line with: python test_audio_cli.py
"""

import time
import platform
import sys

def print_colored(text, color="default"):
    """Print colored text to console (if supported)"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "default": "\033[0m"
    }
    
    # Windows command prompt doesn't support ANSI color codes by default
    if platform.system() == "Windows" and "ANSICON" not in os.environ:
        print(text)
        return
        
    end_color = colors["default"]
    color_code = colors.get(color, end_color)
    print(f"{color_code}{text}{end_color}")

def test_speech_recognition():
    """Test if speech recognition is working properly"""
    try:
        import speech_recognition as sr
        print_colored("✅ Successfully imported speech_recognition library", "green")
        
        # Create a recognizer
        recognizer = sr.Recognizer()
        print_colored("✅ Successfully created recognizer", "green")
        
        # Test microphone access
        try:
            with sr.Microphone() as source:
                print_colored("✅ Successfully accessed microphone", "green")
                return True
        except Exception as e:
            print_colored(f"❌ Error accessing microphone: {str(e)}", "red")
            print_colored("This might be due to missing PyAudio or hardware issues", "red")
            return False
            
    except ImportError:
        print_colored("❌ Could not import speech_recognition library", "red")
        print_colored("Install it with: pip install SpeechRecognition", "yellow")
        return False

def test_pyaudio():
    """Test if PyAudio is properly installed"""
    try:
        import pyaudio
        print_colored("✅ Successfully imported PyAudio", "green")
        
        # Try to initialize PyAudio
        pa = pyaudio.PyAudio()
        print_colored("✅ Successfully initialized PyAudio", "green")
        
        # Get default input device info
        try:
            default_input = pa.get_default_input_device_info()
            print_colored(f"✅ Default input device: {default_input['name']}", "green")
        except Exception as e:
            print_colored(f"⚠️ Could not get default input device: {str(e)}", "yellow")
            
        # List available devices
        print("\n=== Available Audio Input Devices ===")
        device_count = pa.get_device_count()
        input_devices = []
        
        for i in range(device_count):
            try:
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(f"Device {i}: {device_info['name']} (Channels: {device_info['maxInputChannels']})")
            except Exception as e:
                print_colored(f"Error getting device {i} info: {str(e)}", "red")
                
        if input_devices:
            for device in input_devices:
                print(device)
        else:
            print_colored("⚠️ No input devices found", "yellow")
            
        # Clean up
        pa.terminate()
        return True
        
    except ImportError:
        print_colored("❌ Could not import PyAudio", "red")
        print_colored("Install it with: pip install PyAudio", "yellow")
        return False

def listen_and_recognize():
    """Attempt to listen to microphone and recognize speech"""
    try:
        import speech_recognition as sr
        
        # Create a recognizer
        recognizer = sr.Recognizer()
        
        # Message to user
        print("\n=== Speech Recognition Test ===")
        print("I'll listen for speech for 5 seconds...")
        input("Press Enter to start listening...")
        
        try:
            print("Listening... Please speak into your microphone")
            
            # Use microphone as source
            with sr.Microphone() as source:
                # Adjust for ambient noise
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen for audio
                print("Listening... Please speak now")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                print("Processing speech...")
                
            # Recognize speech
            text = recognizer.recognize_google(audio)
            print_colored(f"Recognized: {text}", "green")
            return True
                
        except sr.WaitTimeoutError:
            print_colored("No speech detected within timeout period", "yellow")
        except sr.UnknownValueError:
            print_colored("Could not understand audio. Please try again.", "yellow")
        except sr.RequestError as e:
            print_colored(f"Speech recognition service error: {e}", "red")
        except Exception as e:
            print_colored(f"Unexpected error: {str(e)}", "red")
            
        return False
            
    except Exception as e:
        print_colored(f"Error in speech recognition test: {str(e)}", "red")
        return False

def show_troubleshooting_guide():
    """Display troubleshooting guide for common issues"""
    print("\n====== Troubleshooting Guide ======")
    
    print("\n--- PyAudio Installation Problems ---")
    print("""
Windows:
    pip install pipwin
    pipwin install pyaudio

macOS:
    brew install portaudio
    pip install pyaudio

Linux (Ubuntu/Debian):
    sudo apt-get install python3-pyaudio
    """)
    
    print("\n--- No Microphone Detected ---")
    print("""
1. Check if your microphone is properly connected
2. Make sure your microphone is not muted in your OS settings
3. Check if other applications can access your microphone
4. Try restarting your computer
5. On Windows, check 'Privacy & Security' settings to ensure apps have microphone access
    """)
    
    print("\n--- Recognition Not Working ---")
    print("""
1. Check your internet connection (Google recognition requires internet)
2. Speak clearly and not too quickly
3. Reduce background noise
4. Try a different microphone if available
    """)
    
    print("\n--- Alternative Speech Recognition Engines ---")
    print("""
If Google's speech recognition isn't working, try:

1. Using local recognition with Sphinx:
    pip install pocketsphinx

2. Other services with API keys:
    - Microsoft Azure Speech
    - Amazon Transcribe
    - IBM Watson Speech to Text
    """)

def main():
    print("====================================")
    print("        AUDIO INPUT TEST TOOL       ")
    print("====================================")
    print("This tool checks if your audio input (microphone) is correctly configured.\n")
    
    # System info
    print("=== System Information ===")
    print(f"Operating System: {platform.system()} {platform.version()}")
    print(f"Python Version: {platform.python_version()}")
    
    # Dependencies section
    print("\n=== Checking Dependencies ===")
    sr_available = test_speech_recognition()
    pyaudio_available = test_pyaudio()
    
    # Only test speech recognition if dependencies are available
    if sr_available and pyaudio_available:
        print("\n=== Testing Speech Recognition ===")
        listen_and_recognize()
    else:
        print_colored("\nPlease fix the dependency issues above before testing speech recognition", "red")
    
    # Always show troubleshooting guide
    show_troubleshooting_guide()
    
    print("\n====================================")
    print("           Test Complete           ")
    print("====================================")

if __name__ == "__main__":
    try:
        import os  # Import os for environment variable check
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
        sys.exit(1) 