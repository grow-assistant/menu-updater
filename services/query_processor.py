"""
Query Processor Service for the Swoop AI Conversational Query Flow.

This module integrates the Enhanced Data Access Layer with the Response Service
to process queries, execute database operations, and generate formatted responses.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import time
import traceback
from datetime import datetime

from services.data import get_data_access
from services.response_service import ResponseService
from services.context_manager import ContextManager, ConversationContext
from services.utils.error_handler import (
    ErrorTypes, 
    error_handler, 
    error_handling_decorator
)

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Processes user queries by connecting the data access layer with response generation.
    
    Features:
    - Query execution through enhanced data access layer
    - Response generation via response service
    - Error handling and recovery
    - Performance tracking
    - Context-aware query processing
    """
    
    # Error type mapping
    ERROR_TYPES = {
        "database_connection": ErrorTypes.DATABASE_ERROR,
        "database_query": ErrorTypes.SQL_EXECUTION_ERROR,
        "sql_generation": ErrorTypes.SQL_GENERATION_ERROR,
        "missing_parameter": ErrorTypes.VALIDATION_ERROR,
        "invalid_format": ErrorTypes.VALIDATION_ERROR,
        "permission_denied": ErrorTypes.AUTHORIZATION_ERROR,
        "entity_not_found": ErrorTypes.NOT_FOUND_ERROR,
        "timeout": ErrorTypes.TIMEOUT_ERROR,
        "internal_error": ErrorTypes.INTERNAL_ERROR,
        "classification_error": ErrorTypes.CLASSIFICATION_ERROR,
        "context_error": ErrorTypes.CONTEXT_ERROR,
        "action_error": ErrorTypes.ACTION_ERROR,
        "response_error": ErrorTypes.RESPONSE_GENERATION_ERROR
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the query processor.
        
        Args:
            config: Configuration dictionary for services
        """
        self.config = config
        
        # Initialize data access service
        self.data_access = get_data_access(config.get("database", {}))
        
        # Initialize response service
        self.response_service = ResponseService()
        
        # Initialize context manager
        self.context_manager = ContextManager(
            config.get("context_manager", {}).get("expiry_minutes", 30)
        )
        
        # Performance metrics
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_processing_time": 0,
            "average_processing_time": 0,
            "error_counts": {},
            "query_types": {}
        }
    
    @error_handling_decorator(ErrorTypes.INTERNAL_ERROR)
    def process_query(self, 
                     query_text: str, 
                     session_id: str,
                     classification_result: Dict[str, Any],
                     additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query based on its classification.
        
        Args:
            query_text: The original query text
            session_id: Session identifier for context tracking
            classification_result: Output from the query classifier
            additional_context: Any additional context to use
            
        Returns:
            Formatted response dictionary
        """
        start_time = time.time()
        
        try:
            # Update metrics
            self.metrics["total_queries"] += 1
            query_type = classification_result.get("query_type", "unknown")
            self.metrics["query_types"][query_type] = self.metrics["query_types"].get(query_type, 0) + 1
            
            # Get or create conversation context
            context = self.context_manager.get_context(session_id)
            
            # Update context with the new query
            context.update_with_query(query_text, classification_result)
            
            # Add any additional context
            if additional_context:
                for key, value in additional_context.items():
                    if key not in context.to_dict():
                        setattr(context, key, value)
            
            # Process based on query type
            query_info = {
                "query_type": query_type,
                "start_time": start_time,
                "session_id": session_id,
                "metadata": {}
            }
            
            if query_type == "data_query":
                response = self._process_data_query(
                    query_text, classification_result, context, query_info
                )
            elif query_type == "action_request":
                response = self._process_action_request(
                    query_text, classification_result, context, query_info
                )
            else:
                # Handle other query types or return error
                return self._create_error_response(
                    ErrorTypes.PARSING_ERROR,
                    f"Unsupported query type: {query_type}",
                    query_info, 
                    context
                )
            
            # Update metrics
            self.metrics["successful_queries"] += 1
            
            return response
            
        except Exception as e:
            # Log the error with the error handler
            error_response = error_handler.handle_error(
                e, 
                ErrorTypes.INTERNAL_ERROR,
                context={
                    "query_text": query_text,
                    "session_id": session_id,
                    "query_type": classification_result.get("query_type", "unknown")
                }
            )
            
            # Convert to appropriate response format
            return self._create_error_response(
                ErrorTypes.INTERNAL_ERROR,
                str(e),
                query_info,
                context
            )
        finally:
            # Update timing metrics
            processing_time = time.time() - start_time
            self.metrics["total_processing_time"] += processing_time
            if self.metrics["total_queries"] > 0:
                self.metrics["average_processing_time"] = (
                    self.metrics["total_processing_time"] / self.metrics["total_queries"]
                )
    
    def _process_data_query(self, 
                          query_text: str,
                          classification_result: Dict[str, Any],
                          context: ConversationContext,
                          query_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a data query.
        
        Args:
            query_text: Original query text
            classification_result: Query classification data
            context: Conversation context
            query_info: Query metadata
            
        Returns:
            Formatted response
        """
        try:
            # Generate SQL from the query
            sql_query, params = self._generate_sql_from_query(
                query_text, classification_result, context
            )
            
            if not sql_query:
                return self._create_error_response(
                    ErrorTypes.SQL_GENERATION_ERROR,
                    "Could not generate a valid SQL query from your request",
                    query_info,
                    context
                )
            
            # Execute the query
            result = self.data_access.execute_query(
                sql_query=sql_query,
                params=params,
                use_cache=True
            )
            
            # Check for errors in the result
            if result.get("error"):
                return self._create_error_response(
                    self.ERROR_TYPES.get(
                        result.get("error_type", "database_query"),
                        ErrorTypes.SQL_EXECUTION_ERROR
                    ),
                    result.get("message", "Database query error"),
                    query_info,
                    context
                )
            
            # Check for empty results
            if not result.get("data") or (
                isinstance(result.get("data"), list) and len(result.get("data")) == 0
            ):
                # Create metadata for the response
                metadata = {
                    "entity_type": context.get_reference_summary().get("entity_type", "item"),
                    "time_period": context.get_reference_summary().get("time_period", "")
                }
                
                # Format the empty response
                return self.response_service.format_response(
                    response_type="data",
                    data=[],
                    context=context.to_dict(),
                    metadata=metadata
                )
            
            # Create metadata for the response
            metadata = {
                "entity_type": context.get_reference_summary().get("entity_type", "item"),
                "time_period": context.get_reference_summary().get("time_period", ""),
                "query_execution_time": result.get("execution_time", 0)
            }
            
            # Format the success response
            return self.response_service.format_response(
                response_type="data",
                data=result.get("data", []),
                context=context.to_dict(),
                metadata=metadata
            )
            
        except Exception as e:
            error_type = ErrorTypes.SQL_EXECUTION_ERROR
            if "timeout" in str(e).lower():
                error_type = ErrorTypes.TIMEOUT_ERROR
            
            error_response = error_handler.handle_error(
                e, 
                error_type,
                context={
                    "query_text": query_text,
                    "classification": classification_result
                }
            )
            
            return self._create_error_response(
                error_type,
                str(e),
                query_info,
                context
            )
    
    def _process_action_request(self, 
                              query_text: str,
                              classification_result: Dict[str, Any],
                              context: ConversationContext,
                              query_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an action request.
        
        Args:
            query_text: Original query text
            classification_result: Query classification data
            context: Conversation context
            query_info: Query metadata
            
        Returns:
            Formatted response
        """
        try:
            # Extract action parameters
            action_type = classification_result.get("action", {}).get("type")
            parameters = classification_result.get("action", {}).get("parameters", {})
            
            if not action_type:
                return self._create_error_response(
                    ErrorTypes.VALIDATION_ERROR,
                    "No action type specified",
                    query_info,
                    context
                )
            
            # Check for required parameters
            required_params = classification_result.get("action", {}).get("required_params", [])
            missing_params = [param for param in required_params if param not in parameters]
            
            if missing_params:
                # Create a clarification response for missing parameters
                return self._create_clarification_response(
                    "missing_parameters",
                    ", ".join(missing_params),
                    query_info,
                    context
                )
            
            # Execute the action (this would normally call an action handler service)
            # For now, return a mock response
            action_response = {
                "action": action_type,
                "success": True,
                "entity_type": parameters.get("entity_type", "item"),
                "entity_name": parameters.get("name", parameters.get("id", "unknown")),
                "message": f"Successfully performed {action_type}"
            }
            
            # Create metadata for the response
            metadata = {
                "action_type": action_type,
                "entity_type": parameters.get("entity_type", "item"),
                "parameters": parameters
            }
            
            # Format the success response
            return self.response_service.format_response(
                response_type="action",
                data=action_response,
                context=context.to_dict(),
                metadata=metadata
            )
            
        except Exception as e:
            error_response = error_handler.handle_error(
                e, 
                ErrorTypes.ACTION_ERROR,
                context={
                    "query_text": query_text,
                    "classification": classification_result,
                    "action": classification_result.get("action", {})
                }
            )
            
            return self._create_error_response(
                ErrorTypes.ACTION_ERROR,
                str(e),
                query_info,
                context
            )
    
    def _generate_sql_from_query(self, 
                               query_text: str,
                               classification_result: Dict[str, Any],
                               context: ConversationContext) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a SQL query from the natural language query.
        
        Args:
            query_text: Original query text
            classification_result: Query classification data
            context: Conversation context
            
        Returns:
            Tuple of (sql_query, parameters)
        """
        # This would normally use a SQL generator service
        # For now, return a mock query
        entity_type = classification_result.get("entity_type", "orders")
        time_filter = context.get_reference_summary().get("time_period", "")
        
        if not time_filter:
            time_filter = "WHERE order_date >= DATE('now', '-7 day')"
        else:
            # Mock time filter transformation
            time_filter = f"WHERE order_date BETWEEN :start_date AND :end_date"
            
        sql_query = f"SELECT * FROM {entity_type} {time_filter} LIMIT 10"
        
        # Mock parameters
        params = {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        }
        
        return sql_query, params
    
    def _create_error_response(self, 
                             error_type: str,
                             error_message: str,
                             query_info: Dict[str, Any],
                             context: Optional[ConversationContext]) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error_type: Type of error
            error_message: Error message
            query_info: Query metadata
            context: Conversation context
            
        Returns:
            Formatted error response
        """
        # Update metrics
        self.metrics["failed_queries"] += 1
        self.metrics["error_counts"][error_type] = self.metrics["error_counts"].get(error_type, 0) + 1
        
        # Get context as dict if available
        context_dict = context.to_dict() if context else {}
        
        # Create error data
        error_data = {
            "error": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "query_info": query_info
        }
        
        # Get recovery suggestion from error handler
        recovery_suggestion = error_handler.DEFAULT_RECOVERY_SUGGESTIONS.get(
            error_type, 
            error_handler.DEFAULT_RECOVERY_SUGGESTIONS[ErrorTypes.INTERNAL_ERROR]
        )
        error_data["recovery_suggestion"] = recovery_suggestion
        
        # Format the error response using the response service
        return self.response_service.format_response(
            response_type="error",
            data=error_data,
            context=context_dict
        )
    
    def _create_clarification_response(self, 
                                     clarification_type: str,
                                     clarification_subject: str,
                                     query_info: Dict[str, Any],
                                     context: ConversationContext) -> Dict[str, Any]:
        """
        Create a clarification request response.
        
        Args:
            clarification_type: Type of clarification needed
            clarification_subject: Subject of the clarification
            query_info: Query metadata
            context: Conversation context
            
        Returns:
            Formatted clarification response
        """
        # Update context to indicate clarification is needed
        context.clarification_state = context.CLARIFYING
        context.clarification_type = clarification_type
        context.clarification_subject = clarification_subject
        
        # Create clarification data
        clarification_data = {
            "type": clarification_type,
            "subject": clarification_subject,
            "timestamp": datetime.now().isoformat(),
            "query_info": query_info
        }
        
        # Format the clarification response
        return self.response_service.format_response(
            response_type="clarification",
            data=clarification_data,
            context=context.to_dict(),
            metadata={"clarification_subject": clarification_subject}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the query processor.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check for the query processor.
        
        Returns:
            Health status dictionary
        """
        data_access_health = self.data_access.health_check()
        
        # Get error rate from error handler
        error_handler_health = error_handler.health_check()
        
        return {
            "status": "healthy" if data_access_health.get("status") == "healthy" else "degraded",
            "components": {
                "data_access": data_access_health,
                "error_handler": error_handler_health
            },
            "metrics": {
                "total_queries": self.metrics["total_queries"],
                "success_rate": (
                    self.metrics["successful_queries"] / self.metrics["total_queries"]
                    if self.metrics["total_queries"] > 0 else 1.0
                ),
                "average_processing_time": self.metrics["average_processing_time"]
            }
        } 