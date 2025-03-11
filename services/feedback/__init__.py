"""
Feedback module for the Swoop AI Conversational Query Flow.

This module provides functionality for capturing, storing, and analyzing
user feedback on AI responses to improve system quality over time.
"""

from services.feedback.feedback_service import FeedbackService, get_feedback_service
from services.data.models.feedback import FeedbackModel, FeedbackStats, FeedbackType, IssueCategory

__all__ = [
    'FeedbackService',
    'get_feedback_service',
    'FeedbackModel',
    'FeedbackStats',
    'FeedbackType',
    'IssueCategory'
] 