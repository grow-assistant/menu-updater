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
        # Database errors
        'connection_error': {
            'message': 'Unable to connect to the database',
            'recovery': 'database_error'
        },
        'timeout_error': {
            'message': 'The query took too long to execute',
            'recovery': 'database_error'
        },
        'query_error': {
            'message': 'There was an error in the database query',
            'recovery': 'database_error'
        },
        
        # Data access errors
        'invalid_query': {
            'message': 'The query is invalid or malformed',
            'recovery': 'default'
        },
        'permission_error': {
            'message': 'You do not have permission to access this data',
            'recovery': 'no_permission'
        },
        
        # Context errors
        'missing_entity': {
            'message': 'Could not determine which entity you are referring to',
            'recovery': 'missing_entity'
        },
        'invalid_date': {
            'message': 'Could not understand the date or time period',
            'recovery': 'invalid_date'
        },
        
        # Generic errors
        'internal_error': {
            'message': 'An internal error occurred',
            'recovery': 'default'
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the query processor.
        
        Args:
            config: Configuration dictionary including database settings
        """
        self.config = config
        
        # Initialize data access layer
        self.data_access = get_data_access(config)
        
        # Initialize response service
        self.response_service = ResponseService()
        
        # Initialize context manager if provided in config
        context_manager_config = config.get('context_manager', {})
        self.context_manager = ContextManager(
            expiry_minutes=context_manager_config.get('expiry_minutes', 30)
        )
        
        # Performance metrics
        self.metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_processing_time': 0,
            'total_processing_time': 0
        }
        
        logger.info("QueryProcessor initialized")
    
    def process_query(self, 
                     query_text: str, 
                     session_id: str,
                     classification_result: Dict[str, Any],
                     additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query and generate a response.
        
        Args:
            query_text: The user's query text
            session_id: Session identifier for context tracking
            classification_result: Results from query classification
            additional_context: Any additional context information
            
        Returns:
            Dict with response information
        """
        start_time = time.time()
        self.metrics['total_queries'] += 1
        
        # Track query info for metrics and logging
        query_info = {
            'query_id': f"q-{int(start_time)}-{self.metrics['total_queries']}",
            'session_id': session_id,
            'query_text': query_text,
            'query_type': classification_result.get('query_type', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Processing query: {query_info['query_id']} - '{query_text}'")
        
        try:
            # Get conversation context
            context = self.context_manager.get_context(session_id)
            
            # Update context with new query
            context.update_with_query(query_text, classification_result)
            
            # Add additional context if provided
            if additional_context:
                for key, value in additional_context.items():
                    if key not in context.to_dict():
                        setattr(context, key, value)
            
            # Process based on query type
            query_type = classification_result.get('query_type', 'data_query')
            
            if query_type == 'action_request':
                response = self._process_action_request(
                    query_text, classification_result, context, query_info
                )
            else:  # Default to data query
                response = self._process_data_query(
                    query_text, classification_result, context, query_info
                )
            
            # Record successful query
            self.metrics['successful_queries'] += 1
            
        except Exception as e:
            logger.error(f"Error processing query {query_info['query_id']}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Record failed query
            self.metrics['failed_queries'] += 1
            
            # Generate error response
            response = self._create_error_response(
                'internal_error', 
                str(e), 
                query_info,
                context if 'context' in locals() else None
            )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update timing metrics
        self.metrics['total_processing_time'] += processing_time
        self.metrics['avg_processing_time'] = (
            self.metrics['total_processing_time'] / self.metrics['total_queries']
        )
        
        # Add performance info to response metadata
        if 'metadata' not in response:
            response['metadata'] = {}
            
        response['metadata'].update({
            'query_id': query_info['query_id'],
            'processing_time': processing_time,
            'query_type': query_info.get('query_type', 'unknown')
        })
        
        # If context exists, update it with the response
        if 'context' in locals() and context is not None:
            context.update_with_response(response.get('text', ''))
        
        logger.info(
            f"Query {query_info['query_id']} processed in {processing_time:.4f}s "
            f"with response type: {response.get('type', 'unknown')}"
        )
        
        return response
    
    def _process_data_query(self, 
                          query_text: str,
                          classification_result: Dict[str, Any],
                          context: ConversationContext,
                          query_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a data retrieval query.
        
        Args:
            query_text: The user's query text
            classification_result: Results from query classification
            context: Conversation context
            query_info: Query tracking information
            
        Returns:
            Response dictionary
        """
        # Extract parameters from classification
        params = classification_result.get('parameters', {})
        entity_type = params.get('entity_type', context.get_reference_summary().get('entity_type'))
        
        # Check if we're missing required parameters
        if not entity_type:
            # We need clarification on entity type
            return self._create_clarification_response(
                'entity_type',
                'what type of information you are looking for',
                query_info,
                context
            )
        
        # Generate SQL from the query and context
        try:
            sql_query, sql_params = self._generate_sql_from_query(
                query_text, classification_result, context
            )
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return self._create_error_response(
                'invalid_query',
                f"Unable to generate a database query: {str(e)}",
                query_info,
                context
            )
        
        # Execute the query
        df, metadata = self.data_access.query_to_dataframe(
            sql_query=sql_query,
            params=sql_params,
            use_cache=True
        )
        
        # Check for execution errors
        if not metadata.get('success', False):
            error_type = 'query_error'
            if 'timeout' in metadata.get('error', '').lower():
                error_type = 'timeout_error'
            
            return self._create_error_response(
                error_type,
                metadata.get('error', 'Unknown database error'),
                query_info,
                context
            )
        
        # Generate response
        response_metadata = {
            'entity_type': entity_type,
            'time_period': context.get_reference_summary().get('time_period', 'the requested period'),
            'execution_metadata': metadata,
            **query_info
        }
        
        # Format the response
        response = self.response_service.format_response(
            response_type='data',
            data=df,
            context=context.to_dict(),
            metadata=response_metadata
        )
        
        return response
    
    def _process_action_request(self, 
                              query_text: str,
                              classification_result: Dict[str, Any],
                              context: ConversationContext,
                              query_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an action request query.
        
        Args:
            query_text: The user's query text
            classification_result: Results from query classification
            context: Conversation context
            query_info: Query tracking information
            
        Returns:
            Response dictionary
        """
        # Extract action parameters
        params = classification_result.get('parameters', {})
        action_type = params.get('action_type')
        entity_type = params.get('entity_type', context.get_reference_summary().get('entity_type'))
        entity_id = params.get('entity_id')
        entity_name = params.get('entity_name')
        
        # Check if we have all required parameters
        if not action_type:
            return self._create_clarification_response(
                'action_type',
                'what action you want to perform',
                query_info,
                context
            )
        
        if not entity_type:
            return self._create_clarification_response(
                'entity_type',
                'what type of item you want to modify',
                query_info,
                context
            )
        
        if not (entity_id or entity_name):
            return self._create_clarification_response(
                'entity_name',
                f'which {entity_type} you want to modify',
                query_info,
                context
            )
        
        # For this implementation, we'll just simulate the action
        # In a real implementation, we would call the ActionHandler service
        
        # Simulate successful action
        action_result = {
            'action': action_type,
            'entity_type': entity_type,
            'entity_name': entity_name or f"ID: {entity_id}",
            'success': True,
            'details': f"The {entity_type} has been updated successfully."
        }
        
        # Format response
        response_metadata = {
            'entity_type': entity_type,
            'entity_name': entity_name or f"ID: {entity_id}",
            **query_info
        }
        
        response = self.response_service.format_response(
            response_type='action',
            data=action_result,
            context=context.to_dict(),
            metadata=response_metadata
        )
        
        return response
    
    def _generate_sql_from_query(self, 
                               query_text: str,
                               classification_result: Dict[str, Any],
                               context: ConversationContext) -> Tuple[str, Dict[str, Any]]:
        """
        Generate SQL from the query and context.
        
        Args:
            query_text: The user's query text
            classification_result: Results from query classification
            context: Conversation context
            
        Returns:
            Tuple of (sql_query, sql_parameters)
        """
        # This is a simplified implementation
        # In a real system, you would use a specialized SQL generator
        # based on the query type and parameters
        
        # Extract parameters
        params = classification_result.get('parameters', {})
        entity_type = params.get('entity_type', context.get_reference_summary().get('entity_type', 'items'))
        
        # Get time period from context if available
        time_refs = context.get_reference_summary().get('time_references', {})
        start_date = time_refs.get('start_date')
        end_date = time_refs.get('end_date')
        
        # Build very basic SQL (in reality, this would be much more sophisticated)
        sql_params = {}
        
        if entity_type == 'orders':
            sql = "SELECT * FROM orders"
            
            # Add time filters if available
            where_clauses = []
            if start_date:
                where_clauses.append("order_date >= :start_date")
                sql_params['start_date'] = start_date
            
            if end_date:
                where_clauses.append("order_date <= :end_date")
                sql_params['end_date'] = end_date
            
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
            # Add limit
            sql += " LIMIT 100"
            
        elif entity_type == 'menu_items':
            sql = "SELECT * FROM menu_items"
            
            # Add status filter
            sql += " WHERE active = 1"
            
            # Add limit
            sql += " LIMIT 100"
            
        else:
            # Generic fallback
            sql = f"SELECT * FROM {entity_type} LIMIT 100"
        
        return sql, sql_params
    
    def _create_error_response(self, 
                             error_type: str,
                             error_message: str,
                             query_info: Dict[str, Any],
                             context: Optional[ConversationContext]) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            error_type: Type of error
            error_message: Error message
            query_info: Query tracking information
            context: Conversation context (optional)
            
        Returns:
            Error response dictionary
        """
        error_data = {
            'error': error_type,
            'message': self.ERROR_TYPES.get(error_type, {}).get('message', error_message),
            'recovery_suggestion': self.ERROR_TYPES.get(error_type, {}).get('recovery', 'default')
        }
        
        # Format the error response
        ctx_dict = context.to_dict() if context else {}
        
        response = self.response_service.format_response(
            response_type='error',
            data=error_data,
            context=ctx_dict,
            metadata={**query_info}
        )
        
        return response
    
    def _create_clarification_response(self, 
                                     clarification_type: str,
                                     clarification_subject: str,
                                     query_info: Dict[str, Any],
                                     context: ConversationContext) -> Dict[str, Any]:
        """
        Create a clarification response.
        
        Args:
            clarification_type: Type of clarification needed
            clarification_subject: Subject requiring clarification
            query_info: Query tracking information
            context: Conversation context
            
        Returns:
            Clarification response dictionary
        """
        clarification_data = {
            'clarification_type': clarification_type,
            'clarification_subject': clarification_subject
        }
        
        # Add options if available
        if clarification_type == 'entity_type':
            # Suggest common entity types based on the system's capabilities
            clarification_data['options'] = ['orders', 'menu items', 'customers', 'sales']
        elif clarification_type == 'time_period':
            # Suggest common time periods
            clarification_data['options'] = ['today', 'yesterday', 'this week', 'last week', 'this month', 'last month']
        
        # Format the clarification response
        response = self.response_service.format_response(
            response_type='clarification',
            data=clarification_data,
            context=context.to_dict(),
            metadata={**query_info}
        )
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the query processor.
        
        Returns:
            Dictionary with metric information
        """
        metrics = self.metrics.copy()
        metrics['data_access_metrics'] = self.data_access.get_performance_metrics()
        return metrics
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the query processor and its dependencies.
        
        Returns:
            Dict with health status information
        """
        start_time = time.time()
        
        # Check data access health
        data_access_health = self.data_access.health_check()
        
        # Check response service health
        response_service_health = self.response_service.health_check()
        
        # Overall status is OK if all components are OK
        status = "ok"
        if data_access_health.get('status') != 'ok' or response_service_health.get('status') != 'ok':
            status = "error"
        
        health_info = {
            "service": "query_processor",
            "status": status,
            "components": {
                "data_access": data_access_health,
                "response_service": response_service_health
            },
            "metrics": {
                "total_queries": self.metrics['total_queries'],
                "success_rate": (
                    self.metrics['successful_queries'] / self.metrics['total_queries'] * 100
                    if self.metrics['total_queries'] > 0 else 0
                )
            },
            "response_time": time.time() - start_time
        }
        
        return health_info 