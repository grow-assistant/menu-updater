# Debugging Guide for AI Menu Updater

This guide provides information on how to debug issues with the AI Menu Updater application, particularly focused on AI API calls and Text-to-Speech (TTS) functionality.

## Log Files

The application creates the following log files:

- `logs/app.log` - Main application logs
- `logs/api_calls/*.log` - Detailed logs of all AI API calls (OpenAI, ElevenLabs)
- `logs/tts_debug.log` - Specialized TTS debugging information
- `logs/ai_prompts/` - Contains detailed logs of the prompts sent to OpenAI

## Debugging Scripts

### API Call Analysis

The `scripts/analyze_api_logs.py` script analyzes all API calls to identify patterns and issues:

```bash
python scripts/analyze_api_logs.py --days 1
```

This will show:
- General API call metrics
- Success/failure rates
- Most common errors
- Verbal response specific analysis

### TTS Debugging

If you're seeing "No verbal response was generated" messages, use the TTS debugging script:

```bash
python scripts/debug_tts.py
```

This script tests:
1. ElevenLabs API directly
2. TTS through the orchestrator
3. ResponseGenerator initialization and verbal response generation

## Common Issues

### "No verbal response was generated"

This message occurs in the logs when the application decides not to generate a verbal (audio) response. Based on our investigation, this can happen for the following reasons:

1. **Fast mode is enabled**: When `fast_mode=True`, verbal responses are skipped for performance
   - Solution: Set `context["enable_verbal"] = True` when calling `process_query`
   - This will override the fast_mode setting (see line 105-106 in services/orchestrator/orchestrator.py)

2. **ElevenLabs is not initialized**:
   - Check if `elevenlabs` package is installed: `pip install elevenlabs`
   - Check if ElevenLabs API key is configured in config.yaml or .env file
   - Run `debug_tts.py` to validate ElevenLabs functionality

3. **TTS is disabled in configuration**:
   - Check if `features.enable_tts` is set to `true` in your config.yaml
   - We've added this feature flag to the configuration, make sure it's present

4. **Environment variable substitution failed**:
   - If you see `${OPENAI_API_KEY}` or `${ELEVENLABS_API_KEY}` in error messages, it means the environment variables aren't being properly substituted
   - Follow the guide in docs/environment_variables.md to properly set up your .env file

5. **Invalid or missing OpenAI API key**:
   - The verbal text generation requires a valid OpenAI API key to work
   - Check if you're getting 401 errors ("Incorrect API key provided")
   - Verify your OpenAI API key is correctly set in your .env file or environment

You can diagnose these issues by running the TTS debugging script:

```bash
python scripts/debug_tts.py
```

And check the logs at `logs/tts_debug.log` for detailed diagnostics.

### OpenAI API Issues

If you're seeing errors with OpenAI API calls:

1. Check if your API key is valid and has sufficient credits
2. Inspect the detailed logs in `logs/api_calls/` for specific error messages
3. Look at the prompts in `logs/ai_prompts/` to ensure they're properly formatted

## Running the Application

Always run the application with Streamlit:

```bash
streamlit run main.py
```

Do not use `python main.py` directly, as this will cause Streamlit warning messages.

## Getting More Detailed Logs

To increase log verbosity, modify the logging configuration in `main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
``` 