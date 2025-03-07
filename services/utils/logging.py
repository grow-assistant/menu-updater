# Standard library imports
import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

# Set up logging configuration
logger = logging.getLogger("swoop_ai")

def get_log_file_path(base_dir: str = "logs") -> str:
    """
    Generate a log file path for the current session.
    
    Args:
        base_dir: Base directory for logs
        
    Returns:
        str: Path to the log file
    """
    # Create a session ID for this run
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ensure logs directory exists
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    
    # Create a session-specific directory
    session_dir = os.path.join(base_dir, f"session_{session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Return the main log file path
    return os.path.join(session_dir, "app_main.log")

def clean_old_logs(base_dir: str = "logs", max_sessions: int = 10) -> None:
    """
    Clean up old log sessions to prevent disk space issues.
    
    Args:
        base_dir: Base directory for logs
        max_sessions: Maximum number of session directories to keep
    """
    if not os.path.exists(base_dir):
        return
        
    # Get all session directories
    session_dirs = [
        d for d in Path(base_dir).iterdir() 
        if d.is_dir() and d.name.startswith("session_")
    ]
    
    # If we have more than max_sessions, remove the oldest ones
    if len(session_dirs) > max_sessions:
        # Sort by creation time
        session_dirs.sort(key=lambda d: d.stat().st_mtime)
        # Remove oldest sessions
        for old_dir in session_dirs[:-max_sessions]:
            try:
                for file in old_dir.glob("*"):
                    file.unlink()
                old_dir.rmdir()
                logger.info(f"Removed old log session: {old_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove old log session {old_dir}: {e}")

class ModuleFilter(logging.Filter):
    """Filter that only allows logs from a specific module"""
    
    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name
        
    def filter(self, record):
        """
        Filter logs based on the module filename.
        This checks if the record's pathname ends with the module name.
        """
        if hasattr(record, 'pathname') and isinstance(record.pathname, str):
            filename = os.path.basename(record.pathname)
            return filename == self.module_name
        return False

def setup_logging(
    log_level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Set up logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format for log messages
        log_file: Path to log file
    """
    # Create a session ID for this run if log_file is not provided
    if not log_file:
        log_file = get_log_file_path()
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Set default log format if not provided
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Create console handler with a higher level to reduce console noise
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(max(numeric_level, logging.INFO))  # At least INFO for console
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # Create file handler if log file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)

    # Configure application-specific logger
    app_logger = logging.getLogger("swoop_ai")
    app_logger.setLevel(numeric_level)
    
    # Suppress verbose logging from external libraries
    for module in ["comtypes", "httpcore", "httpx"]:
        logging.getLogger(module).setLevel(logging.WARNING)
        
    app_logger.info(f"Logging initialized at level {log_level}")
    app_logger.info(f"Log file: {log_file}")

def setup_ai_api_logging():
    """
    Set up specialized logging for AI API calls.
    Creates separate log files for different AI services.
    """
    session_dirs = [d for d in Path("logs").iterdir() if d.is_dir() and d.name.startswith("session_")]
    if not session_dirs:
        logger.error("No log session directories found. Please call setup_logging() first.")
        return
        
    # Get the latest session directory
    latest_session_dir = sorted(session_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    logger.info(f"Setting up AI API logging in session directory: {latest_session_dir}")
    
    # Configure OpenAI logger
    openai_logger = logging.getLogger("openai_categorization")
    openai_logger.setLevel(logging.INFO)
    # Prevent propagation to parent loggers
    openai_logger.propagate = False
    # Remove any existing handlers
    openai_logger.handlers = []
    openai_log_path = os.path.join(latest_session_dir, "openai_categorization.log")
    openai_handler = logging.FileHandler(openai_log_path)
    openai_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    openai_logger.addHandler(openai_handler)
    # Add test log message
    openai_logger.info("OpenAI logger initialized")
    logger.info(f"OpenAI logger configured: {openai_log_path}")
    
    # Configure Gemini logger
    gemini_logger = logging.getLogger("google_gemini")
    gemini_logger.setLevel(logging.INFO)
    # Prevent propagation to parent loggers
    gemini_logger.propagate = False
    # Remove any existing handlers
    gemini_logger.handlers = []
    gemini_log_path = os.path.join(latest_session_dir, "google_gemini.log")
    gemini_handler = logging.FileHandler(gemini_log_path)
    gemini_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    gemini_logger.addHandler(gemini_handler)
    # Add test log message
    gemini_logger.info("Google Gemini logger initialized")
    logger.info(f"Google Gemini logger configured: {gemini_log_path}")
    
    # Configure summarization logger
    summary_logger = logging.getLogger("summarization")
    summary_logger.setLevel(logging.INFO)
    # Prevent propagation to parent loggers
    summary_logger.propagate = False
    # Remove any existing handlers
    summary_logger.handlers = []
    summary_log_path = os.path.join(latest_session_dir, "summarization.log")
    summary_handler = logging.FileHandler(summary_log_path)
    summary_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    summary_logger.addHandler(summary_handler)
    # Add test log message
    summary_logger.info("Summarization logger initialized")
    logger.info(f"Summarization logger configured: {summary_log_path}")
    
    logger.info(f"AI API logging configured for session: {latest_session_dir.name}")

def log_openai_request(prompt: str, parameters: Dict[str, Any] = None, context: Optional[str] = None):
    """Log an OpenAI API request"""
    openai_logger = logging.getLogger("openai_categorization")
    openai_logger.info("OpenAI API REQUEST")
    openai_logger.info(f"PROMPT: {prompt}")
    if parameters:
        openai_logger.info(f"PARAMETERS: {json.dumps(parameters, default=str)}")
    if context:
        openai_logger.info(f"CONTEXT: {context}")
    openai_logger.info("-" * 50)
    # Force flush handlers
    for handler in openai_logger.handlers:
        handler.flush()

def log_openai_response(response: Any, processing_time: float = None):
    """Log an OpenAI API response"""
    openai_logger = logging.getLogger("openai_categorization")
    openai_logger.info("OpenAI API RESPONSE")
    try:
        openai_logger.info(f"RESPONSE: {json.dumps(response, default=str)}")
    except:
        openai_logger.info(f"RESPONSE: {str(response)}")
    if processing_time:
        openai_logger.info(f"PROCESSING TIME: {processing_time:.2f} seconds")
    openai_logger.info("=" * 50)
    # Force flush handlers
    for handler in openai_logger.handlers:
        handler.flush()

def log_gemini_request(prompt: str, parameters: Dict[str, Any] = None, context: Optional[str] = None):
    """Log a Google Gemini API request"""
    gemini_logger = logging.getLogger("google_gemini")
    gemini_logger.info("GEMINI API REQUEST")
    gemini_logger.info(f"PROMPT: {prompt}")
    if parameters:
        gemini_logger.info(f"PARAMETERS: {json.dumps(parameters, default=str)}")
    if context:
        gemini_logger.info(f"CONTEXT: {context}")
    gemini_logger.info("-" * 50)
    # Force flush handlers
    for handler in gemini_logger.handlers:
        handler.flush()

def log_gemini_response(response: Any, processing_time: float = None):
    """Log a Google Gemini API response"""
    gemini_logger = logging.getLogger("google_gemini")
    gemini_logger.info("GEMINI API RESPONSE")
    try:
        gemini_logger.info(f"RESPONSE: {json.dumps(response, default=str)}")
    except:
        gemini_logger.info(f"RESPONSE: {str(response)}")
    if processing_time:
        gemini_logger.info(f"PROCESSING TIME: {processing_time:.2f} seconds")
    gemini_logger.info("=" * 50)
    # Force flush handlers
    for handler in gemini_logger.handlers:
        handler.flush()

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Optional name for the logger (usually __name__)
        
    Returns:
        A Logger instance
    """
    if name:
        return logging.getLogger(f"swoop_ai.{name}")
    return logger

# Initialize logging with default settings
setup_logging()

# Clean old logs on startup
clean_old_logs()

# Export the commonly used functions
__all__ = [
    "logger", 
    "setup_logging", 
    "get_log_file_path", 
    "clean_old_logs", 
    "setup_ai_api_logging",
    "log_openai_request",
    "log_openai_response",
    "log_gemini_request",
    "log_gemini_response",
    "get_logger"
] 