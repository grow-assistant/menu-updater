"""
Feedback Service for the Swoop AI Conversational Query Flow.

This module provides functionality for storing, retrieving, and analyzing
user feedback on AI responses to improve system quality over time.
"""
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd

from services.data.models.feedback import FeedbackModel, FeedbackStats, FeedbackType, IssueCategory

logger = logging.getLogger(__name__)

class FeedbackService:
    """
    Service for managing and analyzing user feedback on AI responses.
    
    Features:
    - Storing feedback in a persistent storage
    - Retrieving feedback for analysis
    - Generating statistics and insights
    - Exporting feedback data for model improvement
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the feedback service.
        
        Args:
            config: Configuration dictionary with settings for the feedback service
        """
        self.config = config
        self.storage_type = config.get("feedback_storage_type", "file")  # 'file', 'database', 'memory'
        
        # File storage settings
        if self.storage_type == "file":
            self.storage_dir = config.get("feedback_storage_dir", "data/feedback")
            os.makedirs(self.storage_dir, exist_ok=True)
            
        # Database settings
        elif self.storage_type == "database":
            # These would be used with a proper database connection
            self.db_connection_string = config.get("feedback_db_connection")
            self.table_name = config.get("feedback_table_name", "ai_feedback")
            # In a real implementation, we would initialize the database connection here
        
        # In-memory storage (for testing or when persistence isn't required)
        self.memory_storage = []
        
        # Cache for quick stats
        self.stats_cache = None
        self.stats_cache_timestamp = None
        self.stats_cache_ttl = config.get("feedback_stats_cache_ttl", 3600)  # 1 hour default
        
        logger.info(f"Feedback service initialized with storage_type={self.storage_type}")
    
    def submit_feedback(self, feedback: Union[FeedbackModel, Dict[str, Any]]) -> str:
        """
        Store user feedback about an AI response.
        
        Args:
            feedback: FeedbackModel instance or dictionary with feedback data
            
        Returns:
            Feedback ID of the stored feedback
        """
        if isinstance(feedback, dict):
            feedback_model = FeedbackModel.from_dict(feedback)
        else:
            feedback_model = feedback
            
        # Store based on the configured storage type
        if self.storage_type == "file":
            return self._store_feedback_in_file(feedback_model)
        elif self.storage_type == "database":
            return self._store_feedback_in_database(feedback_model)
        else:
            # Default to in-memory storage
            return self._store_feedback_in_memory(feedback_model)
    
    def store_query_response(self, 
                           session_id: str,
                           response_id: str,
                           query_text: str,
                           query_type: str,
                           response: Dict[str, Any],
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a query and its response for later feedback reference.
        
        This method tracks user queries and system responses to associate
        feedback with the specific queries and responses they relate to.
        
        Args:
            session_id: Session identifier
            response_id: Unique identifier for the response
            query_text: The text of the user's query
            query_type: Classification of the query
            response: The system's response
            metadata: Additional metadata about the query/response
        """
        # Create a record of the query and response
        response_data = {
            "session_id": session_id,
            "response_id": response_id,
            "query_text": query_text,
            "query_type": query_type,
            "response": response,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Use the appropriate storage method
        try:
            if self.storage_type == "file":
                self._store_response_in_file(response_data)
            elif self.storage_type == "database":
                self._store_response_in_database(response_data)
            else:
                # Default to in-memory storage
                self._store_response_in_memory(response_data)
                
            logger.info(f"Stored response {response_id} for potential feedback")
        except Exception as e:
            logger.error(f"Failed to store response {response_id}: {str(e)}")
    
    def get_feedback(self, 
                   feedback_id: Optional[str] = None,
                   session_id: Optional[str] = None,
                   query_id: Optional[str] = None,
                   limit: int = 100,
                   offset: int = 0,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[FeedbackModel]:
        """
        Retrieve feedback based on search criteria.
        
        Args:
            feedback_id: Optional specific feedback ID to retrieve
            session_id: Optional session ID to filter by
            query_id: Optional query ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            List of FeedbackModel instances matching the criteria
        """
        if self.storage_type == "file":
            return self._get_feedback_from_file(
                feedback_id, session_id, query_id, limit, offset, start_date, end_date)
        elif self.storage_type == "database":
            return self._get_feedback_from_database(
                feedback_id, session_id, query_id, limit, offset, start_date, end_date)
        else:
            return self._get_feedback_from_memory(
                feedback_id, session_id, query_id, limit, offset, start_date, end_date)
    
    def get_statistics(self, 
                     force_refresh: bool = False,
                     time_period: Optional[str] = None) -> FeedbackStats:
        """
        Generate statistics from feedback data.
        
        Args:
            force_refresh: Whether to force regeneration of statistics
            time_period: Optional time period to restrict statistics (e.g., 'day', 'week', 'month')
            
        Returns:
            FeedbackStats instance with statistical summary
        """
        # Check if we can use cached stats
        if not force_refresh and self.stats_cache and self.stats_cache_timestamp:
            cache_age = time.time() - self.stats_cache_timestamp
            if cache_age < self.stats_cache_ttl:
                return self.stats_cache
        
        # Determine date range for filtering
        start_date = None
        if time_period:
            now = datetime.utcnow()
            if time_period == 'day':
                start_date = now - timedelta(days=1)
            elif time_period == 'week':
                start_date = now - timedelta(days=7)
            elif time_period == 'month':
                start_date = now - timedelta(days=30)
            elif time_period == 'quarter':
                start_date = now - timedelta(days=90)
            elif time_period == 'year':
                start_date = now - timedelta(days=365)
        
        # Get all feedback for the specified time period
        feedback_list = self.get_feedback(start_date=start_date, limit=10000)
        
        # If no feedback, return empty stats
        if not feedback_list:
            return FeedbackStats()
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([f.to_dict() for f in feedback_list])
        
        # Calculate basic statistics
        total_count = len(df)
        helpful_count = len(df[df['feedback_type'] == FeedbackType.HELPFUL])
        not_helpful_count = len(df[df['feedback_type'] == FeedbackType.NOT_HELPFUL])
        
        # Calculate average rating (if ratings exist)
        average_rating = 0.0
        if 'rating' in df.columns and not df['rating'].isnull().all():
            average_rating = df['rating'].mean()
        
        # Calculate issue distribution
        issue_distribution = {}
        if 'issue_category' in df.columns:
            issue_counts = df['issue_category'].value_counts().to_dict()
            issue_distribution = {k: v for k, v in issue_counts.items() if k is not None}
        
        # Get top query intents
        top_query_intents = []
        if 'original_intent' in df.columns:
            intent_counts = df['original_intent'].value_counts().head(10).to_dict()
            top_query_intents = [{"intent": k, "count": v} for k, v in intent_counts.items() if k is not None]
        
        # Create and cache stats
        stats = FeedbackStats(
            total_count=total_count,
            helpful_count=helpful_count,
            not_helpful_count=not_helpful_count,
            average_rating=average_rating,
            issue_distribution=issue_distribution,
            top_query_intents=top_query_intents
        )
        
        self.stats_cache = stats
        self.stats_cache_timestamp = time.time()
        
        return stats
    
    def _store_feedback_in_file(self, feedback: FeedbackModel) -> str:
        """Store feedback in a JSON file."""
        # Create filename based on feedback ID
        filename = os.path.join(self.storage_dir, f"{feedback.feedback_id}.json")
        
        # Convert to dictionary and save as JSON
        with open(filename, 'w') as f:
            json.dump(feedback.to_dict(), f, indent=2)
            
        logger.info(f"Stored feedback with ID {feedback.feedback_id} in file {filename}")
        return feedback.feedback_id
    
    def _store_feedback_in_database(self, feedback: FeedbackModel) -> str:
        """Store feedback in a database."""
        # In a real implementation, this would use a database connection
        # For now, we'll just log and use the in-memory implementation
        logger.info(f"Database storage not implemented, using in-memory storage for feedback {feedback.feedback_id}")
        return self._store_feedback_in_memory(feedback)
    
    def _store_feedback_in_memory(self, feedback: FeedbackModel) -> str:
        """Store feedback in memory."""
        self.memory_storage.append(feedback)
        logger.info(f"Stored feedback with ID {feedback.feedback_id} in memory")
        return feedback.feedback_id
    
    def _get_feedback_from_file(self, 
                              feedback_id: Optional[str],
                              session_id: Optional[str],
                              query_id: Optional[str],
                              limit: int,
                              offset: int,
                              start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> List[FeedbackModel]:
        """Retrieve feedback from file storage."""
        result = []
        
        # If specific feedback ID is requested, try to get just that file
        if feedback_id:
            filename = os.path.join(self.storage_dir, f"{feedback_id}.json")
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    feedback_data = json.load(f)
                    feedback = FeedbackModel.from_dict(feedback_data)
                    return [feedback]
            return []
        
        # Otherwise, scan directory for matching files
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.storage_dir, filename)
            with open(filepath, 'r') as f:
                try:
                    feedback_data = json.load(f)
                    
                    # Apply filters
                    if session_id and feedback_data.get('session_id') != session_id:
                        continue
                    if query_id and feedback_data.get('query_id') != query_id:
                        continue
                    
                    # Date filtering
                    if start_date or end_date:
                        created_at = feedback_data.get('created_at')
                        if created_at:
                            feedback_date = datetime.fromisoformat(created_at)
                            if start_date and feedback_date < start_date:
                                continue
                            if end_date and feedback_date > end_date:
                                continue
                    
                    feedback = FeedbackModel.from_dict(feedback_data)
                    result.append(feedback)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing feedback file {filename}: {e}")
        
        # Apply pagination
        return sorted(result, key=lambda x: x.created_at, reverse=True)[offset:offset+limit]
    
    def _get_feedback_from_database(self, 
                                  feedback_id: Optional[str],
                                  session_id: Optional[str],
                                  query_id: Optional[str],
                                  limit: int,
                                  offset: int,
                                  start_date: Optional[datetime],
                                  end_date: Optional[datetime]) -> List[FeedbackModel]:
        """Retrieve feedback from database storage."""
        # In a real implementation, this would execute a SQL query with the filters
        # For now, we'll just log and use the in-memory implementation
        logger.info("Database retrieval not implemented, using in-memory storage")
        return self._get_feedback_from_memory(
            feedback_id, session_id, query_id, limit, offset, start_date, end_date)
    
    def _get_feedback_from_memory(self, 
                                feedback_id: Optional[str],
                                session_id: Optional[str],
                                query_id: Optional[str],
                                limit: int,
                                offset: int,
                                start_date: Optional[datetime],
                                end_date: Optional[datetime]) -> List[FeedbackModel]:
        """Retrieve feedback from memory storage."""
        result = []
        
        for feedback in self.memory_storage:
            # Apply filters
            if feedback_id and feedback.feedback_id != feedback_id:
                continue
            if session_id and feedback.session_id != session_id:
                continue
            if query_id and feedback.query_id != query_id:
                continue
                
            # Date filtering
            if start_date and feedback.created_at < start_date:
                continue
            if end_date and feedback.created_at > end_date:
                continue
                
            result.append(feedback)
        
        # Apply pagination
        return sorted(result, key=lambda x: x.created_at, reverse=True)[offset:offset+limit]
    
    def _store_response_in_file(self, response_data: Dict[str, Any]) -> None:
        """Store query response in a JSON file for future feedback reference."""
        # Create a subdirectory for query responses if it doesn't exist
        response_dir = os.path.join(self.storage_dir, 'responses')
        os.makedirs(response_dir, exist_ok=True)
        
        # Create filename based on response ID
        response_id = response_data.get('response_id')
        filename = os.path.join(response_dir, f"{response_id}.json")
        
        # Save as JSON
        with open(filename, 'w') as f:
            # Remove large response content if needed to save space
            response_data_to_save = response_data.copy()
            # Optionally trim large response data before saving
            if 'response' in response_data_to_save and isinstance(response_data_to_save['response'], dict):
                # Keep only essential information from response
                full_response = response_data_to_save['response'] 
                response_data_to_save['response'] = {
                    'type': full_response.get('type'),
                    'message': full_response.get('message'),
                    'response_id': full_response.get('response_id'),
                    # Add other essential fields but skip large data arrays
                }
            
            json.dump(response_data_to_save, f, indent=2)
            
        logger.debug(f"Stored response with ID {response_id} in file {filename}")
    
    def _store_response_in_database(self, response_data: Dict[str, Any]) -> None:
        """Store query response in a database for future feedback reference."""
        # In a real implementation, this would use a database connection
        # For now, we'll just log and use the in-memory implementation
        logger.info(f"Database storage not implemented for responses, using in-memory storage")
        self._store_response_in_memory(response_data)
    
    def _store_response_in_memory(self, response_data: Dict[str, Any]) -> None:
        """Store query response in memory for future feedback reference."""
        # Initialize response storage if not already done
        if not hasattr(self, 'response_storage'):
            self.response_storage = []
            
        self.response_storage.append(response_data)
        logger.debug(f"Stored response with ID {response_data.get('response_id')} in memory")
    
    def get_response(self, response_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a stored response by its ID.
        
        Args:
            response_id: The unique identifier of the response
            
        Returns:
            Dictionary with response data or None if not found
        """
        # Check storage type and use appropriate retrieval method
        if self.storage_type == "file":
            return self._get_response_from_file(response_id)
        elif self.storage_type == "database":
            return self._get_response_from_database(response_id)
        else:
            return self._get_response_from_memory(response_id)
    
    def _get_response_from_file(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve response data from file storage."""
        response_dir = os.path.join(self.storage_dir, 'responses')
        filename = os.path.join(response_dir, f"{response_id}.json")
        
        if not os.path.exists(filename):
            logger.warning(f"Response file not found for ID {response_id}")
            return None
            
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading response file for ID {response_id}: {str(e)}")
            return None
    
    def _get_response_from_database(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve response data from database storage."""
        # In a real implementation, this would query a database
        logger.info(f"Database retrieval not implemented for responses, using in-memory retrieval")
        return self._get_response_from_memory(response_id)
    
    def _get_response_from_memory(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve response data from memory storage."""
        if not hasattr(self, 'response_storage'):
            return None
            
        for response in self.response_storage:
            if response.get('response_id') == response_id:
                return response
                
        return None
    
    def export_feedback_for_analysis(self, 
                                   format: str = 'csv', 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> str:
        """
        Export feedback data for external analysis.
        
        Args:
            format: Export format ('csv' or 'json')
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Path to the exported file
        """
        # Get all feedback for the specified time period
        feedback_list = self.get_feedback(start_date=start_date, end_date=end_date, limit=100000)
        
        # Create export directory if it doesn't exist
        export_dir = os.path.join(self.storage_dir, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'csv':
            # Convert to DataFrame and export as CSV
            df = pd.DataFrame([f.to_dict() for f in feedback_list])
            export_path = os.path.join(export_dir, f'feedback_export_{timestamp}.csv')
            df.to_csv(export_path, index=False)
        else:
            # Export as JSON
            export_path = os.path.join(export_dir, f'feedback_export_{timestamp}.json')
            with open(export_path, 'w') as f:
                json.dump([f.to_dict() for f in feedback_list], f, indent=2)
        
        logger.info(f"Exported {len(feedback_list)} feedback entries to {export_path}")
        return export_path


def get_feedback_service(config: Optional[Dict[str, Any]] = None) -> FeedbackService:
    """
    Factory function to get a FeedbackService instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        FeedbackService instance
    """
    if config is None:
        config = {}
    return FeedbackService(config) 