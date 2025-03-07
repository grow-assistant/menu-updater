import streamlit as st
from elevenlabs import generate, play, set_api_key

# Replace these with your actual ElevenLabs API key and voice ID
API_KEY = "sk_6b0386660b88145b59fdd5b2dfa5a8da5e817484542dee64"
VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"

# Set up the Streamlit app title
st.title("Text-to-Speech with ElevenLabs")

# Define the test text to convert to speech
text = "Hello, this is a test voice."

# Set the API key
set_api_key(API_KEY)

# Generate the audio using the ElevenLabs API
audio = generate(
    text=text,
    voice=VOICE_ID,
    model="eleven_monolingual_v1"
)

# Save the audio to a file that Streamlit can access
import tempfile
import os

# Create a temporary file
temp_dir = tempfile.gettempdir()
audio_file = os.path.join(temp_dir, "test_audio.mp3")

# Save the audio to the temporary file
with open(audio_file, "wb") as f:
    f.write(audio)

# Use Streamlit's audio component to play the audio
st.audio(audio_file, format="audio/mp3", autoplay=True)

# Remove the HTML audio player since we're already using Streamlit's native audio component
# The HTML version was causing errors with binary data encoding