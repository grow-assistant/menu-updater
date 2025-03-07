# Enhanced Logging System

This document provides information about the enhanced logging system implemented for the AI Menu Updater application, which helps debug issues related to AI API calls.

## Overview

We've implemented a comprehensive logging system that captures detailed information about all AI API calls, with a particular focus on diagnosing the "No verbal response was generated" issue.

## Logging Features

The enhanced logging system includes:

1. **API Call Tracking**
   - Unique ID for each API call
   - Request details (parameters, model, etc.)
   - Response details (tokens, audio bytes, etc.)
   - Performance metrics (duration, success/failure)

2. **TTS-Specific Logging**
   - ElevenLabs API integration details
   - Verbal text generation process
   - Voice selection and TTS model parameters

3. **Analysis Tools**
   - API call statistics and patterns
   - Error rate analysis
   - Performance bottleneck identification

## Log Files

The system generates the following log files:

- `logs/app.log` - Main application logs
- `logs/api_calls/api_calls_YYYYMMDD.log` - JSON-formatted logs of all API calls
- `logs/ai_prompts/openai_response_*.log` - Detailed logs of prompts and responses
- `logs/tts_debug.log` - TTS debugging information

## Debugging "No verbal response was generated" Issue

The "No verbal response was generated" message appears in the logs when the application skips generating a verbal (audio) response. Based on our investigation, this can happen for several reasons:

1. **Fast mode is enabled** - Verbal responses are skipped for performance
2. **TTS is disabled in configuration** - The `features.enable_tts` flag is not set to `true`
3. **Environment variable substitution failed** - API keys are not properly loaded
4. **Invalid OpenAI API key** - The verbal text generation step fails

See `docs/debug_guide.md` for complete troubleshooting steps.

## Utilities and Tools

### API Call Analysis Script

The `scripts/analyze_api_logs.py` script analyzes the API call logs to identify patterns and issues:

```bash
python scripts/analyze_api_logs.py --days 1
```

This shows:
- Total API calls and success rates
- Most common errors
- Slowest API calls
- Verbal response specific analysis

### TTS Debugging Script

The `scripts/debug_tts.py` script provides comprehensive diagnostics for TTS functionality:

```bash
python scripts/debug_tts.py
```

This tests:
1. ElevenLabs API directly (key validation, voice listing, audio generation)
2. Orchestrator's TTS functionality
3. ResponseGenerator's verbal response generation

## Implementation Details

The enhanced logging is implemented in:

1. **ResponseGenerator** (`services/response/response_generator.py`)
   - Added `_log_api_call` method to log API calls
   - Enhanced error handling with detailed messages
   - Added API call tracking statistics

2. **Orchestrator** (`services/orchestrator/orchestrator.py`)
   - Added detailed logging around ElevenLabs initialization
   - Enhanced debugging for verbal response generation
   - Added specific error messages for each potential issue

3. **Configuration** (`config/config.yaml`)
   - Added explicit `features.enable_tts` flag
   - Added documentation about environment variable usage

## Using the Logs for Debugging

To diagnose issues with the application:

1. Check `logs/app.log` for high-level error messages
2. Run `python scripts/analyze_api_logs.py` to get an overview of API call patterns
3. If TTS issues are suspected, run `python scripts/debug_tts.py`
4. Check `logs/api_calls/*.log` for detailed API call information
5. Review environment variable setup using the guidance in `docs/environment_variables.md`

## Future Improvements

Potential improvements to the logging system include:

1. Centralized log aggregation and search
2. Real-time monitoring dashboard
3. Automatic error alerting
4. Long-term trend analysis 