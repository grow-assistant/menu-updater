# First, set environment variables to suppress warnings
import os
os.environ["STREAMLIT_LOG_LEVEL"] = "critical"  # Even stricter than error
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SILENCE_NON_RUNTIME_WARNING"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings

import sys
import json
import logging
import time
import threading
from io import StringIO, BytesIO
from typing import Tuple, List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import requests
from unittest.mock import patch, MagicMock
import warnings
import random
import traceback

# Configure minimal logging - suppress ALL logs
logging.basicConfig(level=logging.CRITICAL)  # Only show critical errors

# Suppress all loggers - including absl used by gRPC
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)

# Extra suppression for specific loggers
for logger_name in ['tensorflow', 'absl', 'streamlit', 'google']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Global variables for feature availability
SPEECH_RECOGNITION_AVAILABLE = False
ELEVENLABS_AVAILABLE = False
PYGAME_AVAILABLE = False
USE_NEW_API = False

# Global module references
pygame = None

# Try to import app modules at the global level
try:
    import app
    from utils.function_calling_spec import functions as get_functions_list
    from utils import database_functions
    from utils.create_sql_statement import generate_sql_from_user_query, load_schema, create_prompt
    from utils.query_processing import process_query_results
    APP_MODULES_IMPORTED = True
except ImportError as e:
    print(f"⚠️ Error importing app modules: {str(e)}")
    APP_MODULES_IMPORTED = False

# If the module import fails, create a mock version of the generate_sql_from_user_query function
if not APP_MODULES_IMPORTED:
    def generate_sql_from_user_query(user_query, location_id, base_sql_query=None):
        """Mock implementation for when the real function isn't available"""
        print("⚠️ Using mock SQL generator - actual database integration not available")
        
        # Return a simple mock query - this won't work with a real database but prevents errors
        if "revenue" in user_query.lower():
            return "SELECT SUM(order_total) AS total_revenue FROM orders WHERE location_id = " + str(location_id)
        elif "popular" in user_query.lower() or "menu items" in user_query.lower():
            return "SELECT menu_item_name, COUNT(*) as count FROM order_items WHERE location_id = " + str(location_id) + " GROUP BY menu_item_name ORDER BY count DESC LIMIT 5"
        elif "orders" in user_query.lower():
            return "SELECT COUNT(*) as order_count FROM orders WHERE location_id = " + str(location_id)
        elif "who" in user_query.lower() or "staff" in user_query.lower():
            return "SELECT first_name, last_name FROM staff WHERE location_id = " + str(location_id)
        else:
            return "SELECT * FROM orders WHERE location_id = " + str(location_id) + " LIMIT 5"
            
    # Also create mock versions of other potentially used functions
    def app():
        class MockApp:
            @staticmethod
            def adjust_query_timezone(query, location_id):
                return query
                
            @staticmethod
            def execute_menu_query(query):
                # Return mock data based on query
                if "revenue" in query.lower():
                    return {"success": True, "results": [{"total_revenue": 12345.67}]}
                elif "menu_item_name" in query.lower():
                    return {"success": True, "results": [
                        {"menu_item_name": "Burger", "count": 42},
                        {"menu_item_name": "Pizza", "count": 37},
                        {"menu_item_name": "Salad", "count": 25}
                    ]}
                elif "order_count" in query.lower():
                    return {"success": True, "results": [{"order_count": 156}]}
                elif "first_name" in query.lower():
                    return {"success": True, "results": [
                        {"first_name": "John", "last_name": "Smith"},
                        {"first_name": "Jane", "last_name": "Doe"}
                    ]}
                else:
                    return {"success": True, "results": [{"order_id": 123, "customer_name": "Example Customer", "order_total": 45.67}]}
        
        return MockApp()
    
    # Mock the app module
    import types
    sys.modules['app'] = types.ModuleType('app')
    sys.modules['app'].adjust_query_timezone = app().adjust_query_timezone
    sys.modules['app'].execute_menu_query = app().execute_menu_query

    # Mock the get_clients function
    def get_clients():
        """Return mock client for OpenAI and xAI config"""
        class MockOpenAIClient:
            class ChatCompletions:
                @staticmethod
                def create(model=None, messages=None, functions=None, temperature=None):
                    class MockResponse:
                        class Choice:
                            class Message:
                                def __init__(self, content):
                                    self.content = content
                                    self.function_call = None
                                    
                            def __init__(self, content):
                                self.message = self.Message(content)
                                
                        def __init__(self, content):
                            self.choices = [self.Choice(content)]
                    
                    # Create a simple mock response
                    return MockResponse("This is a mock response from the AI assistant.")
            
            def __init__(self):
                self.chat = self.ChatCompletions()
        
        return MockOpenAIClient(), {"dummy": "config"}

