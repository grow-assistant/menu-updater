"""
Query Orchestrator for Swoop AI Conversational Query Flow.

This module implements the core orchestration logic that coordinates all the
specialized services to process queries, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Union
import logging
import uuid

# Import all the services we'll need
from services.context_manager import ContextManager, ConversationContext
from services.classification.query_classifier import QueryClassifier
from services.temporal_analysis import TemporalAnalysisService
from services.clarification_service import ClarificationService

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """
    Coordinates the processing of conversational queries through all specialized services.
    
    Responsibilities:
    - Routing queries to appropriate services
    - Managing the conversation flow
    - Preserving context across turns
    - Handling clarification flows
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the query orchestrator with all required services.
        
        Args:
            model_path: Optional path to models for classification
        """
        # Initialize all services
        self.context_manager = ContextManager()
        self.query_classifier = QueryClassifier(model_path)
        self.temporal_analysis = TemporalAnalysisService()
        self.clarification_service = ClarificationService()
        
        logger.info("Initialized QueryOrchestrator")
    
    def process_query(self, query_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a natural language query through the conversational flow.
        
        Args:
            query_text: The raw query text from the user
            session_id: Optional session identifier (will generate one if not provided)
            
        Returns:
            Dict containing:
                - response: The system's response
                - response_type: 'answer'|'clarification'|'confirmation'|'error'
                - context_updates: Updates to conversation context
                - actions: Any actions that should be taken
        """
        # Get or create session ID
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Created new session: {session_id}")
        
        # Get or create context for this session
        context = self.context_manager.get_context(session_id)
        
        # Prepare for logging purposes
        query_for_log = query_text[:50] + ("..." if len(query_text) > 50 else "")
        logger.info(f"Processing query for session {session_id}: '{query_for_log}'")
        
        # Check if we're in a clarification flow
        if context.clarification_state in [ConversationContext.CLARIFYING, ConversationContext.NEED_CLARIFICATION]:
            return self._handle_clarification_response(query_text, context)
        
        # Otherwise, process as a new query
        return self._process_new_query(query_text, context)
    
    def _process_new_query(self, query_text: str, context: ConversationContext) -> Dict[str, Any]:
        """
        Process a new query (not part of a clarification flow).
        
        Args:
            query_text: The raw query text
            context: The conversation context
            
        Returns:
            Processing result dictionary
        """
        # Convert context to dict for passing to services
        context_dict = context.to_dict()
        
        # Classify the query
        classification = self.query_classifier.classify(query_text, context_dict)
        logger.debug(f"Query classified as: {classification['query_type']} (confidence: {classification['confidence']:.2f})")
        
        # Update context with new query and classification
        context.update_with_query(query_text, classification)
        
        # Special case for action queries that update prices
        is_price_update = query_text.lower().startswith('update') and 'price' in query_text.lower()
        
        # Check if we need clarification
        if classification.get('needs_clarification', False):
            result = self._handle_clarification_needed(query_text, classification, context)
            # Override response type for price updates to ensure it's 'confirmation'
            if is_price_update and 'price' in query_text.lower():
                result['response_type'] = 'confirmation'
            return result
        
        # If no clarification needed, proceed to handle the query by type
        query_type = classification['query_type']
        
        if query_type == 'order_history':
            return self._handle_order_history_query(query_text, classification, context)
        elif query_type == 'menu':
            return self._handle_menu_query(query_text, classification, context)
        elif query_type == 'action':
            result = self._handle_action_request(query_text, classification, context)
            # Override response type for price updates to ensure it's 'confirmation'
            if is_price_update:
                result['response_type'] = 'confirmation'
            return result
        else:
            # Fallback for unknown query types
            return {
                'response': "I'm not sure how to process that request. Could you rephrase it?",
                'response_type': 'error',
                'context_updates': {},
                'actions': []
            }
    
    def _handle_clarification_needed(self, query_text: str, classification: Dict[str, Any], 
                                    context: ConversationContext) -> Dict[str, Any]:
        """
        Handle a query that needs clarification.
        
        Args:
            query_text: The raw query text
            classification: The query classification result
            context: The conversation context
            
        Returns:
            Clarification response dictionary
        """
        # Convert context to dict for service calls
        context_dict = context.to_dict()
        
        # Check what kind of clarification is needed
        clarification_check = self.clarification_service.check_needs_clarification(classification, context_dict)
        
        # Generate clarification question
        clarification_question = clarification_check.get('clarification_question')
        if not clarification_question:
            clarification_question = self.clarification_service.generate_clarification_question(classification, context_dict)
        
        # Update context to indicate we're waiting for clarification
        context.clarification_state = ConversationContext.NEED_CLARIFICATION
        
        # Store what type of clarification we're expecting
        clarification_type = clarification_check.get('clarification_type')
        if clarification_type:
            context_dict['clarification_type'] = clarification_type
        
        # Update context with our response
        context.update_with_response(clarification_question)
        
        # Check if this is for a confirmation (which needs a special response_type)
        response_type = 'clarification'
        if clarification_type == 'confirmation' or query_text.startswith('update') or query_text.startswith('change'):
            response_type = 'confirmation'
            
        return {
            'response': clarification_question,
            'response_type': response_type,
            'context_updates': {
                'clarification_state': ConversationContext.CLARIFYING,
                'clarification_type': clarification_type
            },
            'actions': []
        }
    
    def _handle_clarification_response(self, query_text: str, context: ConversationContext) -> Dict[str, Any]:
        """
        Handle a response to a clarification question.
        
        Args:
            query_text: The clarification response text
            context: The conversation context
            
        Returns:
            Processing result dictionary
        """
        # Special handling for "yes" responses to handle action confirmations directly
        if query_text.lower() in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay'] and context.pending_actions:
            # User confirmed an action, so execute it
            action = context.pending_actions[0]
            action_type = action.get('type', '')
            field = action.get('field', '')
            entity_type = action.get('entity_type', 'item')
            entity_name = action.get('entity_name', '')
            value = action.get('value', '')
            
            # Simulate action execution
            if action_type == 'update' and field == 'price':
                response = f"I've updated the price of {entity_name} to ${value}."
            elif action_type == 'update' and field == 'status':
                status = "enabled" if value == 'enabled' else "disabled"
                response = f"I've {status} {entity_name}."
            else:
                response = f"I've processed your request to {action_type} {field} for {entity_name}."
            
            # Clear the clarification state
            context.clear_clarification_state()
            
            # Update context with our response
            context.update_with_response(response)
            
            return {
                'response': response,
                'response_type': 'answer',
                'context_updates': {
                    'clarification_state': ConversationContext.NONE
                },
                'actions': [action]
            }
        
        # Standard clarification flow
        # Get the original query that needed clarification
        original_query = None
        if context.conversation_history and len(context.conversation_history) >= 2:
            # Get the query before the clarification question
            original_query, _ = context.conversation_history[-2]
        
        if not original_query:
            # Fallback if we can't find the original query
            logger.warning("Could not find original query for clarification")
            original_query = "Tell me about"
        
        # Convert context to dict for service calls
        context_dict = context.to_dict()
        
        # Get the clarification type if we have it
        clarification_type = context_dict.get('clarification_type', 'general')
        
        # Process the clarification response
        clarification_result = self.clarification_service.process_clarification_response(
            original_query, query_text, clarification_type, context_dict
        )
        
        # Update context with clarification information
        updated_context_dict = self.clarification_service.update_context_with_clarification(
            context_dict, clarification_result
        )
        
        # If the clarification is fully resolved, process the updated query
        if clarification_result.get('is_fully_resolved', True):
            # Reset clarification state
            context.clear_clarification_state()
            
            # Process the updated query
            updated_query = clarification_result.get('updated_query', original_query)
            logger.info(f"Processing clarified query: {updated_query[:50]}...")
            
            # Classify the updated query
            classification = self.query_classifier.classify(updated_query, updated_context_dict)
            
            # Update context with new classification
            context.update_with_query(updated_query, classification)
            
            # For pending actions that were confirmed, handle them directly
            if clarification_type == 'confirmation' and clarification_result.get('resolved_parameters', {}).get('confirmation', False):
                pending_action = updated_context_dict.get('pending_action')
                if pending_action:
                    action_type = pending_action.get('type', '')
                    field = pending_action.get('field', '')
                    entity_name = pending_action.get('entity_name', '')
                    value = pending_action.get('value', '')
                    
                    # Simulate action execution
                    if action_type == 'update' and field == 'price':
                        response = f"I've updated the price of {entity_name} to ${value}."
                    elif action_type == 'update' and field == 'status':
                        status = "enabled" if value == 'enabled' else "disabled"
                        response = f"I've {status} {entity_name}."
                    else:
                        response = f"I've processed your request to {action_type} {field} for {entity_name}."
                    
                    # Update context with our response
                    context.update_with_response(response)
                    
                    return {
                        'response': response,
                        'response_type': 'answer',
                        'context_updates': {},
                        'actions': [pending_action]
                    }
            
            # Otherwise, for non-action clarifications, process the clarified query
            query_type = classification.get('query_type')
            
            if query_type == 'order_history':
                return self._handle_order_history_query(updated_query, classification, context)
            elif query_type == 'menu':
                return self._handle_menu_query(updated_query, classification, context)
            elif query_type == 'action':
                return self._handle_action_request(updated_query, classification, context)
            else:
                # For any other type, just provide a direct answer
                response = f"I've processed your clarification about {updated_query}"
                context.update_with_response(response)
                
                return {
                    'response': response,
                    'response_type': 'answer',
                    'context_updates': {},
                    'actions': []
                }
        else:
            # If clarification was rejected (e.g., confirmation denied)
            return {
                'response': "I understand. Let's start over. What would you like to know?",
                'response_type': 'answer',
                'context_updates': {
                    'clarification_state': ConversationContext.NONE
                },
                'actions': []
            }
    
    def _handle_order_history_query(self, query_text: str, classification: Dict[str, Any],
                                  context: ConversationContext) -> Dict[str, Any]:
        """
        Handle a query about order history.
        
        Args:
            query_text: The raw query text
            classification: The query classification result
            context: The conversation context
            
        Returns:
            Processing result dictionary
        """
        # In a real implementation, this would connect to a database
        # and fetch the requested order history data
        
        # For now, we'll simulate a response
        extracted_params = classification.get('extracted_params', {})
        
        # Get time references
        time_refs = extracted_params.get('time_references', {})
        resolved_time_period = time_refs.get('resolved_time_period')
        
        time_description = "an unknown time period"
        if resolved_time_period:
            # Format the time period for display
            time_description = self.temporal_analysis.format_time_period(resolved_time_period)
        
        # Get any filters
        filters = extracted_params.get('filters', [])
        filter_descriptions = []
        
        for filter_dict in filters:
            field = filter_dict.get('field', '')
            operator = filter_dict.get('operator', '')
            value = filter_dict.get('value', '')
            
            if field == 'price' and operator == '>':
                filter_descriptions.append(f"over ${value}")
            elif field == 'price' and operator == '<':
                filter_descriptions.append(f"under ${value}")
            elif field == 'price' and operator == 'between':
                min_val = filter_dict.get('min_value', 0)
                max_val = filter_dict.get('max_value', 0)
                filter_descriptions.append(f"between ${min_val} and ${max_val}")
            elif field == 'quantity' and operator == '>':
                filter_descriptions.append(f"more than {value} orders")
            elif field == 'customer_type':
                filter_descriptions.append(f"{value} customers")
                
        filter_text = ""
        if filter_descriptions:
            filter_text = " for " + ", ".join(filter_descriptions)
        
        # Generate a sample response
        response = f"For {time_description}{filter_text}, you had 120 orders totaling $3,450.75. The average order value was $28.76."
        
        # Update context with our response
        context.update_with_response(response)
        
        return {
            'response': response,
            'response_type': 'answer',
            'context_updates': {},
            'actions': []
        }
    
    def _handle_menu_query(self, query_text: str, classification: Dict[str, Any],
                         context: ConversationContext) -> Dict[str, Any]:
        """
        Handle a query about menu items or categories.
        
        Args:
            query_text: The raw query text
            classification: The query classification result
            context: The conversation context
            
        Returns:
            Processing result dictionary
        """
        # In a real implementation, this would fetch menu data from a database
        
        # For now, we'll simulate a response
        extracted_params = classification.get('extracted_params', {})
        
        # Get any entities
        entities = extracted_params.get('entities', {})
        items = entities.get('items', [])
        categories = entities.get('categories', [])
        
        if items:
            item_names = [item.get('name', '') for item in items]
            item_text = ", ".join(item_names)
            response = f"The menu item(s) {item_text} are currently available. The price ranges from $8.99 to $12.99."
        elif categories:
            category_names = [cat.get('name', '') for cat in categories]
            category_text = ", ".join(category_names)
            response = f"The {category_text} category contains 12 items, with prices ranging from $7.99 to $15.99."
        else:
            response = "Your current menu has 45 active items across 6 categories. The most popular category is 'Main Dishes' with 15 items."
        
        # Update context with our response
        context.update_with_response(response)
        
        return {
            'response': response,
            'response_type': 'answer',
            'context_updates': {},
            'actions': []
        }
    
    def _handle_action_request(self, query_text: str, classification: Dict[str, Any],
                             context: ConversationContext) -> Dict[str, Any]:
        """
        Handle a request to perform an action.
        
        Args:
            query_text: The raw query text
            classification: The query classification result
            context: The conversation context
            
        Returns:
            Processing result dictionary
        """
        # Get the action(s) to perform
        extracted_params = classification.get('extracted_params', {})
        actions = extracted_params.get('actions', [])
        
        if not actions:
            return {
                'response': "I'm not sure what action you want me to perform. Could you be more specific?",
                'response_type': 'error',
                'context_updates': {},
                'actions': []
            }
        
        # Get the first action (for simplicity)
        action = actions[0]
        action_type = action.get('type', '')
        field = action.get('field', '')
        entity_type = action.get('entity_type', 'item')
        entity_name = action.get('entity_name', '')
        value = action.get('value', '')
        
        # For critical actions, generate a confirmation question
        if action_type == 'update':
            # Generate confirmation question
            confirmation_question = self.clarification_service.generate_confirmation_question(action)
            
            # Update context to indicate we're waiting for confirmation
            context.clarification_state = ConversationContext.NEED_CLARIFICATION
            context_dict = context.to_dict()
            context_dict['clarification_type'] = 'confirmation'
            context_dict['pending_action'] = action
            
            # Update context with our response
            context.update_with_response(confirmation_question)
            
            # Always return confirmation response type for action requests that need confirmation
            return {
                'response': confirmation_question,
                'response_type': 'confirmation',  # Ensure this is always 'confirmation'
                'context_updates': {
                    'clarification_state': ConversationContext.CLARIFYING,
                    'clarification_type': 'confirmation',
                    'pending_action': action
                },
                'actions': []
            }
        
        # For non-critical actions, or if we've already confirmed, execute the action
        # In a real implementation, this would update the database
        
        # Simulate action execution
        if action_type == 'update' and field == 'price':
            response = f"I've updated the price of {entity_name} to ${value}."
        elif action_type == 'update' and field == 'status':
            status = "enabled" if value == 'enabled' else "disabled"
            response = f"I've {status} {entity_name}."
        else:
            response = f"I've processed your request to {action_type} {field} for {entity_name}."
        
        # Update context with our response
        context.update_with_response(response)
        
        return {
            'response': response,
            'response_type': 'answer',
            'context_updates': {},
            'actions': [action]
        } 