# Audio Input Testing Tools

This directory contains tools to help you test your audio input (microphone) functionality for the Swoop AI application.

## Available Test Tools

1. **Streamlit Test** (`test_audio_input.py`): A graphical interface using Streamlit to test your audio configuration.
2. **Command Line Test** (`test_audio_cli.py`): A simpler command-line tool that doesn't require Streamlit.

## Prerequisites

Before running these tests, you need to install the required packages:

```bash
pip install SpeechRecognition PyAudio streamlit
```

### Common PyAudio Installation Issues

PyAudio can be tricky to install on some systems. If you encounter errors, try these platform-specific commands:

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install python3-pyaudio
```

## Running the Tests

### Streamlit Test

The Streamlit version provides a more interactive interface with expandable troubleshooting sections:

```bash
streamlit run test_audio_input.py
```

This will open a web browser with the test interface where you can:
- Check if required libraries are installed
- View available audio input devices
- Test speech recognition
- Access detailed troubleshooting information

### Command Line Test

For a quicker test without needing to start a web server:

```bash
python test_audio_cli.py
```

This will run through the same tests in your terminal with colored output (where supported).

## What These Tests Check

Both tools check for:

1. **Library Installation**: Verifies if SpeechRecognition and PyAudio are properly installed
2. **Microphone Access**: Checks if your system's microphone can be accessed by Python
3. **Audio Devices**: Lists available audio input devices
4. **Speech Recognition**: Tests if your microphone can pick up your voice and convert it to text

## Troubleshooting

If you encounter issues, both tools provide troubleshooting suggestions for:
- PyAudio installation problems
- Microphone detection issues
- Speech recognition failures
- Alternative speech recognition engines

## Integration with Swoop AI

Once you confirm your audio input is working correctly, you can integrate it with the Swoop AI application.

The main application uses the same underlying libraries:
- `speech_recognition` for detecting and transcribing speech
- `PyAudio` for accessing your microphone

---

If issues persist after trying the suggestions, please check your system's audio settings to ensure your microphone is properly configured and has necessary permissions. 