# Define error messages for easy reuse
ERROR_MESSAGES = {
    "pyaudio_install": "\nTo enable voice input, install PyAudio:\n"
                      "  - Windows: pip install pipwin && pipwin install pyaudio\n"
                      "  - macOS: brew install portaudio && pip install pyaudio\n"
                      "  - Linux: sudo apt-get install python3-pyaudio\n"
                      "  - With conda: conda install -c conda-forge pyaudio",
    "speech_recognition_install": "To enable speech input, run: pip install SpeechRecognition",
    "elevenlabs_install": "To enable voice output, run: pip install elevenlabs"
}

def setup_speech_recognition() -> bool:
    """Setup speech recognition and return availability status"""
    global SPEECH_RECOGNITION_AVAILABLE
    
    try:
        import speech_recognition as sr
        SPEECH_RECOGNITION_AVAILABLE = True
        print("✓ Speech recognition library imported successfully")
        
        # Also check if PyAudio is available by testing microphone setup
        try:
            # Just create a Microphone instance to test if PyAudio is available
            mic = sr.Microphone()
            print("✓ Microphone access (PyAudio) confirmed")
            return True
        except Exception as e:
            SPEECH_RECOGNITION_AVAILABLE = False
            error_msg = str(e)
            print(f"⚠️ Speech recognition library imported but microphone access failed: {error_msg}")
            print(ERROR_MESSAGES["pyaudio_install"])
            return False
    except ImportError:
        SPEECH_RECOGNITION_AVAILABLE = False
        print(ERROR_MESSAGES["speech_recognition_install"])
        return False

def setup_elevenlabs() -> bool:
    """Setup ElevenLabs and return availability status"""
    global ELEVENLABS_AVAILABLE, USE_NEW_API
    
    try:
        print("Attempting to import ElevenLabs...")
        
        # Try multiple approaches for different package versions
        try:
            # Latest version with Client (1.51.0+)
            from elevenlabs.client import ElevenLabs
            test_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
            USE_NEW_API = True
            print("✓ ElevenLabs package (v1.51.0+) loaded successfully with client approach")
        except Exception as e:
            print(f"Error with new API approach: {str(e)}")
            print("Falling back to legacy approach...")
            # Older version with direct imports
            from elevenlabs import generate, play, set_api_key, voices, Voice, VoiceSettings
            if os.getenv("ELEVENLABS_API_KEY"):
                set_api_key(os.getenv("ELEVENLABS_API_KEY"))
            USE_NEW_API = False
            print("✓ ElevenLabs package (older version) loaded successfully with legacy approach")
        ELEVENLABS_AVAILABLE = True
        return True
    except Exception as e:
        print(f"Complete ElevenLabs initialization error: {str(e)}")
        ELEVENLABS_AVAILABLE = False
        USE_NEW_API = False
        print(ERROR_MESSAGES["elevenlabs_install"])
        return False

def setup_audio_playback() -> bool:
    """Setup audio playback and return availability status"""
    global PYGAME_AVAILABLE, pygame
    
    try:
        import pygame as pg
        pygame = pg  # Assign to global variable
        pygame.mixer.init()
        PYGAME_AVAILABLE = True
        print("✓ Pygame audio initialized successfully")
        return True
    except (ImportError, Exception) as e:
        PYGAME_AVAILABLE = False
        print(f"Pygame error: {str(e)}")
        return False

