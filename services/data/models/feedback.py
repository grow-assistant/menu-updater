"""
Feedback data models for the Swoop AI Conversational Query Flow.

This module defines the data structures for storing and analyzing 
user feedback on AI responses to improve system quality over time.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import uuid


class FeedbackType:
    """Enumeration of feedback types."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    SPECIFIC_ISSUE = "specific_issue"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"
    TECHNICAL_ISSUE = "technical_issue"
    OTHER = "other"


class IssueCategory:
    """Enumeration of issue categories when feedback is negative."""
    INCORRECT_DATA = "incorrect_data"
    MISUNDERSTOOD_QUERY = "misunderstood_query"
    IRRELEVANT_RESPONSE = "irrelevant_response"
    MISSING_INFORMATION = "missing_information"
    TOO_COMPLICATED = "too_complicated"
    TOO_VERBOSE = "too_verbose"
    SQL_ERROR = "sql_error"
    SYSTEM_ERROR = "system_error"
    OTHER = "other"


class FeedbackModel:
    """
    Data model for storing user feedback on AI responses.
    
    Attributes:
        feedback_id: Unique identifier for the feedback
        session_id: Session identifier
        query_id: Identifier for the specific query
        query_text: The original text of the query
        response_id: Identifier for the response
        feedback_type: Type of feedback (helpful, not helpful, etc.)
        rating: Numeric rating (1-5)
        issue_category: Category of issue if feedback is negative
        comment: Free-text comment from the user
        original_intent: The intent classification for the query
        created_at: Timestamp when feedback was created
        metadata: Additional context or metadata
    """
    
    def __init__(
        self, 
        session_id: str,
        query_text: str,
        response_id: Optional[str] = None,
        feedback_type: str = FeedbackType.HELPFUL,
        rating: Optional[int] = None,
        issue_category: Optional[str] = None,
        comment: Optional[str] = None,
        original_intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        feedback_id: Optional[str] = None,
        query_id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        """
        Initialize a new feedback model.
        
        Args:
            session_id: Session identifier
            query_text: The original text of the query
            response_id: Identifier for the response
            feedback_type: Type of feedback
            rating: Numeric rating (1-5)
            issue_category: Category of issue if feedback is negative
            comment: Free-text comment from the user
            original_intent: The intent classification for the query
            metadata: Additional context or metadata
            feedback_id: Unique identifier (auto-generated if not provided)
            query_id: Identifier for the query (auto-generated if not provided)
            created_at: Timestamp when feedback was created
        """
        self.feedback_id = feedback_id or str(uuid.uuid4())
        self.session_id = session_id
        self.query_id = query_id or str(uuid.uuid4())
        self.query_text = query_text
        self.response_id = response_id
        self.feedback_type = feedback_type
        self.rating = rating
        self.issue_category = issue_category
        self.comment = comment
        self.original_intent = original_intent
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert feedback model to a dictionary.
        
        Returns:
            Dictionary representation of the feedback
        """
        return {
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "response_id": self.response_id,
            "feedback_type": self.feedback_type,
            "rating": self.rating,
            "issue_category": self.issue_category,
            "comment": self.comment,
            "original_intent": self.original_intent,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackModel':
        """
        Create a FeedbackModel from a dictionary.
        
        Args:
            data: Dictionary containing feedback data
            
        Returns:
            FeedbackModel instance
        """
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        return cls(
            feedback_id=data.get("feedback_id"),
            session_id=data.get("session_id"),
            query_id=data.get("query_id"),
            query_text=data.get("query_text"),
            response_id=data.get("response_id"),
            feedback_type=data.get("feedback_type"),
            rating=data.get("rating"),
            issue_category=data.get("issue_category"),
            comment=data.get("comment"),
            original_intent=data.get("original_intent"),
            metadata=data.get("metadata"),
            created_at=created_at
        )


class FeedbackStats:
    """
    Statistical summary of feedback.
    
    Attributes:
        total_count: Total number of feedback entries
        helpful_count: Number of 'helpful' feedback entries
        not_helpful_count: Number of 'not helpful' feedback entries
        average_rating: Average rating across all feedback
        issue_distribution: Count of each issue category
        top_query_intents: Most common query intents receiving feedback
    """
    
    def __init__(
        self,
        total_count: int = 0,
        helpful_count: int = 0,
        not_helpful_count: int = 0,
        average_rating: float = 0.0,
        issue_distribution: Dict[str, int] = None,
        top_query_intents: List[Dict[str, Any]] = None
    ):
        """
        Initialize feedback statistics.
        
        Args:
            total_count: Total number of feedback entries
            helpful_count: Number of 'helpful' feedback entries
            not_helpful_count: Number of 'not helpful' feedback entries
            average_rating: Average rating across all feedback
            issue_distribution: Count of each issue category
            top_query_intents: Most common query intents receiving feedback
        """
        self.total_count = total_count
        self.helpful_count = helpful_count
        self.not_helpful_count = not_helpful_count
        self.average_rating = average_rating
        self.issue_distribution = issue_distribution or {}
        self.top_query_intents = top_query_intents or []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert statistics to a dictionary.
        
        Returns:
            Dictionary representation of the statistics
        """
        return {
            "total_count": self.total_count,
            "helpful_count": self.helpful_count,
            "not_helpful_count": self.not_helpful_count,
            "helpful_percentage": (self.helpful_count / self.total_count * 100) if self.total_count else 0,
            "average_rating": self.average_rating,
            "issue_distribution": self.issue_distribution,
            "top_query_intents": self.top_query_intents
        } 