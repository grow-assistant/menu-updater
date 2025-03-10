"""
Tests for the Error Handler module.

This file contains tests that validate:
- Error handling functionality
- Error response formatting
- Metrics collection
- The decorator functionality
"""
import unittest
from unittest.mock import patch, MagicMock, call
import time
import logging
from datetime import datetime

from services.utils.error_handler import (
    ErrorHandler, 
    ErrorTypes, 
    error_handler, 
    error_handling_decorator
)

class TestErrorHandler(unittest.TestCase):
    """Test cases for the ErrorHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a fresh error handler for each test
        self.handler = ErrorHandler()
    
    def test_initialization(self):
        """Test that the error handler initializes with default values."""
        self.assertEqual(sum(self.handler.error_counts.values()), 0)
        self.assertEqual(len(self.handler.last_errors), 0)
        self.assertEqual(len(self.handler.error_timestamps), 0)
    
    def test_handle_error_basic(self):
        """Test basic error handling without additional parameters."""
        # Arrange
        test_error = ValueError("Test error message")
        
        # Act
        response = self.handler.handle_error(test_error)
        
        # Assert
        self.assertEqual(response["error"], ErrorTypes.INTERNAL_ERROR)
        self.assertEqual(response["message"], "Test error message")
        self.assertIn("timestamp", response)
        self.assertEqual(response["status_code"], 500)
        self.assertIn("recovery_suggestion", response)
        self.assertEqual(self.handler.error_counts[ErrorTypes.INTERNAL_ERROR], 1)
    
    def test_handle_error_with_type(self):
        """Test error handling with a specific error type."""
        # Arrange
        test_error = ValueError("Invalid input")
        error_type = ErrorTypes.VALIDATION_ERROR
        
        # Act
        response = self.handler.handle_error(test_error, error_type)
        
        # Assert
        self.assertEqual(response["error"], ErrorTypes.VALIDATION_ERROR)
        self.assertEqual(response["status_code"], 400)
        self.assertEqual(self.handler.error_counts[ErrorTypes.VALIDATION_ERROR], 1)
        self.assertIn("Please check your input", response["recovery_suggestion"])
    
    def test_handle_error_with_context(self):
        """Test error handling with additional context."""
        # Arrange
        test_error = ValueError("Database connection failed")
        error_type = ErrorTypes.DATABASE_ERROR
        context = {
            "query": "SELECT * FROM users",
            "user_id": 123,
            "password": "secret_password"  # Should be redacted
        }
        
        # Act
        response = self.handler.handle_error(test_error, error_type, context)
        
        # Assert
        self.assertEqual(response["error"], ErrorTypes.DATABASE_ERROR)
        self.assertEqual(response["request_context"]["query"], "SELECT * FROM users")
        self.assertEqual(response["request_context"]["user_id"], 123)
        self.assertEqual(response["request_context"]["password"], "***REDACTED***")
    
    def test_handle_error_with_custom_recovery(self):
        """Test error handling with a custom recovery suggestion."""
        # Arrange
        test_error = ValueError("Test error")
        custom_recovery = "Try this specific solution..."
        
        # Act
        response = self.handler.handle_error(
            test_error, 
            ErrorTypes.INTERNAL_ERROR,
            recovery_suggestion=custom_recovery
        )
        
        # Assert
        self.assertEqual(response["recovery_suggestion"], custom_recovery)
    
    @patch('services.utils.error_handler.logger')
    def test_log_error(self, mock_logger):
        """Test error logging with different severity levels."""
        # Arrange
        internal_error = ValueError("Critical system error")
        validation_error = ValueError("Invalid input")
        
        # Act - Test critical error (should use logger.error)
        self.handler.handle_error(internal_error, ErrorTypes.INTERNAL_ERROR)
        
        # Act - Test non-critical error (should use logger.info)
        self.handler.handle_error(validation_error, ErrorTypes.VALIDATION_ERROR)
        
        # Assert
        self.assertEqual(mock_logger.error.call_count, 1)
        self.assertEqual(mock_logger.info.call_count, 1)
    
    def test_sanitize_context(self):
        """Test context sanitization for sensitive information."""
        # Arrange
        context = {
            "user_id": 123,
            "api_key": "secret-api-key-value",
            "nested": {
                "password": "nested-password",
                "safe": "safe-value"
            },
            "list_of_dicts": [
                {"id": 1, "token": "secret-token-1"},
                {"id": 2, "token": "secret-token-2"}
            ]
        }
        
        # Act
        sanitized = self.handler._sanitize_context(context)
        
        # Assert
        self.assertEqual(sanitized["user_id"], 123)
        self.assertEqual(sanitized["api_key"], "***REDACTED***")
        self.assertEqual(sanitized["nested"]["password"], "***REDACTED***")
        self.assertEqual(sanitized["nested"]["safe"], "safe-value")
        self.assertEqual(sanitized["list_of_dicts"][0]["id"], 1)
        self.assertEqual(sanitized["list_of_dicts"][0]["token"], "***REDACTED***")
        self.assertEqual(sanitized["list_of_dicts"][1]["token"], "***REDACTED***")
    
    def test_error_metrics_update(self):
        """Test error metrics update functionality."""
        # Arrange
        test_error = ValueError("Test error")
        
        # Act - Generate errors of different types
        self.handler.handle_error(test_error, ErrorTypes.DATABASE_ERROR)
        self.handler.handle_error(test_error, ErrorTypes.DATABASE_ERROR)
        self.handler.handle_error(test_error, ErrorTypes.VALIDATION_ERROR)
        
        # Assert
        self.assertEqual(self.handler.error_counts[ErrorTypes.DATABASE_ERROR], 2)
        self.assertEqual(self.handler.error_counts[ErrorTypes.VALIDATION_ERROR], 1)
        self.assertEqual(len(self.handler.error_timestamps), 3)
        self.assertIn(ErrorTypes.DATABASE_ERROR, self.handler.last_errors)
        self.assertIn(ErrorTypes.VALIDATION_ERROR, self.handler.last_errors)
    
    def test_track_error_rate(self):
        """Test error rate calculation over time windows."""
        # Arrange - Set up error timestamps
        now = time.time()
        self.handler.error_timestamps = [
            now - 30,  # 30 seconds ago
            now - 60,  # 1 minute ago
            now - 90,  # 1.5 minutes ago
            now - 120, # 2 minutes ago
            now - 800  # ~13 minutes ago
        ]
        
        # Act & Assert - For each window count the errors that fall within it
        error_30s = sum(1 for ts in self.handler.error_timestamps if now - 30 < ts <= now)
        error_60s = sum(1 for ts in self.handler.error_timestamps if now - 60 < ts <= now)
        error_180s = sum(1 for ts in self.handler.error_timestamps if now - 180 < ts <= now)
        error_900s = sum(1 for ts in self.handler.error_timestamps if now - 900 < ts <= now)
        
        self.assertEqual(self.handler.track_error_rate(30), error_30s/30)  # errors in 30s window
        self.assertEqual(self.handler.track_error_rate(60), error_60s/60)  # errors in 60s window
        self.assertEqual(self.handler.track_error_rate(180), error_180s/180)  # errors in 3m window
        self.assertEqual(self.handler.track_error_rate(900), error_900s/900)  # errors in 15m window
    
    def test_get_error_metrics(self):
        """Test retrieval of error metrics."""
        # Arrange
        test_error = ValueError("Test error")
        
        # Simulate errors
        self.handler.handle_error(test_error, ErrorTypes.DATABASE_ERROR)
        self.handler.handle_error(test_error, ErrorTypes.VALIDATION_ERROR)
        
        # Act
        metrics = self.handler.get_error_metrics()
        
        # Assert
        self.assertEqual(metrics["total_errors"], 2)
        self.assertEqual(metrics["error_counts_by_type"][ErrorTypes.DATABASE_ERROR], 1)
        self.assertEqual(metrics["error_counts_by_type"][ErrorTypes.VALIDATION_ERROR], 1)
        self.assertIn("error_rate_1min", metrics)
        self.assertIn("error_rate_5min", metrics)
        self.assertIn("error_rate_15min", metrics)
    
    def test_health_check(self):
        """Test health check functionality."""
        # Arrange - Error rate below threshold
        self.handler.track_error_rate = MagicMock(return_value=0.5)
        
        # Act
        health_status = self.handler.health_check()
        
        # Assert
        self.assertEqual(health_status["status"], "healthy")
        self.assertEqual(health_status["error_rate_1min"], 0.5)
        
        # Arrange - Error rate above threshold
        self.handler.track_error_rate = MagicMock(return_value=1.5)
        
        # Act
        health_status = self.handler.health_check()
        
        # Assert
        self.assertEqual(health_status["status"], "degraded")
    
    def test_get_caller_info(self):
        """Test retrieving caller information."""
        # Act
        caller_info = self.handler._get_caller_info()
        
        # Assert
        self.assertIn("file", caller_info)
        self.assertIn("function", caller_info)
        self.assertIn("line", caller_info)
        self.assertEqual(caller_info["function"], "test_get_caller_info")


class TestErrorHandlingDecorator(unittest.TestCase):
    """Test cases for the error handling decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock for the error handler
        self.mock_error_handler = MagicMock()
        self.mock_error_handler.handle_error.return_value = {
            "error": ErrorTypes.INTERNAL_ERROR,
            "message": "Test error"
        }
        
        # Save and restore the real error handler
        self.original_error_handler = error_handler
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Restore the original error handler
        globals()['error_handler'] = self.original_error_handler
    
    @patch('services.utils.error_handler.error_handler')
    def test_decorator_success_case(self, mock_handler):
        """Test the decorator when the function succeeds."""
        # Arrange
        @error_handling_decorator()
        def test_function():
            return "success"
        
        # Act
        result = test_function()
        
        # Assert
        self.assertEqual(result, "success")
        mock_handler.handle_error.assert_not_called()
    
    @patch('services.utils.error_handler.error_handler')
    def test_decorator_error_case(self, mock_handler):
        """Test the decorator when the function raises an exception."""
        # Arrange
        mock_handler.handle_error.return_value = {
            "error": ErrorTypes.INTERNAL_ERROR,
            "message": "An error occurred"
        }
        
        @error_handling_decorator(ErrorTypes.DATABASE_ERROR)
        def failing_function():
            raise ValueError("Test error")
        
        # Act
        result = failing_function()
        
        # Assert
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], mock_handler.handle_error.return_value)
        mock_handler.handle_error.assert_called_once()
        
        # Verify the error type was passed correctly
        args, kwargs = mock_handler.handle_error.call_args
        self.assertEqual(kwargs["error_type"], ErrorTypes.DATABASE_ERROR)
    
    @patch('services.utils.error_handler.error_handler')
    def test_decorator_preserves_function_metadata(self, mock_handler):
        """Test that the decorator preserves function metadata."""
        # Arrange
        @error_handling_decorator()
        def function_with_docstring():
            """This is a test docstring."""
            return True
        
        # Assert
        self.assertEqual(function_with_docstring.__name__, "function_with_docstring")
        self.assertEqual(function_with_docstring.__doc__, "This is a test docstring.")
    
    @patch('services.utils.error_handler.error_handler')
    def test_decorator_with_arguments(self, mock_handler):
        """Test that the decorator correctly passes function arguments."""
        # Arrange
        mock_handler.handle_error.return_value = {"error": "test"}
        
        @error_handling_decorator()
        def function_with_args(a, b, c=None):
            raise ValueError("Test error")
        
        # Act
        result = function_with_args(1, "test", c={"key": "value"})
        
        # Assert
        self.assertFalse(result["success"])
        
        # Check that context contains args
        args, kwargs = mock_handler.handle_error.call_args
        context = kwargs["context"]
        self.assertEqual(context["function"], "function_with_args")
        self.assertEqual(len(context["args"]), 2)
        self.assertEqual(context["kwargs"], {"c": {"key": "value"}})


if __name__ == '__main__':
    unittest.main() 