def initialize_dependencies():
    """Initialize all dependencies and return overall status"""
    speech_available = setup_speech_recognition()
    elevenlabs_available = setup_elevenlabs()
    audio_playback_available = setup_audio_playback()
    
    # Check if app modules were already imported
    app_modules_imported = APP_MODULES_IMPORTED
    
    # Only try to import app modules again if they weren't already imported
    if not app_modules_imported:
        try:
            import app
            from utils.function_calling_spec import functions as get_functions_list
            from utils import database_functions
            from utils.create_sql_statement import generate_sql_from_user_query, load_schema, create_prompt
            from utils.query_processing import process_query_results
            app_modules_imported = True
            print("✓ App modules imported successfully")
        except ImportError as e:
            print(f"⚠️ Error importing app modules: {str(e)}")
    else:
        print("✓ App modules already imported")
    
    return {
        "speech_recognition": speech_available,
        "elevenlabs": elevenlabs_available,
        "audio_playback": audio_playback_available,
        "app_modules": app_modules_imported
    }

class MockSessionState:
    """Mock session state class with attribute access similar to Streamlit's session_state"""
    
    def __init__(self, location_id: int = 62):
        self.selected_location_id = location_id
        self.last_sql_query = None
        self.api_chat_history = [{
            "role": "system", 
            "content": "Test system prompt"
        }]
        self.full_chat_history = []
    
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)
    
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

