"""
Enhanced Error Handler for Swoop AI Conversational Query Flow.

This module provides a centralized error handling system with:
- Standardized error types and error codes
- Contextual error messages with recovery suggestions
- Detailed error logging
- Error tracking and metrics
"""
import logging
import traceback
import inspect
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Callable, Type, Union
from functools import wraps

logger = logging.getLogger(__name__)

# Define standard error types
class ErrorTypes:
    """Standard error types across the application."""
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    PARSING_ERROR = "parsing_error"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    RESOURCE_ERROR = "resource_error"
    INTERNAL_ERROR = "internal_error"
    INPUT_ERROR = "input_error"
    CONFIGURATION_ERROR = "configuration_error"
    
    # More specific AI workflow errors
    CLASSIFICATION_ERROR = "classification_error"
    ENTITY_RESOLUTION_ERROR = "entity_resolution_error"
    TEMPORAL_ANALYSIS_ERROR = "temporal_analysis_error"
    SQL_GENERATION_ERROR = "sql_generation_error"
    SQL_EXECUTION_ERROR = "sql_execution_error"
    CONTEXT_ERROR = "context_error"
    ACTION_ERROR = "action_error"
    RESPONSE_GENERATION_ERROR = "response_generation_error"

class ErrorHandler:
    """
    Centralized error handler for the Swoop AI system.
    
    Features:
    - Standardized error formatting
    - Error metrics collection
    - Recovery suggestion generation
    - Context-aware error details
    """
    
    # Default recovery suggestions by error type
    DEFAULT_RECOVERY_SUGGESTIONS = {
        ErrorTypes.DATABASE_ERROR: "Please try again in a moment. If the problem persists, contact support.",
        ErrorTypes.VALIDATION_ERROR: "Please check your input and try again with valid parameters.",
        ErrorTypes.AUTHENTICATION_ERROR: "Your session may have expired. Please log in again.",
        ErrorTypes.AUTHORIZATION_ERROR: "You don't have permission to perform this action. Please contact an administrator.",
        ErrorTypes.NOT_FOUND_ERROR: "The requested resource could not be found. Please verify and try again.",
        ErrorTypes.PARSING_ERROR: "I couldn't understand that request. Could you rephrase it?",
        ErrorTypes.TIMEOUT_ERROR: "The operation took too long to complete. Please try a simpler query or try again later.",
        ErrorTypes.NETWORK_ERROR: "There was a network issue. Please check your connection and try again.",
        ErrorTypes.EXTERNAL_SERVICE_ERROR: "A service we depend on is currently unavailable. Please try again later.",
        ErrorTypes.RESOURCE_ERROR: "The system doesn't have enough resources to complete this request. Please try again later.",
        ErrorTypes.INTERNAL_ERROR: "An internal error occurred. Our team has been notified.",
        ErrorTypes.INPUT_ERROR: "There was an issue with your input. Please try again with different parameters.",
        ErrorTypes.CONFIGURATION_ERROR: "There is a configuration issue. Please contact support.",
        
        # AI workflow specific suggestions
        ErrorTypes.CLASSIFICATION_ERROR: "I had trouble understanding your request. Could you rephrase it?",
        ErrorTypes.ENTITY_RESOLUTION_ERROR: "I couldn't identify some items in your request. Could you clarify what you're looking for?",
        ErrorTypes.TEMPORAL_ANALYSIS_ERROR: "I had trouble understanding the time period you mentioned. Could you specify the dates more clearly?",
        ErrorTypes.SQL_GENERATION_ERROR: "I couldn't convert your question into a database query. Could you rephrase it?",
        ErrorTypes.SQL_EXECUTION_ERROR: "There was an issue running your query against the database. Please try a different query.",
        ErrorTypes.CONTEXT_ERROR: "I lost track of our conversation context. Could you provide more details?",
        ErrorTypes.ACTION_ERROR: "I couldn't perform that action. Please check the details and try again.",
        ErrorTypes.RESPONSE_GENERATION_ERROR: "I had trouble generating a response. Please try again."
    }
    
    # Error HTTP status codes
    ERROR_STATUS_CODES = {
        ErrorTypes.DATABASE_ERROR: 503,
        ErrorTypes.VALIDATION_ERROR: 400,
        ErrorTypes.AUTHENTICATION_ERROR: 401,
        ErrorTypes.AUTHORIZATION_ERROR: 403,
        ErrorTypes.NOT_FOUND_ERROR: 404,
        ErrorTypes.PARSING_ERROR: 400,
        ErrorTypes.TIMEOUT_ERROR: 504,
        ErrorTypes.NETWORK_ERROR: 503,
        ErrorTypes.EXTERNAL_SERVICE_ERROR: 502,
        ErrorTypes.RESOURCE_ERROR: 503,
        ErrorTypes.INTERNAL_ERROR: 500,
        ErrorTypes.INPUT_ERROR: 400,
        ErrorTypes.CONFIGURATION_ERROR: 500
    }
    
    def __init__(self):
        """Initialize the error handler."""
        self.error_counts = {error_type: 0 for error_type in dir(ErrorTypes) 
                           if not error_type.startswith('__')}
        self.last_errors = {}
        self.error_timestamps = []
    
    def handle_error(self, 
                   error: Exception, 
                   error_type: str = ErrorTypes.INTERNAL_ERROR,
                   context: Optional[Dict[str, Any]] = None,
                   recovery_suggestion: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle an exception and format it into a standardized error response.
        
        Args:
            error: The exception that occurred
            error_type: The type of error (use ErrorTypes constants)
            context: Additional context about the error
            recovery_suggestion: Custom recovery suggestion to override default
            
        Returns:
            Formatted error response dictionary
        """
        # Set defaults for missing parameters
        if context is None:
            context = {}
        
        # Get the caller information
        caller_info = self._get_caller_info()
        
        # Update error metrics
        self._update_error_metrics(error_type)
        
        # Determine stack trace (limit to 10 levels for readability)
        stack_trace = traceback.format_exc().split('\n')[:10]
        
        # Get default recovery suggestion if not provided
        if recovery_suggestion is None:
            recovery_suggestion = self.DEFAULT_RECOVERY_SUGGESTIONS.get(
                error_type, 
                self.DEFAULT_RECOVERY_SUGGESTIONS[ErrorTypes.INTERNAL_ERROR]
            )
        
        # Get HTTP status code
        status_code = self.ERROR_STATUS_CODES.get(
            error_type, 
            self.ERROR_STATUS_CODES[ErrorTypes.INTERNAL_ERROR]
        )
        
        # Create error response
        error_response = {
            "error": error_type,
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code,
            "recovery_suggestion": recovery_suggestion,
            "request_context": self._sanitize_context(context),
            "source": {
                "file": caller_info.get("file"),
                "function": caller_info.get("function"),
                "line": caller_info.get("line")
            }
        }
        
        # Add stack trace in non-production environments
        if context.get("environment") != "production":
            error_response["stack_trace"] = stack_trace
        
        # Log the error
        self._log_error(error_response)
        
        # Return standardized error response
        return error_response
    
    def track_error_rate(self, window_seconds: int = 60) -> float:
        """
        Calculate the error rate over the specified time window.
        
        Args:
            window_seconds: Time window in seconds to calculate rate
            
        Returns:
            Error rate (errors per second)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Count errors in the window
        errors_in_window = sum(1 for ts in self.error_timestamps if ts > window_start)
        
        # Calculate rate (errors per second)
        if window_seconds > 0:
            return errors_in_window / window_seconds
        return 0.0
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """
        Get error metrics for monitoring.
        
        Returns:
            Dictionary with error metrics
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts_by_type": self.error_counts,
            "error_rate_1min": self.track_error_rate(60),
            "error_rate_5min": self.track_error_rate(300),
            "error_rate_15min": self.track_error_rate(900),
            "last_errors": {k: v for k, v in list(self.last_errors.items())[-10:]}
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check for the error handler.
        
        Returns:
            Health status dictionary
        """
        error_rate_1min = self.track_error_rate(60)
        
        return {
            "status": "healthy" if error_rate_1min < 1.0 else "degraded",
            "error_rate_1min": error_rate_1min,
            "total_errors": sum(self.error_counts.values()),
            "last_error_timestamp": self.error_timestamps[-1] if self.error_timestamps else None
        }
    
    def _log_error(self, error_response: Dict[str, Any]) -> None:
        """Log an error with appropriate severity."""
        error_type = error_response["error"]
        error_message = error_response["message"]
        source = error_response["source"]
        
        log_message = f"ERROR [{error_type}] {error_message} - in {source['file']}:{source['line']} ({source['function']})"
        
        # Choose log level based on error type
        if error_type in [ErrorTypes.INTERNAL_ERROR, ErrorTypes.DATABASE_ERROR, 
                         ErrorTypes.CONFIGURATION_ERROR]:
            logger.error(log_message)
        elif error_type in [ErrorTypes.TIMEOUT_ERROR, ErrorTypes.NETWORK_ERROR, 
                           ErrorTypes.EXTERNAL_SERVICE_ERROR]:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _update_error_metrics(self, error_type: str) -> None:
        """Update error metrics for monitoring."""
        # Increment error count
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add timestamp
        self.error_timestamps.append(time.time())
        
        # Limit timestamps list to last 24 hours
        day_ago = time.time() - 86400
        self.error_timestamps = [ts for ts in self.error_timestamps if ts > day_ago]
        
        # Store last error of this type
        self.last_errors[error_type] = {
            "timestamp": datetime.now().isoformat(),
            "count": self.error_counts[error_type]
        }
    
    def _get_caller_info(self) -> Dict[str, Any]:
        """Get information about the caller of handle_error."""
        stack = inspect.stack()
        
        # Look for the first frame that's not in this file
        for frame in stack[1:]:
            if frame.filename != __file__:
                return {
                    "file": frame.filename,
                    "function": frame.function,
                    "line": frame.lineno
                }
        
        # Fallback
        return {
            "file": "unknown",
            "function": "unknown",
            "line": 0
        }
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context data to remove sensitive information.
        
        Args:
            context: The context dictionary to sanitize
            
        Returns:
            Sanitized context dictionary
        """
        # Make a copy to avoid modifying the original
        sanitized = context.copy()
        
        # Remove sensitive fields if present
        sensitive_fields = [
            "password", "token", "api_key", "secret", "credential", 
            "auth", "key", "private", "social_security", "ssn", "credit_card"
        ]
        
        for field in list(sanitized.keys()):
            lower_field = field.lower()
            if any(sensitive in lower_field for sensitive in sensitive_fields):
                sanitized[field] = "***REDACTED***"
                
            # Sanitize nested dictionaries
            elif isinstance(sanitized[field], dict):
                sanitized[field] = self._sanitize_context(sanitized[field])
                
            # Handle lists of dictionaries
            elif isinstance(sanitized[field], list) and all(isinstance(item, dict) for item in sanitized[field]):
                sanitized[field] = [self._sanitize_context(item) for item in sanitized[field]]
        
        return sanitized

# Create a singleton instance
error_handler = ErrorHandler()

def error_handling_decorator(error_type: str = ErrorTypes.INTERNAL_ERROR):
    """
    Decorator for error handling in service methods.
    
    Args:
        error_type: Default error type to use if not specified during handling
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create context from function arguments
                context = {
                    "function": func.__name__,
                    "args": [str(arg) for arg in args],
                    "kwargs": kwargs
                }
                
                # Handle the error
                error_response = error_handler.handle_error(
                    error=e,
                    error_type=error_type,
                    context=context
                )
                
                # Return error response
                return {
                    "success": False,
                    "error": error_response
                }
        return wrapper
    return decorator 