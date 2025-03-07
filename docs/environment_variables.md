# Environment Variables Setup Guide

This document explains how to properly set up environment variables for the AI Menu Updater application.

## Environment Variable Configuration

The application uses environment variables for sensitive configuration values like API keys and database credentials. You have two options for setting these variables:

### Option 1: .env File (Recommended)

Create a `.env` file in the project root with the following variables:

```
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# ElevenLabs API (Text-to-Speech)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Database Configuration
DB_CONNECTION_STRING=postgresql://user:password@localhost:5432/dbname
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_db_name

# Application Settings
DEFAULT_LOCATION_ID=1
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.7
DEFAULT_PERSONA=casual
LOG_LEVEL=INFO
```

### Option 2: System Environment Variables

Set these variables directly in your system's environment:

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY = "your_openai_api_key_here"
$env:ELEVENLABS_API_KEY = "your_elevenlabs_api_key_here"
# Add other variables similarly
```

**Bash (Linux/Mac):**
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
# Add other variables similarly
```

## API Keys

### OpenAI API Key

You need an OpenAI API key to use the language model capabilities:

1. Visit https://platform.openai.com/account/api-keys
2. Sign in or create an account
3. Create a new API key
4. Add the key to your environment variables

### ElevenLabs API Key (Text-to-Speech)

For verbal responses using ElevenLabs:

1. Visit https://elevenlabs.io/app
2. Sign in or create an account
3. Go to your profile settings to find your API key
4. Add the key to your environment variables

## Troubleshooting Environment Variables

If you see errors like the following:

```
Error code: 401 - {'error': {'message': 'Incorrect API key provided: ${OPENAI*****KEY}
```

It means the application is not properly substituting environment variables in the configuration. Check the following:

1. Verify your `.env` file exists in the root directory
2. Ensure the variable names match exactly what's in the config file
3. Make sure there are no spaces around the `=` sign in the `.env` file
4. Restart the application after making changes

## Debugging Tips

To debug environment variable issues:

1. Run the TTS debug script: `python scripts/debug_tts.py`
2. Check the API key configuration with: `python -c "import os; print('OPENAI_API_KEY set:', bool(os.environ.get('OPENAI_API_KEY'))); print('ELEVENLABS_API_KEY set:', bool(os.environ.get('ELEVENLABS_API_KEY')))"`
3. Verify the variables are actually loaded by adding print statements in your code 