class ElevenLabsVoice:
    """Class to handle ElevenLabs text-to-speech functionality with improved error handling"""
    
    def __init__(self, default_voice_id: str = "UgBBYS2sOqTuMpoF3BR0"):
        self.enabled = False
        self.voice_id = default_voice_id
        self.available_voices = []
        self.initialized = False
        self.client = None
        self.voice_name = "Unknown"
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize ElevenLabs with better error handling"""
        if not ELEVENLABS_AVAILABLE:
            return
            
        try:
            # Get API key from environment variable
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                print("⚠️ ElevenLabs API key not found in environment variables")
                return
                
            if USE_NEW_API:
                # Create a client with the API key using the correct import
                from elevenlabs.client import ElevenLabs
                self.client = ElevenLabs(api_key=api_key)
                print("✓ Created ElevenLabs client with API key")
                
                # Get available voices
                try:
                    response = self.client.voices.get_all()
                    self.available_voices = response.voices
                    print(f"✓ Found {len(self.available_voices)} voices")
                except Exception as e:
                    print(f"⚠️ Error getting voices: {str(e)}")
                    return
                
                # Default voice is already set, but verify it exists in available voices
                voice_exists = any(voice.voice_id == self.voice_id for voice in self.available_voices)
                if not voice_exists:
                    print(f"⚠️ Specified voice ID {self.voice_id} not found, defaulting to first available voice")
                    if self.available_voices:
                        self.voice_id = self.available_voices[0].voice_id
                        self.voice_name = self.available_voices[0].name
                else:
                    # Find and set voice name
                    for voice in self.available_voices:
                        if voice.voice_id == self.voice_id:
                            self.voice_name = voice.name
                            break
                    print(f"✓ Using voice: {self.voice_name} (ID: {self.voice_id})")
                
                self.enabled = True
                self.initialized = True
                print("✓ ElevenLabs voice initialized successfully")
            else:
                # For older version
                from elevenlabs import generate, play, set_api_key, voices, Voice, VoiceSettings
                set_api_key(api_key)
                try:
                    self.available_voices = voices()
                    print(f"✓ Found {len(self.available_voices)} voices")
                except Exception as e:
                    print(f"⚠️ Error getting voices: {str(e)}")
                    return
                
                # Check if specified voice ID exists
                voice_exists = any(voice.voice_id == self.voice_id for voice in self.available_voices)
                if not voice_exists:
                    print(f"⚠️ Specified voice ID {self.voice_id} not found, defaulting to first available voice")
                    if self.available_voices:
                        self.voice_id = self.available_voices[0].voice_id
                        self.voice_name = self.available_voices[0].name
                else:
                    # Find and set voice name
                    for voice in self.available_voices:
                        if voice.voice_id == self.voice_id:
                            self.voice_name = voice.name
                            break
                    print(f"✓ Using voice: {self.voice_name} (ID: {self.voice_id})")
                
                self.enabled = True
                self.initialized = True
                print("✓ ElevenLabs voice initialized successfully (legacy API)")
        except Exception as e:
            print(f"⚠️ Error initializing ElevenLabs: {str(e)}")
    
    def list_voices(self) -> str:
        """List available voices with details"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        if not self.available_voices:
            return "No voices available"
        
        voice_list = []
        current_voice_marker = " ← current"
        
        for i, voice in enumerate(self.available_voices):
            marker = current_voice_marker if voice.voice_id == self.voice_id else ""
            voice_list.append(f"{i+1}. {voice.name} (ID: {voice.voice_id}){marker}")
        
        return "\n".join(voice_list)
    
    def set_voice(self, voice_index_or_id: Union[str, int]) -> str:
        """Set the voice by index (1-based) or by voice ID with improved feedback"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        if not self.available_voices:
            return "No voices available"
            
        # Store old voice ID for comparison
        old_voice_id = self.voice_id
        
        # Check if input is a voice ID
        for voice in self.available_voices:
            if voice.voice_id == voice_index_or_id:
                self.voice_id = voice.voice_id
                self.voice_name = voice.name
                return f"Voice set to {voice.name} (ID: {voice.voice_id})"
        
        # If not a voice ID, try as an index
        try:
            index = int(voice_index_or_id) - 1
            if 0 <= index < len(self.available_voices):
                self.voice_id = self.available_voices[index].voice_id
                self.voice_name = self.available_voices[index].name
                return f"Voice set to {self.voice_name} (ID: {self.voice_id})"
            else:
                return f"Invalid voice index. Choose between 1 and {len(self.available_voices)}"
        except ValueError:
            return "Please provide a valid number or voice ID"
    
    def toggle(self) -> str:
        """Toggle voice on/off with status feedback"""
        if not self.initialized:
            return "ElevenLabs not initialized"
        
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Voice {status} ({self.voice_name})"
    
    def speak(self, text: str) -> bool:
        """Convert text to speech and play it with better error handling"""
        if not self.initialized or not self.enabled or not text:
            return False
        
        try:
            audio = None
            
            # Generate audio
            if USE_NEW_API and self.client:
                # New API with client
                print(f"Generating speech using voice: {self.voice_name}")
                try:
                    audio_stream = self.client.text_to_speech.convert(
                        text=text,
                        voice_id=self.voice_id,
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128"
                    )
                    
                    # Check if result is a generator/stream and convert to bytes if needed
                    if not isinstance(audio_stream, bytes):
                        all_audio = bytearray()
                        for chunk in audio_stream:
                            if isinstance(chunk, bytes):
                                all_audio.extend(chunk)
                        audio = bytes(all_audio)
                    else:
                        audio = audio_stream
                    
                    if audio:
                        print(f"✓ Generated audio of size: {len(audio)} bytes")
                    else:
                        print("⚠️ No audio generated")
                        return False
                except Exception as e:
                    print(f"⚠️ Error generating speech: {str(e)}")
                    return False
            else:
                # Old API with direct function calls
                try:
                    from elevenlabs import generate, Models
                    audio = generate(
                        text=text,
                        voice=self.voice_id,
                        model=Models.ELEVEN_MULTILINGUAL_V2
                    )
                    if audio:
                        print(f"✓ Generated audio using legacy API")
                    else:
                        print("⚠️ No audio generated with legacy API")
                        return False
                except Exception as e:
                    print(f"⚠️ Error generating speech with legacy API: {str(e)}")
                    return False
            
            # Play the audio with various fallback options
            if PYGAME_AVAILABLE and audio:
                try:
                    # Save audio to a temporary file and play with pygame
                    temp_file = BytesIO(audio)
                    temp_file.seek(0)
                    
                    pygame.mixer.music.load(temp_file)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    return True
                except Exception as e:
                    print(f"⚠️ Error playing audio with Pygame: {str(e)}")
            
            # Try legacy playback if Pygame failed
            if not USE_NEW_API and audio:
                try:
                    from elevenlabs import play
                    play(audio)
                    return True
                except Exception as e:
                    print(f"⚠️ Error playing audio with legacy method: {str(e)}")
            
            # If we get here, we couldn't play the audio
            if audio:
                print("⚠️ Generated audio but couldn't play it. Try installing pygame: pip install pygame")
                return False
            else:
                print("⚠️ No audio generated to play")
                return False
                    
        except Exception as e:
            print(f"⚠️ Error in speak method: {str(e)}")
            return False

class SpeechListener:
    """Class to handle speech recognition with visual feedback"""
    
    def __init__(self):
        self.recognizer = None
        self.initialized = False
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize the speech recognizer"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return
            
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.initialized = True
            print("✓ Speech listener initialized")
        except Exception as e:
            print(f"⚠️ Error initializing speech listener: {str(e)}")
            self.initialized = False
    
    def listen(self, timeout: int = 10, phrase_time_limit: int = 15) -> Tuple[Optional[str], Optional[str]]:
        """
        Listen for speech with visual feedback and return the recognized text or error
        
        Args:
            timeout: Time to wait for speech to start
            phrase_time_limit: Maximum duration of speech to recognize
            
        Returns:
            tuple: (recognized_text, error_message)
        """
        if not self.initialized or not SPEECH_RECOGNITION_AVAILABLE:
            return None, "Speech recognition not initialized"
        
        import speech_recognition as sr
        
        try:
            with sr.Microphone() as source:
                print("\n🎤 Listening... (speak now)")
                print("═" * 20)
                
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Create a listening animation thread
                stop_animation = threading.Event()
                animation_thread = threading.Thread(
                    target=self._show_listening_animation, 
                    args=(stop_animation,)
                )
                animation_thread.daemon = True
                animation_thread.start()
                
                try:
                    # Listen for audio input
                    audio = self.recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_time_limit
                    )
                    # Stop the animation
                    stop_animation.set()
                    animation_thread.join(0.5)  # Wait for animation to stop
                    print("\nDone listening!")
                    print("═" * 20)
                except sr.WaitTimeoutError:
                    # Stop the animation
                    stop_animation.set()
                    animation_thread.join(0.5)
                    print("\n❌ Listening timed out. No speech detected.")
                    return None, "Listening timed out"
            
            print("🔍 Processing your speech...")
            
            try:
                # Use Google's speech recognition
                text = self.recognizer.recognize_google(audio)
                print(f"\n💬 You said: \"{text}\"")
                return text, None
            except sr.UnknownValueError:
                print("❌ Sorry, I couldn't understand what you said")
                return None, "Could not understand speech"
            except sr.RequestError as e:
                print(f"❌ Could not request results from Google Speech Recognition service; {e}")
                return None, f"Speech recognition service error: {e}"
        except Exception as e:
            error_msg = str(e)
            if "pyaudio" in error_msg.lower() or "check installation" in error_msg.lower():
                print("\n❌ PyAudio is not installed or configured properly.")
                print(ERROR_MESSAGES["pyaudio_install"])
                return None, f"PyAudio not installed: {error_msg}"
            else:
                print(f"❌ Error getting voice input: {e}")
                return None, f"Error: {error_msg}"
    
    def _show_listening_animation(self, stop_event: threading.Event) -> None:
        """Show a listening animation while waiting for speech"""
        animation = "|/-\\"
        idx = 0
        while not stop_event.is_set():
            print(f"\rListening {animation[idx % len(animation)]}", end="", flush=True)
            idx += 1
            time.sleep(0.1)

def get_clients():
    """Get the OpenAI and xAI clients"""
    from app import get_openai_client, get_xai_config
    return get_openai_client(), get_xai_config()

def process_user_query(
    user_query: str, 
    mock_session: MockSessionState, 
    conversation_history: Optional[List[Tuple[str, str]]] = None
) -> str:
    """
    Process a user query through the complete flow with improved error handling:
    1. OpenAI Categorization
    2. Google Gemini SQL Generation
    3. SQL Execution
    4. OpenAI Summarization
    
    Args:
        user_query: The user's query text
        mock_session: Session state with context
        conversation_history: Previous conversation exchanges
        
    Returns:
        str: The response to the user's query
    """
    if conversation_history is None:
        conversation_history = []
        
    try:
        # Setup clients and test query
        openai_client, _ = get_clients()  # We won't use xAI client
        
        # Step 1: OpenAI Categorization
        print("\n🧠 Categorizing your query...")
        try:
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_query}],
                functions=get_functions_list
            )
            
            function_call = categorization_response.choices[0].message.function_call
            if function_call:
                print(f"✓ Query identified as: {function_call.name}")
            else:
                print("ℹ️ Query could not be categorized into a specific function")
        except Exception as e:
            print(f"⚠️ Error during query categorization: {str(e)}")
            # Continue with SQL generation anyway
        
        # Step 2: SQL Generation
        print("\n🔍 Generating SQL query...")
        
        # Get previous SQL query context if available
        base_sql_query = mock_session.get("last_sql_query", None)
        
        try:
            # Generate SQL using the same approach as app.py
            sql_query = generate_sql_from_user_query(
                user_query, 
                mock_session.selected_location_id, 
                base_sql_query=base_sql_query
            )
            
            # Apply transformations
            sql_query = sql_query.replace("created_at", "updated_at")
            
            # Store the SQL query in session state
            mock_session["last_sql_query"] = sql_query
            
            # Format SQL query for display (remove newlines)
            formatted_sql = sql_query.strip().replace(chr(10), ' ')
            if len(formatted_sql) > 100:
                formatted_sql = formatted_sql[:97] + "..."
                
            print(f"✓ Generated SQL: {formatted_sql}")
            
        except Exception as e:
            print(f"⚠️ Error generating SQL: {str(e)}")
            return f"I'm having trouble generating a database query for your question. Please try rephrasing it or ask a different question. Error: {str(e)}"
        
        # Step 3: SQL Execution
        print("\n💾 Executing SQL query...")
        
        try:
            # Apply timezone adjustments
            sql_query = app.adjust_query_timezone(sql_query, mock_session.selected_location_id)
            
            # Execute the query
            result = app.execute_menu_query(sql_query)
            
            if result.get('success'):
                if result.get('results') and len(result['results']) > 0:
                    result_count = len(result['results'])
                    print(f"✓ Query executed successfully with {result_count} results.")
                    
                    # Show the first result
                    print(f"  First result: {result['results'][0]}")
                    
                    # Also print all people's names if it's a who query
                    if "who" in user_query.lower() and "first_name" in result['results'][0]:
                        names = [f"{r.get('first_name', '')} {r.get('last_name', '')}" for r in result['results']]
                        print(f"  All people: {names}")
                else:
                    print("✓ Query executed successfully, no results found.")
                    return "I couldn't find any data matching your query. Please try asking something else or rephrase your question."
            else:
                error = result.get('error', 'Unknown error')
                print(f"✗ SQL Execution Error: {error}")
                return f"I encountered an error executing your query: {error}. Please try rephrasing your question."
        except Exception as e:
            print(f"⚠️ Error executing SQL: {str(e)}")
            return f"I'm having trouble accessing the database. Error: {str(e)}. Please try again later."
        
        # Step 4: Summarize the results with OpenAI
        print("\n📝 Summarizing results...")
        
        try:
            # Create a context that includes conversation history
            context = ""
            if conversation_history:
                context = "Previous conversation:\n"
                # Include the most recent exchanges (up to 2)
                for i, (q, a) in enumerate(conversation_history[-2:]):
                    context += f"Q: {q}\nA: {a}\n\n"
            
            # Create a prompt for OpenAI that includes the user question and SQL results
            prompt = (
                f"{context}\n\n" if context else ""
                f"NEW QUESTION: {user_query}\n\n"
                f"DATABASE RESULTS:\n{json.dumps(result['results'], indent=2)}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Answer the NEW QUESTION above using ONLY the DATABASE RESULTS.\n"
                f"2. DO NOT repeat the previous answer.\n"
                f"3. Be specific and mention ALL data points from the results.\n"
                f"4. Format currency values with dollar signs ($).\n"
                f"5. If the results contain a 'count', clearly state that number in your answer.\n"
                f"6. If the question asks about dates or times, format them clearly.\n"
                f"7. Keep your answer concise but complete.\n"
            )
            
            print(f"  Prompt length: {len(prompt)} characters")
            
            # Make the OpenAI API call for summarization
            summarization_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a direct database assistant for a restaurant management system. Answer the NEW QUESTION using the database results provided. Be clear and specific with numbers and details."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Extract the summary from the response
            summary = summarization_response.choices[0].message.content
            
            print("✓ Summary generated")
            return summary
            
        except Exception as e:
            print(f"⚠️ Error summarizing results: {str(e)}")
            
            # Fallback: provide a basic response with the raw data
            try:
                if result.get('results') and len(result['results']) > 0:
                    return f"I found {len(result['results'])} results, but I'm having trouble summarizing them. Here's the first result: {result['results'][0]}"
                else:
                    return "I found no results matching your query."
            except:
                return "I processed your query but encountered an error when preparing the response. Please try again."
    
    except Exception as e:
        print(f"⚠️ Unexpected error in query processing: {str(e)}")
        traceback.print_exc()
        return f"I encountered an unexpected error processing your request: {str(e)}. Please try again."

def handle_voice_command(voice: ElevenLabsVoice, command: str) -> str:
    """
    Handle voice commands with improved command parsing
    
    Args:
        voice: The ElevenLabsVoice instance
        command: The command string starting with !voice
        
    Returns:
        str: Command result message
    """
    if not command.startswith("!voice"):
        return "Not a valid voice command"
        
    parts = command.split()
    if len(parts) < 2:
        return "Invalid voice command format"
    
    subcommand = parts[1].lower()
    
    # List all voices
    if subcommand == "list":
        return voice.list_voices()
    
    # Set voice by index or ID
    elif subcommand == "set" and len(parts) > 2:
        voice_id_or_index = ' '.join(parts[2:]) if len(parts) > 3 else parts[2]
        return voice.set_voice(voice_id_or_index)
    
    # Toggle voice on/off
    elif subcommand == "toggle":
        return voice.toggle()
    
    # Show voice info
    elif subcommand == "info":
        voice_name = voice.voice_name or next(
            (v.name for v in voice.available_voices if v.voice_id == voice.voice_id), 
            "Unknown"
        )
        return (
            f"Current voice: {voice_name}\n"
            f"Voice ID: {voice.voice_id}\n"
            f"Voice enabled: {voice.enabled}\n"
            f"Available voices: {len(voice.available_voices)}"
        )
    
    # Invalid command
    else:
        return "Invalid voice command. Use !voice list, !voice set [number or ID], !voice toggle, or !voice info"

def run_interactive_voice_chat():
    """
    Run an interactive voice chat session with the AI.
    This function creates a conversation where the AI asks questions and the user responds.
    """
    # Initialize session state and history
    mock_session = MockSessionState()
    conversation_history = []
    
    # Initialize voice components
    voice = ElevenLabsVoice()
    speech_listener = SpeechListener()
    
    # Determine if voice input is available
    voice_input_available = SPEECH_RECOGNITION_AVAILABLE and speech_listener.initialized
    
    # Display welcome header
    print("\n" + "="*50)
    print("🎤 Swoop AI")
    print("="*50)
    
    # Check voice input availability
    if voice_input_available:
        print("The AI will automatically listen for your voice input.")
        print("Type 'text' anytime to use keyboard input instead of voice for a turn.")
    else:
        print("Using text input mode.")
        if not SPEECH_RECOGNITION_AVAILABLE:
            print(ERROR_MESSAGES["speech_recognition_install"])
        elif not speech_listener.initialized:
            print("Speech recognition initialized but not working properly.")
            print(ERROR_MESSAGES["pyaudio_install"])
    
    print("Type 'exit', 'quit', or Ctrl+C to end the session.")
    
    # Display voice commands if available
    if ELEVENLABS_AVAILABLE and voice.initialized:
        print("\n🔊 Voice Commands:")
        print("  !voice list - List available voices")
        print("  !voice set [number or ID] - Set voice by number or voice ID")
        print("  !voice toggle - Turn voice on/off")
        print("  !voice info - Show current voice information")
        
        # Display current voice info
        print(f"\n🎤 Current voice: {voice.voice_name} (ID: {voice.voice_id})")
    
    print("="*50 + "\n")
    
    # Ensure voice is enabled if available
    if ELEVENLABS_AVAILABLE and voice.initialized and not voice.enabled:
        voice.toggle()
        
    # Display sample questions
    sample_questions = [
        "What are the most popular menu items this week?",
        "How many orders did we receive yesterday?",
        "What's the total revenue for this month?",
        "Who placed the largest order this week?",
        "Which staff member processed the most orders today?"
    ]
    
    print("📝 Sample questions you can ask:")
    for i, question in enumerate(sample_questions, 1):
        print(f"  {i}. {question}")
    print()
        
    # Welcome message
    welcome_message = "This is Swoop AI, How can I help you today?"
    print("\n🤖 Assistant: " + welcome_message)
    
    # Speak welcome message
    if voice.enabled:
        print("🔊 Speaking...")
        voice.speak(welcome_message)
    
    # Main conversation loop
    while True:
        try:
            # Get user input - use voice if available, otherwise text
            if voice_input_available:
                print("\n🎤 Listening for your voice input... (type 'text' anytime to switch to keyboard input)")
                
                # Check for text command first
                try:
                    # Use select to check if there's input before starting voice recognition
                    import msvcrt # Windows-specific
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8')
                        if key.lower() == 't':
                            print("\nSwitching to text input for this turn...")
                            user_query = input("\n💬 You (text input): ").strip()
                        else:
                            # Start with the first character typed
                            user_query = key + input().strip()
                    else:
                        # Default to voice input
                        user_query, error = speech_listener.listen()
                except (ImportError, Exception):
                    # Fallback if msvcrt isn't available (non-Windows) or other error
                    user_query, error = speech_listener.listen()
                
                # If voice input failed or returned empty, allow text fallback
                if not user_query:
                    print("No speech detected or recognition failed. You can type your input instead:")
                    user_query = input("\n💬 You (text fallback): ").strip()
            else:
                # Regular text input if speech recognition is not available
                user_query = input("\n💬 You: ").strip()
            
            # Check for direct text input command
            if user_query.lower() == 'text':
                user_query = input("\n💬 You (text input): ").strip()
            
            # Check for exit command
            if user_query.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                goodbye_message = "Thank you for chatting with me. Have a great day!"
                print("\n🤖 Assistant: " + goodbye_message)
                if voice.enabled:
                    voice.speak(goodbye_message)
                break
            
            # Check for voice commands
            if user_query.startswith("!voice"):
                result = handle_voice_command(voice, user_query)
                print(f"\n🔊 {result}")
                continue
            
            # Skip empty queries
            if not user_query:
                print("Please say or type something.")
                continue
            
            # Process the query and get response
            try:
                print("\n⏳ Checking...")
                response = process_user_query(user_query, mock_session, conversation_history)
            except Exception as e:
                print(f"⚠️ Error processing query: {str(e)}")
                response = f"I'm having trouble processing that query. Error: {str(e)}. Could you try asking something else?"
            
            # Display the response
            print("\n🤖 Assistant: " + response)
            
            # Speak the response if voice is enabled
            if voice.enabled:
                print("🔊 Speaking...")
                voice.speak(response)
            
            # Save to conversation history
            conversation_history.append((user_query, response))
            
            # Use contextual follow-up based on conversation length
            if len(conversation_history) < 5:
                try:
                    # Choose from a variety of follow-up questions for more natural conversation
                    follow_up_options = [
                        "What else would you like to know?",
                        "Is there anything else you'd like to ask about?",
                        "Do you have any other questions about the restaurant?",
                        "What other information would be helpful?",
                        "Is there something specific you'd like to learn more about?"
                    ]
                    follow_up = random.choice(follow_up_options)
                    
                    print("\n🤖 Assistant: " + follow_up)
                    if voice.enabled:
                        print("🔊 Speaking...")
                        voice.speak(follow_up)
                    
                except Exception as e:
                    print(f"\n⚠️ Error generating follow-up: {str(e)}")
                    # If we fail to generate a follow-up, move on silently
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n⚠️ An error occurred: {str(e)}")
            print("Let's try again with a different question.")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("💬 Starting Interactive Voice Chat...")
    print("="*50)
    
    # Initialize dependencies
    status = initialize_dependencies()
    
    # Run the voice chat version
    try:
        run_interactive_voice_chat()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError running voice chat: {str(e)}")
        traceback.print_exc()
        
    print("\nScript completed. Goodbye!")