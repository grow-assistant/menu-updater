"""
Clarification Service for Swoop AI Conversational Query Flow.

This module provides functionality for handling ambiguous queries and generating
clarification questions, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Union
import logging
import re

logger = logging.getLogger(__name__)


class ClarificationService:
    """
    Handles ambiguous queries and manages the clarification workflow.
    
    Responsibilities:
    - Detecting missing information in queries
    - Generating appropriate clarification questions
    - Tracking clarification state
    - Incorporating clarification responses into the original query
    """
    
    # Types of clarification that can be requested
    CLARIFICATION_TYPES = {
        'time': 'time period',
        'entity': 'specific item or category',
        'filter': 'filter conditions',
        'action': 'action details',
        'confirmation': 'confirmation'
    }
    
    def __init__(self):
        """Initialize the clarification service."""
        logger.info("Initialized ClarificationService")
    
    def check_needs_clarification(self, query_classification: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Check if a query needs clarification based on its classification.
        
        Args:
            query_classification: Result from query classifier
            context: Optional conversation context
            
        Returns:
            Dict containing:
                - needs_clarification: True|False
                - missing_parameters: List of missing parameter types
                - clarification_question: Suggested question to ask
                - clarification_type: Type of clarification needed
        """
        logger.debug("Checking if query needs clarification")
        
        result = {
            'needs_clarification': False,
            'missing_parameters': [],
            'clarification_question': None,
            'clarification_type': None
        }
        
        # If the classifier already determined clarification is needed, use that
        if query_classification.get('needs_clarification', False):
            result['needs_clarification'] = True
            result['clarification_question'] = query_classification.get('clarification_question')
            
            # Try to determine what type of clarification is needed
            query_type = query_classification.get('query_type')
            extracted_params = query_classification.get('extracted_params', {})
            
            # Check for missing time references in order history queries
            if query_type == 'order_history':
                time_refs = extracted_params.get('time_references', {})
                if time_refs.get('is_ambiguous', False):
                    result['missing_parameters'].append('time_period')
                    result['clarification_type'] = 'time'
            
            # Check for missing entities in action requests
            elif query_type == 'action':
                entities = extracted_params.get('entities', {})
                actions = extracted_params.get('actions', [])
                
                # If we have actions but no entities, we need entity clarification
                if actions and not any(entities.values()):
                    result['missing_parameters'].append('entity')
                    result['clarification_type'] = 'entity'
                
                # If we have actions that need values, we need action clarification
                for action in actions:
                    if action.get('type') == 'update' and 'value' not in action:
                        result['missing_parameters'].append('action_value')
                        result['clarification_type'] = 'action'
            
            # If we couldn't determine a specific clarification type, use a generic one
            if not result['clarification_type']:
                result['clarification_type'] = 'general'
        
        return result
    
    def process_clarification_response(self, original_query: str, clarification_response: str, 
                                      clarification_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a response to a clarification question.
        
        Args:
            original_query: The original ambiguous query
            clarification_response: The user's response to the clarification
            clarification_type: The type of clarification requested
            context: Optional conversation context
            
        Returns:
            Dict containing:
                - updated_query: The combined query with clarification
                - confidence: Confidence in the processed result
                - context_updates: Updates to make to the context
        """
        result = {
            "updated_query": original_query,
            "confidence": 0.7,
            "context_updates": {}
        }
        
        # Handle different types of clarifications
        if clarification_type == 'confirmation':
            # For confirmation, we just determine if the user confirmed or denied
            is_confirmed = self._process_confirmation(clarification_response)
            result["is_confirmed"] = is_confirmed
            result["confidence"] = 0.9 if is_confirmed else 0.8
            return result
        
        # For other types, we need to update the original query
        updated_query = original_query
        
        # Time clarification
        if clarification_type == 'time':
            # Extract time expression and append to the original query
            updated_query = self._combine_with_time_clarification(original_query, clarification_response)
            
        # Entity clarification
        elif clarification_type == 'entity':
            # Extract entity and combine with the original query
            updated_query = self._combine_with_entity_clarification(original_query, clarification_response)
            
        # Filter clarification
        elif clarification_type == 'filter':
            # Extract filter conditions and combine with the original query
            updated_query = self._combine_with_filter_clarification(original_query, clarification_response)
            
        # Action clarification    
        elif clarification_type == 'action':
            # Extract action details and combine with the original query
            updated_query = self._combine_with_action_clarification(original_query, clarification_response)
            
        # Update the result
        result["updated_query"] = updated_query
        result["context_updates"] = {
            "clarification_applied": True,
            "clarification_type": clarification_type,
            "original_query": original_query,
            "clarification_response": clarification_response
        }
            
        return result
    
    def process_correction(self, correction: Dict[str, Any], original_query: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a correction to a previous query.
        
        Args:
            correction: The correction query classification result
            original_query: The original query classification that's being corrected
            context: Optional conversation context
            
        Returns:
            Dict containing:
                - updated_query: The corrected query
                - corrected_parameters: Parameters that were corrected
                - confidence: Confidence in the correction
                - context_updates: Updates to make to the context
        """
        # Extract correction parameters
        correction_parameters = correction.get("parameters", {})
        correction_text = correction_parameters.get("correction_text", "")
        correction_target = correction_parameters.get("correction_target", "unknown")
        
        # Start with the original query parameters
        original_parameters = original_query.get("parameters", {})
        corrected_parameters = original_parameters.copy()
        
        # Apply corrections based on the target
        if correction_target == "time_period":
            # Extract time period from correction
            time_refs = self._extract_time_references(correction_text)
            if time_refs:
                corrected_parameters["time_references"] = time_refs
                
        elif correction_target in ["item", "category"]:
            # Extract entities from correction
            entities = self._extract_entities(correction_text)
            if entities:
                if "entities" not in corrected_parameters:
                    corrected_parameters["entities"] = {}
                    
                # Update the appropriate entity type
                if correction_target == "item" and entities.get("items"):
                    corrected_parameters["entities"]["items"] = entities.get("items")
                elif correction_target == "category" and entities.get("categories"):
                    corrected_parameters["entities"]["categories"] = entities.get("categories")
                    
        elif correction_target == "price":
            # Extract price from correction
            price_match = re.search(r'\$?(\d+(?:\.\d{1,2})?)', correction_text)
            if price_match:
                price = price_match.group(1)
                # Update the price in actions
                if "actions" in corrected_parameters:
                    for action in corrected_parameters["actions"]:
                        if action.get("field") == "price":
                            action["value"] = price
                else:
                    corrected_parameters["actions"] = [{
                        "type": "update",
                        "field": "price",
                        "value": price
                    }]
                    
        elif correction_target == "action":
            # Extract actions from correction
            actions = self._extract_actions(correction_text)
            if actions:
                corrected_parameters["actions"] = actions
        
        # Create a new query with corrected parameters
        corrected_query = {
            "query_type": original_query.get("query_type"),
            "parameters": corrected_parameters,
            "confidence": min(0.8, original_query.get("confidence", 0.5) + 0.2),
            "clarification_needed": False
        }
        
        # Generate a reconstructed natural language query that combines both
        reconstructed_query = self._reconstruct_query(original_query, correction, corrected_parameters)
        
        return {
            "updated_query": corrected_query,
            "reconstructed_text": reconstructed_query,
            "corrected_parameters": {correction_target: corrected_parameters},
            "confidence": corrected_query["confidence"],
            "context_updates": {
                "correction_applied": True,
                "correction_target": correction_target,
                "original_query": original_query,
                "correction": correction
            }
        }
    
    def _combine_with_time_clarification(self, original_query: str, clarification_response: str) -> str:
        """Combine original query with time clarification response."""
        # Clean up the response - remove unnecessary words
        time_expression = clarification_response.strip()
        time_expression = re.sub(r'^(?:for|during|in|on|at)\s+', '', time_expression, flags=re.IGNORECASE)
        
        # Determine the best way to combine
        if re.search(r'(when|what time|what period|which date)', original_query, re.IGNORECASE):
            # Replace the question with the answer
            combined = re.sub(r'\b(?:when|what time|what period|which date)\b.*?(?=\?|$)', time_expression, original_query, flags=re.IGNORECASE)
        else:
            # Append the time expression if it doesn't already contain similar information
            if not re.search(r'(?:last|this|next|previous|yesterday|today|tomorrow|\d{1,2}[/-]\d{1,2})', original_query, re.IGNORECASE):
                combined = f"{original_query} for {time_expression}"
            else:
                # If there's already time information, replace it
                combined = re.sub(r'(?:last|this|next|previous|yesterday|today|tomorrow|\d{1,2}[/-]\d{1,2})[^?]*', time_expression, original_query, flags=re.IGNORECASE)
                
        return combined
    
    def _combine_with_entity_clarification(self, original_query: str, clarification_response: str) -> str:
        """Combine original query with entity clarification response."""
        # Clean up the response - remove unnecessary words
        entity_expression = clarification_response.strip()
        entity_expression = re.sub(r'^(?:for|the|about)\s+', '', entity_expression, flags=re.IGNORECASE)
        
        # Determine the best way to combine
        if re.search(r'(which|what) (?:item|category|product|menu)', original_query, re.IGNORECASE):
            # Replace the question with the answer
            combined = re.sub(r'\b(?:which|what) (?:item|category|product|menu)\b.*?(?=\?|$)', entity_expression, original_query, flags=re.IGNORECASE)
        else:
            # Append the entity expression
            combined = f"{original_query} for {entity_expression}"
                
        return combined
    
    def _combine_with_filter_clarification(self, original_query: str, clarification_response: str) -> str:
        """Combine original query with filter clarification response."""
        # Clean up the response - remove unnecessary words
        filter_expression = clarification_response.strip()
        
        # Determine the best way to combine
        if re.search(r'(how|which|what).*(?:filter|condition|restriction)', original_query, re.IGNORECASE):
            # Replace the question with the answer
            combined = re.sub(r'\b(?:how|which|what).*?(?:filter|condition|restriction)\b.*?(?=\?|$)', filter_expression, original_query, flags=re.IGNORECASE)
        else:
            # Append the filter expression
            combined = f"{original_query} {filter_expression}"
                
        return combined
    
    def _combine_with_action_clarification(self, original_query: str, clarification_response: str) -> str:
        """Combine original query with action clarification response."""
        # Clean up the response - remove unnecessary words
        action_expression = clarification_response.strip()
        
        # Check if it's a price value
        price_match = re.search(r'\$?(\d+(?:\.\d{1,2})?)', action_expression)
        if price_match and re.search(r'(?:price|cost)', original_query, re.IGNORECASE):
            # Replace the price or add it if not present
            if re.search(r'\$?(\d+(?:\.\d{1,2})?)', original_query):
                combined = re.sub(r'\$?(\d+(?:\.\d{1,2})?)', f"${price_match.group(1)}", original_query)
            else:
                combined = f"{original_query} to ${price_match.group(1)}"
            return combined
            
        # Determine the best way to combine for other action types
        if re.search(r'(?:what|which|how).*(?:action|change|update|modify)', original_query, re.IGNORECASE):
            # Replace the question with the answer
            combined = re.sub(r'\b(?:what|which|how).*?(?:action|change|update|modify)\b.*?(?=\?|$)', action_expression, original_query, flags=re.IGNORECASE)
        else:
            # Append the action expression
            combined = f"{original_query} {action_expression}"
                
        return combined
    
    def _extract_time_references(self, text: str) -> Dict[str, Any]:
        """Extract time references from text."""
        # This is a simplified implementation
        # In a real system, you'd use the TemporalAnalysisService
        time_refs = {}
        
        # Check for time periods
        period_matches = re.findall(r'(last|this|next|previous) (day|week|month|year)', text, re.IGNORECASE)
        if period_matches:
            period_type = period_matches[0][1].lower()
            period_qualifier = period_matches[0][0].lower()
            time_refs["period_type"] = period_type
            time_refs["period_qualifier"] = period_qualifier
            
        # Check for specific dates
        date_matches = re.findall(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', text)
        if date_matches:
            time_refs["specific_date"] = {
                "month": date_matches[0][0],
                "day": date_matches[0][1],
                "year": date_matches[0][2] if len(date_matches[0]) > 2 else None
            }
            
        return time_refs
    
    def _extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract entities from text."""
        # This is a simplified implementation
        # In a real system, you'd use the EntityResolutionService
        entities = {
            "items": [],
            "categories": []
        }
        
        # Check for quoted items
        item_matches = re.findall(r'"([^"]+)"', text)
        if item_matches:
            for item in item_matches:
                entities["items"].append({"name": item, "confidence": 0.9})
                
        # Simple category detection
        category_keywords = ["appetizer", "entree", "dessert", "drink", "beverage", "side"]
        for keyword in category_keywords:
            if keyword in text.lower():
                entities["categories"].append({"name": keyword, "confidence": 0.8})
                
        return entities
    
    def _extract_actions(self, text: str) -> List[Dict[str, Any]]:
        """Extract actions from text."""
        # This is a simplified implementation
        actions = []
        
        # Check for price changes
        price_match = re.search(r'(change|update|set) (?:the )?price (?:to|of) \$?(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        if price_match:
            actions.append({
                "type": "update",
                "field": "price",
                "value": price_match.group(2)
            })
            
        # Check for enable/disable
        status_match = re.search(r'(enable|disable|activate|deactivate)', text, re.IGNORECASE)
        if status_match:
            status = "enabled" if status_match.group(1).lower() in ["enable", "activate"] else "disabled"
            actions.append({
                "type": "update",
                "field": "status",
                "value": status
            })
            
        return actions
    
    def _reconstruct_query(self, original_query: Dict[str, Any], correction: Dict[str, Any], 
                          corrected_parameters: Dict[str, Any]) -> str:
        """Reconstruct a natural language query from the original and correction."""
        # Get the original query type and extract key information
        query_type = original_query.get("query_type")
        correction_target = correction.get("parameters", {}).get("correction_target", "unknown")
        
        # Start with template based on query type
        if query_type == "order_history":
            reconstructed = "Show me the order history"
            
            # Add time period if available
            time_refs = corrected_parameters.get("time_references", {})
            if time_refs.get("period_type") and time_refs.get("period_qualifier"):
                period = f"{time_refs['period_qualifier']} {time_refs['period_type']}"
                reconstructed += f" for {period}"
                
            # Add entities if available
            entities = corrected_parameters.get("entities", {})
            items = entities.get("items", [])
            categories = entities.get("categories", [])
            
            if items:
                item_names = [item["name"] for item in items[:3]]
                reconstructed += f" for {', '.join(item_names)}"
            elif categories:
                category_names = [cat["name"] for cat in categories[:3]]
                reconstructed += f" for the {', '.join(category_names)} category"
                
        elif query_type == "menu":
            reconstructed = "Show me the menu"
            
            # Add entities if available
            entities = corrected_parameters.get("entities", {})
            items = entities.get("items", [])
            categories = entities.get("categories", [])
            
            if items:
                item_names = [item["name"] for item in items[:3]]
                reconstructed += f" information for {', '.join(item_names)}"
            elif categories:
                category_names = [cat["name"] for cat in categories[:3]]
                reconstructed += f" for the {', '.join(category_names)} category"
                
        elif query_type == "action":
            # Start with the action type
            actions = corrected_parameters.get("actions", [])
            if not actions:
                reconstructed = "Update the menu"
            else:
                action = actions[0]
                
                if action.get("field") == "price" and action.get("value"):
                    reconstructed = f"Change the price to ${action['value']}"
                elif action.get("field") == "status":
                    status = "Enable" if action.get("value") == "enabled" else "Disable"
                    reconstructed = f"{status}"
                else:
                    reconstructed = "Update"
                    
                # Add the target entity
                entities = corrected_parameters.get("entities", {})
                items = entities.get("items", [])
                categories = entities.get("categories", [])
                
                if items:
                    item_names = [item["name"] for item in items[:3]]
                    reconstructed += f" {', '.join(item_names)}"
                elif categories:
                    category_names = [cat["name"] for cat in categories[:3]]
                    reconstructed += f" the {', '.join(category_names)} category"
        else:
            # Default to the original query text
            reconstructed = "Query with corrections applied"
            
        return reconstructed
        
    def _process_confirmation(self, response: str) -> bool:
        """
        Process a confirmation response to determine if it's affirmative or negative.
        
        Args:
            response: User's response to a confirmation question
            
        Returns:
            True if confirmed, False if denied
        """
        response_lower = response.lower()
        
        # Check for affirmative responses
        affirmative = ['yes', 'yeah', 'yep', 'correct', 'right', 'ok', 'okay', 'sure', 'confirm', 'confirmed', 'approve', 'approved']
        for word in affirmative:
            if re.search(r'\b' + word + r'\b', response_lower):
                return True
                
        # Check for negative responses
        negative = ['no', 'nope', 'not', 'don\'t', 'do not', 'wrong', 'incorrect', 'cancel', 'stop', 'deny', 'rejected', 'negative']
        for word in negative:
            if re.search(r'\b' + word + r'\b', response_lower):
                return False
                
        # Default to True for responses that don't contain clear indicators
        # This is a simplified approach and could be improved
        return True
    
    def generate_clarification_question(self, query_classification: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate an appropriate clarification question based on what's missing.
        
        Args:
            query_classification: Result from query classifier
            context: Optional conversation context
            
        Returns:
            Clarification question string
        """
        # If the classifier already provided a clarification question, use it
        if query_classification.get('clarification_question'):
            return query_classification['clarification_question']
            
        # Otherwise, generate a question based on what's missing
        query_type = query_classification.get('query_type')
        
        if query_type == 'order_history':
            return "For what time period would you like to see this information?"
            
        elif query_type == 'menu':
            return "Which menu items or categories are you interested in?"
            
        elif query_type == 'action':
            actions = query_classification.get('extracted_params', {}).get('actions', [])
            if actions:
                action = actions[0]
                action_type = action.get('type')
                field = action.get('field')
                
                if action_type == 'update' and field == 'price':
                    return "Which item's price would you like to update?"
                elif action_type == 'update' and field == 'status':
                    return "Which item would you like to update?"
            
            return "What action would you like to perform?"
            
        # Default question if we can't determine a specific one
        return "Could you please provide more information?"
    
    def generate_confirmation_question(self, action: Dict[str, Any]) -> str:
        """
        Generate a confirmation question for an action.
        
        Args:
            action: Action dictionary with details of the action
            
        Returns:
            Confirmation question string
        """
        action_type = action.get('type')
        field = action.get('field')
        entity_type = action.get('entity_type', 'item')
        entity_name = action.get('entity_name', 'this item')
        value = action.get('value')
        
        if action_type == 'update':
            if field == 'price':
                return f"Are you sure you want to change the price of {entity_name} to ${value}?"
            elif field == 'status':
                status_action = 'enable' if value == 'enabled' else 'disable'
                return f"Are you sure you want to {status_action} {entity_name}?"
        
        # Generic confirmation question
        return "Are you sure you want to proceed with this action?"
    
    def update_context_with_clarification(self, context: Dict[str, Any], clarification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the conversation context with clarification results.
        
        Args:
            context: Current conversation context
            clarification_result: Result from process_clarification_response
            
        Returns:
            Updated context dictionary
        """
        # Handle different types of resolved parameters
        resolved_params = clarification_result.get('resolved_parameters', {})
        
        # Handle time period clarification
        if 'time_period' in resolved_params:
            if 'time_references' not in context:
                context['time_references'] = {}
            context['time_references']['relative_references'] = [resolved_params['time_period']]
        
        # Handle entity clarification
        if 'entity' in resolved_params:
            entity = resolved_params['entity']
            # For simplicity, we're just adding it as an item, but in a real implementation
            # we would need to determine the entity type
            if 'active_entities' not in context:
                context['active_entities'] = {'items': [], 'categories': [], 'options': [], 'option_items': []}
            context['active_entities']['items'].append({'name': entity, 'confidence': 0.9})
        
        # Handle filter clarification
        if 'filter' in resolved_params:
            if 'active_filters' not in context:
                context['active_filters'] = []
            # In a real implementation, we would parse the filter string
            # For now, we'll just store it as a raw filter
            context['active_filters'].append({'raw_filter': resolved_params['filter']})
        
        # Handle action value clarification
        if 'action_value' in resolved_params:
            if 'pending_actions' not in context or not context['pending_actions']:
                context['pending_actions'] = [{'type': 'update', 'value': resolved_params['action_value']}]
            else:
                context['pending_actions'][0]['value'] = resolved_params['action_value']
                
        # Update clarification state
        context['clarification_state'] = 'RESOLVED'
            
        return context 