"""
Voice and speech recognition services for the Streamlit app.

This module provides voice synthesis and speech recognition capabilities.
"""

import os
import time
import logging
import re
import threading
import io
from typing import Optional, Dict, Any, Callable

# Configure logger
logger = logging.getLogger("ai_menu_updater")

class SimpleVoice:
    """Simple voice class that avoids complex imports"""

    def __init__(self, persona="casual", **kwargs):
        self.enabled = True
        self.initialized = True
        self.persona = persona

        # Get persona info from configuration
        from prompts.personas import get_persona_info
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]

        logger.info(f"Initialized SimpleVoice with persona: {persona}")

    def clean_text_for_speech(self, text):
        """Clean text to make it more suitable for speech synthesis"""
        import re
        
        # Try to import inflect, but make it optional
        try:
            import inflect
            p = inflect.engine()
            
            # Dictionary of special cases for common ordinals
            ordinal_words = {
                1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
                6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
                11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 
                15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 
                19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fortieth",
                50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth", 
                90: "ninetieth", 100: "hundredth", 1000: "thousandth"
            }
            
            # Function to convert ordinal numbers to words
            def replace_ordinal(match):
                # Extract the number part (e.g., "21" from "21st")
                num = int(match.group(1))
                suffix = match.group(2)  # st, nd, rd, th
                
                # Check for special cases first
                if num in ordinal_words:
                    return ordinal_words[num]
                
                # For numbers 21-99 that aren't in our special cases
                if 21 <= num < 100:
                    tens = (num // 10) * 10
                    ones = num % 10
                    
                    if ones == 0:  # For 30, 40, 50, etc.
                        return ordinal_words[tens]
                    else:
                        # Convert the base number to words (e.g., 21 -> twenty-one)
                        base_word = p.number_to_words(num)
                        
                        # If ones digit has a special ordinal form
                        if ones in ordinal_words:
                            # Replace last word with its ordinal form
                            base_parts = base_word.split("-")
                            if len(base_parts) > 1:
                                return f"{base_parts[0]}-{ordinal_words[ones]}"
                            else:
                                return ordinal_words[ones]
                
                # For other numbers, fallback to converting to words then adding suffix
                word_form = p.number_to_words(num)
                return word_form
            
            # Replace ordinal numbers (1st, 2nd, 3rd, 21st, etc.) with word equivalents
            text = re.sub(r'(\d+)(st|nd|rd|th)', replace_ordinal, text)
        except ImportError:
            # If inflect is not available, we'll skip the ordinal conversion
            pass
        
        # Remove markdown formatting
        # Replace ** and * (bold and italic) with nothing
        text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)

        # Remove markdown bullet points and replace with natural pauses
        text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)

        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Replace newlines with spaces to make it flow better in speech
        text = re.sub(r"\n+", " ", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # Replace common abbreviations with full words
        text = text.replace("vs.", "versus")
        text = text.replace("etc.", "etcetera")
        text = text.replace("e.g.", "for example")
        text = text.replace("i.e.", "that is")

        # Improve speech timing with commas for complex sentences
        text = re.sub(
            r"(\d+)([a-zA-Z])", r"\1, \2", text
        )  # Put pauses after numbers before words

        # Add a pause after periods that end sentences
        text = re.sub(r"\.(\s+[A-Z])", r". \1", text)

        return text

    def speak(self, text):
        """Speak the given text using ElevenLabs API"""
        if not text:
            return False

        # Clean the text for better speech synthesis
        text = self.clean_text_for_speech(text)

        try:
            # Try to use a simple direct approach with elevenlabs
            try:
                # Simplified approach with minimal imports
                import os
                from dotenv import load_dotenv
                import requests
                import pygame
                from io import BytesIO
                import time

                # Load API key
                load_dotenv()
                api_key = os.getenv("ELEVENLABS_API_KEY")

                if not api_key:
                    raise ValueError("No ElevenLabs API key found")

                # Make direct API call to ElevenLabs
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": api_key,
                }

                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                }

                # Generate speech without showing any messages
                response = requests.post(url, json=data, headers=headers)

                if response.status_code != 200:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text}"
                    )

                # Get audio data
                audio_data = BytesIO(response.content)

                # Play with pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                return True

            except Exception as e:
                # Log error but continue
                logger.error(f"Direct API attempt failed: {str(e)}")
                raise

        except Exception as e:
            # Log error but don't display to user
            logger.error(f"Voice error: {str(e)}")
            return False

    def toggle(self):
        """Toggle voice on/off"""
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Voice {status}"

    def change_persona(self, persona):
        """Change the voice persona"""
        self.persona = persona
        # Get persona info from configuration
        from prompts.personas import get_persona_info
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]
        return f"Changed to {persona} voice"

# For backward compatibility
ElevenLabsVoice = SimpleVoice

def initialize_voice_service(persona="casual"):
    """
    Initialize the voice service with the specified persona
    
    Args:
        persona: Voice persona to use (default: casual)
        
    Returns:
        SimpleVoice: Initialized voice instance
    """
    try:
        voice = SimpleVoice(persona=persona)
        if voice.initialized:
            logger.info(f"Voice service initialized with persona: {persona}")
            return voice
        else:
            logger.warning("Voice service initialization failed")
            return None
    except Exception as e:
        logger.error(f"Error initializing voice service: {str(e)}")
        return None

def recognize_speech_with_timeout(timeout=5, phrase_time_limit=15):
    """
    Capture audio from the microphone and convert it to text with a custom timeout.

    Args:
        timeout: Time to wait before stopping if no speech is detected
        phrase_time_limit: Maximum duration of speech to recognize

    Returns:
        str: Recognized text, or empty string if recognition failed
    """
    try:
        import speech_recognition as sr

        # Create a recognizer instance
        recognizer = sr.Recognizer()

        # Capture audio from the microphone
        with sr.Microphone() as source:
            logger.info("Recording started")

            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            # Capture audio with the specified timeout
            try:
                logger.info(f"Listening... (timeout: {timeout}s)")
                audio = recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            except sr.WaitTimeoutError:
                logger.info("No speech detected within timeout period")
                return ""

            # Try to recognize the speech
            try:
                logger.info("Processing speech...")
                # Use Google's speech recognition
                text = recognizer.recognize_google(audio)
                logger.info(f"Speech recognized: {text}")
                return text
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"Speech recognition service error: {e}")
                return ""

    except ImportError:
        logger.error("Speech recognition library not installed")
        return ""
    except Exception as e:
        logger.error(f"Error during speech recognition: {e}")
        return ""

def background_speech_recognition(callback=None, timeout=5):
    """
    Run speech recognition in a background thread with timeout
    
    Args:
        callback: Function to call with the recognized text
        timeout: Timeout in seconds
        
    Returns:
        thread: The background thread object
    """
    def recognition_thread():
        text = recognize_speech_with_timeout(timeout=timeout)
        if text and callback:
            callback(text)
    
    thread = threading.Thread(target=recognition_thread)
    thread.daemon = True
    thread.start()
    
    return thread 