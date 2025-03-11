"""
Query Classifier for Swoop AI Conversational Query Flow.

This module provides functionality for classifying natural language queries
into different types and extracting parameters, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Union
import re
import logging
import os
from pathlib import Path

# Import services that might be needed for parameter extraction
from services.temporal_analysis import TemporalAnalysisService

logger = logging.getLogger(__name__)


class QueryClassifier:
    """
    Classifies natural language queries into different types and extracts parameters.
    
    Types of queries:
    - order_history: Queries about past orders
    - menu: Queries about menu items, categories, etc.
    - action: Requests to perform actions like price changes
    - clarification: Responses to clarification questions
    """
    
    # Query type keywords
    ORDER_HISTORY_KEYWORDS = [
        'order', 'orders', 'sale', 'sales', 'transaction', 'transactions',
        'sold', 'purchased', 'bought', 'ordered', 'revenue', 'earnings',
        'profit', 'income', 'volume', 'history', 'historical'
    ]
    
    MENU_KEYWORDS = [
        'menu', 'item', 'items', 'category', 'categories', 'price', 'prices',
        'cost', 'costs', 'option', 'options', 'available', 'unavailable',
        'enabled', 'disabled', 'active', 'inactive'
    ]
    
    ACTION_KEYWORDS = [
        'change', 'update', 'modify', 'set', 'make', 'enable', 'disable',
        'activate', 'deactivate', 'add', 'remove', 'delete', 'create',
        'edit', 'adjust', 'increase', 'decrease', 'turn on', 'turn off'
    ]
    
    CLARIFICATION_KEYWORDS = [
        'yes', 'no', 'correct', 'incorrect', 'right', 'wrong',
        'that\'s right', 'that\'s wrong', 'exactly', 'not exactly'
    ]
    
    CORRECTION_KEYWORDS = [
        'correction', 'correcting', 'correct this', 'fix', 'fixed', 'fixing',
        'mistake', 'error', 'wrong', 'not right', 'incorrect', 
        'i meant', 'i actually meant', 'i wanted', 'what i meant',
        'not what i meant', 'misunderstood', 'you misunderstood'
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the query classifier.
        
        Args:
            model_path: Optional path to a trained model for classification
        """
        self.model_path = model_path
        self.temporal_analysis = TemporalAnalysisService()
        
        # Load model if provided (placeholder for actual model loading)
        self.model = None
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading model from {model_path}")
            # TODO: Implement actual model loading when available
            # self.model = load_model(model_path)
        
        logger.info("Initialized QueryClassifier")
        
    def classify(self, query_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a natural language query into a type and extract parameters.
        
        Args:
            query_text: The text of the query to classify
            context: Optional conversation context
            
        Returns:
            Dictionary containing:
            - query_type: The type of query (order_history, menu, action, clarification)
            - confidence: Confidence score for the classification (0-1)
            - parameters: Extracted parameters relevant to the query type
            - clarification_needed: Whether clarification is needed
            - clarification_question: Question to ask for clarification
        """
        # Check if this is a correction to a previous query
        is_correction, correction_info = self._detect_correction(query_text, context)
        if is_correction:
            return {
                "query_type": "correction",
                "confidence": correction_info["confidence"],
                "parameters": {
                    "original_query_id": correction_info.get("original_query_id"),
                    "correction_target": correction_info.get("correction_target"),
                    "correction_text": query_text,
                },
                "clarification_needed": False,
                "clarification_question": None
            }
        
        # If not a correction, proceed with normal classification
        query_type, confidence = self._rule_based_classification(query_text, context)
        
        # Create result object
        result = {
            "query_type": query_type,
            "confidence": confidence,
            "parameters": {},
            "clarification_needed": False,
            "clarification_question": None
        }
        
        # Extract parameters based on query type
        if query_type == "order_history":
            self._extract_order_history_params(query_text, result, context)
        elif query_type == "menu":
            self._extract_menu_params(query_text, result, context)
        elif query_type == "action":
            self._extract_action_params(query_text, result, context)
        elif query_type == "clarification":
            self._extract_clarification_params(query_text, result, context)
        
        # Check if clarification is needed
        result["clarification_needed"] = self._needs_clarification(result, context)
        if result["clarification_needed"]:
            result["clarification_question"] = self._generate_clarification_question(result, context)
        
        return result
        
    def _rule_based_classification(self, query_text: str, context: Optional[Dict[str, Any]]) -> tuple:
        """
        Classify query using rule-based approaches.
        
        Args:
            query_text: The raw query text
            context: Optional context from previous interactions
            
        Returns:
            Tuple of (query_type, confidence)
        """
        query_lower = query_text.lower()
        scores = {
            'order_history': 0.0,
            'menu': 0.0,
            'action': 0.0,
            'clarification': 0.0
        }
        
        # Check for clarification context first
        if context and context.get('clarification_state') == 'CLARIFYING':
            scores['clarification'] = 0.8
        
        # Count keyword matches for each type
        for keyword in self.ORDER_HISTORY_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                scores['order_history'] += 0.1
                
        for keyword in self.MENU_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                scores['menu'] += 0.1
                
        for keyword in self.ACTION_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                scores['action'] += 0.2  # Increased weight for action keywords
                
        for keyword in self.CLARIFICATION_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                scores['clarification'] += 0.1
        
        # Apply additional rules
        
        # Check for specific action verbs at the beginning of the query
        action_verbs = ['enable', 'disable', 'update', 'change', 'set', 'add', 'remove', 'delete']
        for verb in action_verbs:
            if query_lower.strip().startswith(verb):
                scores['action'] += 0.3  # Significant boost for queries starting with action verbs
        
        # Questions are likely queries, not actions
        if '?' in query_text:
            scores['order_history'] *= 1.2
            scores['menu'] *= 1.2
            scores['action'] *= 0.7
        
        # Short responses in clarification context are likely clarifications
        if context and context.get('clarification_state') == 'CLARIFYING' and len(query_text.split()) < 5:
            scores['clarification'] *= 1.5
        
        # Get the highest scoring type
        max_score = max(scores.values())
        if max_score > 0:
            query_types = [t for t, s in scores.items() if s == max_score]
            query_type = query_types[0]  # Take the first if tied
            
            # Normalize confidence to 0.5-1.0 range
            confidence = 0.5 + (0.5 * min(max_score, 1.0))
        else:
            # Default to order_history with low confidence if nothing matches
            query_type = 'order_history'
            confidence = 0.5
            
        return query_type, confidence
    
    def _extract_order_history_params(self, query_text: str, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        """
        Extract parameters for order history queries.
        
        Args:
            query_text: The raw query text
            result: The classification result to update
            context: Optional context from previous interactions
        """
        # Extract time references using TemporalAnalysisService
        time_analysis = self.temporal_analysis.analyze(query_text, context)
        result['parameters']['time_references'] = time_analysis
        
        # Extract filters (e.g., price ranges, customer types)
        filters = self._extract_filters(query_text)
        result['parameters']['filters'] = filters
        
        # Extract entities (e.g., specific items or categories)
        entities = self._extract_entities(query_text)
        result['parameters']['entities'] = entities
    
    def _extract_menu_params(self, query_text: str, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        """
        Extract parameters for menu queries.
        
        Args:
            query_text: The raw query text
            result: The classification result to update
            context: Optional context from previous interactions
        """
        # Extract entities (items, categories, options)
        entities = self._extract_entities(query_text)
        result['parameters']['entities'] = entities
        
        # Extract filters (e.g., price ranges, availability)
        filters = self._extract_filters(query_text)
        result['parameters']['filters'] = filters
    
    def _extract_action_params(self, query_text: str, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        """
        Extract parameters for action requests.
        
        Args:
            query_text: The raw query text
            result: The classification result to update
            context: Optional context from previous interactions
        """
        # Extract the action type (update, enable, disable, etc.)
        actions = self._extract_actions(query_text)
        result['parameters']['actions'] = actions
        
        # Extract entities that the action applies to
        entities = self._extract_entities(query_text)
        result['parameters']['entities'] = entities
        
        # Extract values for updates (e.g., new prices)
        # This is a placeholder and would require more sophisticated parsing
        if any(a.get('type') == 'update' for a in actions):
            # Simple regex for price values
            price_matches = re.findall(r'\$?(\d+(?:\.\d{1,2})?)', query_text)
            if price_matches:
                # Add prices to the actions that are updates
                for action in actions:
                    if action.get('type') == 'update' and 'price' in action.get('field', ''):
                        action['value'] = float(price_matches[0])
    
    def _extract_clarification_params(self, query_text: str, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        """
        Extract parameters from clarification responses.
        
        Args:
            query_text: The raw query text
            result: The classification result to update
            context: Optional context from previous interactions
        """
        # Check what we were expecting clarification for
        if context and context.get('clarification_state') == 'CLARIFYING':
            # If we were asking for time clarification, extract time references
            if context.get('clarification_type') == 'time':
                time_analysis = self.temporal_analysis.analyze(query_text)
                result['parameters']['time_references'] = time_analysis
            
            # If we were asking for entity clarification, extract entities
            elif context.get('clarification_type') == 'entity':
                entities = self._extract_entities(query_text)
                result['parameters']['entities'] = entities
                
            # If we were asking for filter clarification, extract filters
            elif context.get('clarification_type') == 'filter':
                filters = self._extract_filters(query_text)
                result['parameters']['filters'] = filters
    
    def _extract_filters(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Extract filters from query text.
        
        Args:
            query_text: The raw query text
            
        Returns:
            List of filter dictionaries
        """
        filters = []
        
        # Extract price filters
        # Pattern for "over $X" or "more than $X"
        over_pattern = r'(?:over|more than|greater than|above|exceeding)\s+\$?(\d+(?:\.\d{1,2})?)'
        for match in re.finditer(over_pattern, query_text.lower()):
            value = float(match.group(1))
            filters.append({
                'field': 'price',
                'operator': '>',
                'value': value
            })
        
        # Pattern for "under $X" or "less than $X"
        under_pattern = r'(?:under|less than|below|cheaper than|lower than)\s+\$?(\d+(?:\.\d{1,2})?)'
        for match in re.finditer(under_pattern, query_text.lower()):
            value = float(match.group(1))
            filters.append({
                'field': 'price',
                'operator': '<',
                'value': value
            })
        
        # Pattern for "between $X and $Y"
        between_pattern = r'between\s+\$?(\d+(?:\.\d{1,2})?)\s+and\s+\$?(\d+(?:\.\d{1,2})?)'
        for match in re.finditer(between_pattern, query_text.lower()):
            min_value = float(match.group(1))
            max_value = float(match.group(2))
            filters.append({
                'field': 'price',
                'operator': 'between',
                'min_value': min_value,
                'max_value': max_value
            })
        
        # Extract quantity filters
        # Pattern for "more than X orders/sales"
        qty_over_pattern = r'(?:over|more than|greater than|above)\s+(\d+)\s+(?:orders|sales|transactions)'
        for match in re.finditer(qty_over_pattern, query_text.lower()):
            value = int(match.group(1))
            filters.append({
                'field': 'quantity',
                'operator': '>',
                'value': value
            })
        
        return filters
    
    def _extract_entities(self, query_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities (items, categories, options, etc.) from query text.
        
        Args:
            query_text: The raw query text
            
        Returns:
            Dictionary of entity lists by type
        """
        entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        
        # In a real implementation, this would use a more sophisticated approach
        # like entity recognition or database matching
        
        # This is a simple placeholder implementation that looks for quoted strings
        # and assumes they are item names
        quoted_items = re.findall(r'"([^"]+)"', query_text)
        for item in quoted_items:
            entities['items'].append({
                'name': item,
                'confidence': 0.9
            })
        
        # Look for category indicators
        category_pattern = r'(?:category|categories)\s+(?:called|named)?\s*"?([a-zA-Z0-9\s]+)"?'
        category_matches = re.findall(category_pattern, query_text, re.IGNORECASE)
        for category in category_matches:
            entities['categories'].append({
                'name': category.strip(),
                'confidence': 0.8
            })
        
        # Look for option indicators
        option_pattern = r'(?:option|options)\s+(?:called|named)?\s*"?([a-zA-Z0-9\s]+)"?'
        option_matches = re.findall(option_pattern, query_text, re.IGNORECASE)
        for option in option_matches:
            entities['options'].append({
                'name': option.strip(),
                'confidence': 0.8
            })
        
        return entities
    
    def _extract_actions(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Extract actions and their parameters from query text.
        
        Args:
            query_text: The raw query text
            
        Returns:
            List of action dictionaries
        """
        actions = []
        query_lower = query_text.lower()
        
        # Check for price updates
        price_update_pattern = r'(?:change|update|set|modify)\s+(?:the\s+)?price\s+(?:of\s+)?(?:"([^"]+)"|([a-zA-Z0-9\s]+))?\s+to\s+\$?(\d+(?:\.\d{1,2})?)'
        for match in re.finditer(price_update_pattern, query_lower):
            item_name = match.group(1) or match.group(2)
            new_price = float(match.group(3))
            
            if item_name:
                actions.append({
                    'type': 'update',
                    'field': 'price',
                    'entity_type': 'item',
                    'entity_name': item_name.strip(),
                    'value': new_price
                })
        
        # Check for enabling/disabling items
        enable_pattern = r'(enable|disable|activate|deactivate)\s+(?:the\s+)?(?:"([^"]+)"|([a-zA-Z0-9\s]+))?'
        for match in re.finditer(enable_pattern, query_lower):
            action_type = match.group(1)
            item_name = match.group(2) or match.group(3)
            
            if item_name:
                is_enable = action_type in ['enable', 'activate']
                actions.append({
                    'type': 'update',
                    'field': 'status',
                    'entity_type': 'item',  # This could be item, category, option, etc.
                    'entity_name': item_name.strip(),
                    'value': 'enabled' if is_enable else 'disabled'
                })
        
        return actions
    
    def _needs_clarification(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if clarification is needed based on classification result.
        
        Args:
            result: The classification result
            context: Optional context from previous interactions
            
        Returns:
            True if clarification is needed, False otherwise
        """
        query_type = result['query_type']
        extracted_params = result['parameters']
        
        # Check if time references are needed but missing
        if query_type == 'order_history':
            time_refs = extracted_params['time_references']
            if time_refs.get('is_ambiguous', False):
                return True
        
        # Check if entities are needed but missing for actions
        if query_type == 'action':
            entities = extracted_params['entities']
            actions = extracted_params['actions']
            
            # If we have actions but no entities, we need clarification
            if actions and not any(entities.values()):
                return True
                
            # If we have price updates but no price value, we need clarification
            for action in actions:
                if action.get('type') == 'update' and action.get('field') == 'price' and 'value' not in action:
                    return True
        
        return False
    
    def _generate_clarification_question(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a clarification question based on missing parameters.
        
        Args:
            result: Classification result with parameters
            context: Optional conversation context
            
        Returns:
            Question string to ask for clarification
        """
        query_type = result["query_type"]
        params = result["parameters"]
        
        if query_type == "order_history":
            # Check for missing time period
            if not params.get("time_period"):
                return "What time period would you like to see order history for?"
            # Check for missing filters
            if not params.get("filters"):
                return "Would you like to filter the order history in any way?"
        
        elif query_type == "menu":
            # Check for missing item or category
            if not params.get("item") and not params.get("category"):
                return "Which menu item or category would you like information about?"
        
        elif query_type == "action":
            # Check for missing action
            if not params.get("action_type"):
                return "What action would you like to perform?"
            # Check for missing target
            if not params.get("target_item") and not params.get("target_category"):
                return "Which item or category would you like to modify?"
            # Check for missing value for price changes
            if params.get("action_type") == "price_change" and not params.get("new_price"):
                return "What should the new price be?"
        
        # Default question if no specific clarification needed
        return "Could you provide more details about your request?"
    
    def _detect_correction(self, query_text: str, context: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Detect if a query is a correction to a previous query.
        
        Args:
            query_text: The text of the query to analyze
            context: Optional conversation context containing previous queries and responses
            
        Returns:
            Tuple of (is_correction, correction_info)
        """
        # If no context, can't be a correction
        if not context or not context.get("conversation_history"):
            return False, {}
        
        # Lowercase for easier matching
        query_lower = query_text.lower()
        
        # Check for correction keywords
        correction_indicators = [keyword for keyword in self.CORRECTION_KEYWORDS 
                               if keyword in query_lower]
        
        if not correction_indicators:
            return False, {}
        
        # Get previous query from context
        conversation_history = context.get("conversation_history", [])
        if not conversation_history:
            return False, {}
        
        # Find the most recent user query
        previous_queries = [entry for entry in reversed(conversation_history) 
                          if entry.get("role") == "user"]
        
        if not previous_queries:
            return False, {}
        
        previous_query = previous_queries[0]
        previous_query_id = previous_query.get("id")
        previous_query_text = previous_query.get("text", "")
        
        # Calculate confidence based on number of indicators
        confidence = min(0.5 + (len(correction_indicators) * 0.1), 0.95)
        
        # Determine what's being corrected
        correction_target = "unknown"
        
        # Check for patterns indicating what's being corrected
        if re.search(r"(date|time|period|day|week|month|year)", query_lower):
            correction_target = "time_period"
        elif re.search(r"(item|product|dish|menu item|food)", query_lower):
            correction_target = "item"
        elif re.search(r"(category|section|type|group)", query_lower):
            correction_target = "category"
        elif re.search(r"(price|cost|amount|money|dollar)", query_lower):
            correction_target = "price"
        elif re.search(r"(action|change|update|modify)", query_lower):
            correction_target = "action"
        
        return True, {
            "confidence": confidence,
            "original_query_id": previous_query_id,
            "original_query": previous_query_text,
            "correction_target": correction_target,
            "correction_indicators": correction_indicators
        } 