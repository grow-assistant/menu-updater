"""
Base query path class for the AI Menu Updater application.
All specific query paths should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class QueryPath(ABC):
    """Base class for all query paths in the AI Menu Updater application."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the query path.
        
        Args:
            context: Optional context dictionary with session state information
        """
        self.context = context or {}
        
    @property
    def query_type(self) -> str:
        """Return the query type for this path."""
        return getattr(self, "_query_type", "unknown")
        
    @abstractmethod
    def generate_sql(self, query: str, **kwargs) -> str:
        """
        Generate SQL for the query.
        
        Args:
            query: User query
            **kwargs: Additional parameters
            
        Returns:
            str: Generated SQL query
        """
        pass
        
    @abstractmethod
    def process_results(self, results: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """
        Process query results.
        
        Args:
            results: Query results
            query: Original user query
            **kwargs: Additional parameters
            
        Returns:
            dict: Processed results
        """
        pass
        
    def get_context(self) -> Dict[str, Any]:
        """Get the current context."""
        return self.context
        
    def update_context(self, new_context: Dict[str, Any]) -> None:
        """
        Update the context.
        
        Args:
            new_context: New context to merge with the existing context
        """
        self.context.update(new_context)
        
    def get_location_id(self) -> int:
        """Get the current location ID from context."""
        # Try to get the location ID from different possible sources in context
        location_id = self.context.get(
            "selected_location_id",
            self.context.get("location_id", 62)  # Default to 62 (Idle Hour)
        )
        return location_id
        
    def get_location_ids(self) -> List[int]:
        """Get all selected location IDs from context."""
        # Try to get the location IDs from different possible sources in context
        location_ids = self.context.get(
            "selected_location_ids", 
            [self.get_location_id()]  # Fall back to single location ID
        )
        return location_ids 