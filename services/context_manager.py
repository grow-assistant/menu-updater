"""
Context Manager for Swoop AI Conversational Query Flow.

This module implements the ConversationContext class which maintains 
conversation state across turns, as specified in the SWOOP development plan.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ConversationContext:
    """
    Maintains conversation state across turns, including:
    - Conversation history
    - Current topic/intent
    - Active entities
    - Time references and resolutions
    - Active filters
    - Clarification state
    - Pending actions
    """
    
    # Clarification states
    NONE = "NONE"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"
    CLARIFYING = "CLARIFYING"
    RECEIVED_CLARIFICATION = "RECEIVED_CLARIFICATION"
    RESOLVED = "RESOLVED"
    
    def __init__(self, session_id: str):
        """
        Initialize a new conversation context.
        
        Args:
            session_id: Unique identifier for the user session
        """
        self.session_id = session_id
        self.conversation_history = []  # List of (query, response) tuples
        self.current_topic = None  # 'order_history', 'menu', 'action'
        self.active_entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        self.time_references = {
            'explicit_dates': [],  # Parsed datetime objects
            'relative_references': [],  # E.g., 'last month'
            'resolved_time_period': None  # Final resolved time period
        }
        self.active_filters = []  # E.g., {'field': 'price', 'operator': '>', 'value': 100}
        self.clarification_state = self.NONE
        self.pending_actions = []  # Actions awaiting confirmation
        
        # Enhanced reference tracking
        self.last_mentioned_entities = {}  # Entities mentioned in the most recent query
        self.reference_history = []  # Track references and their resolutions
        
        logger.info(f"Initialized new conversation context for session {session_id}")
    
    def update_with_query(self, query: str, classification_result: Dict[str, Any]) -> None:
        """
        Update context with information from a new query.
        
        Args:
            query: User's query text
            classification_result: Result from the query classifier
        """
        # Get the query type from the classification result
        query_type = classification_result.get('query_type')
        
        # Check for topic change
        if query_type and self.current_topic and query_type != self.current_topic:
            if self.detect_topic_change(query_type):
                self.reset_for_new_topic(query_type)
        
        # Set current topic if not already set
        if query_type and not self.current_topic:
            self.current_topic = query_type
            
        # Update conversation history
        if len(self.conversation_history) < 20:  # Limit history size
            self.conversation_history.append((query, None))
        else:
            self.conversation_history.pop(0)
            self.conversation_history.append((query, None))
            
        # Extract entities from the classification result
        entities = classification_result.get('extracted_params', {}).get('entities', {})
        
        # Add extracted entities to active entities
        for entity_type, entity_list in entities.items():
            if entity_type in self.active_entities:
                # Update last_mentioned_entities first
                self.last_mentioned_entities[entity_type] = entity_list.copy()
                
                # Update active_entities, ensuring no duplicates
                for entity in entity_list:
                    if entity not in self.active_entities[entity_type]:
                        self.active_entities[entity_type].append(entity)
        
        # Extract time references from the classification result
        time_refs = classification_result.get('extracted_params', {}).get('time_references', {})
        
        # Update time references
        if time_refs:
            if 'explicit_dates' in time_refs:
                self.time_references['explicit_dates'] = time_refs['explicit_dates']
            if 'relative_references' in time_refs:
                self.time_references['relative_references'] = time_refs['relative_references']
            if 'resolved_time_period' in time_refs:
                self.time_references['resolved_time_period'] = time_refs['resolved_time_period']
        
        # Extract filters from the classification result
        filters = classification_result.get('extracted_params', {}).get('filters', [])
        
        # Update filters, replacing any existing filters on the same field
        if filters:
            for new_filter in filters:
                field = new_filter.get('field')
                # Remove any existing filters for this field
                self.active_filters = [f for f in self.active_filters if f.get('field') != field]
                # Add the new filter
                self.active_filters.append(new_filter)
        
        # Extract actions from the classification result
        actions = classification_result.get('extracted_params', {}).get('actions', [])
        
        # Update pending actions
        if actions:
            for action in actions:
                if action not in self.pending_actions:
                    self.pending_actions.append(action)
    
    def update_with_response(self, response: str) -> None:
        """
        Update context with a response.
        
        Args:
            response: Response text to add to the conversation history
        """
        # Update the most recent entry in the conversation history
        if self.conversation_history:
            query, _ = self.conversation_history[-1]
            self.conversation_history[-1] = (query, response)
    
    def detect_topic_change(self, new_topic: str) -> bool:
        """
        Determine if there has been a topic change.
        
        Args:
            new_topic: The new topic from the latest query
            
        Returns:
            True if the topic has changed, False otherwise
        """
        if not self.current_topic:
            return True
            
        return new_topic != self.current_topic
    
    def reset_for_new_topic(self, new_topic: str) -> None:
        """
        Reset relevant parts of the context when the topic changes.
        
        Args:
            new_topic: The new conversation topic
        """
        logger.info(f"Topic change detected: {self.current_topic} -> {new_topic}")
        
        # Store the old topic for reference history
        old_topic = self.current_topic
        
        # Update the current topic
        self.current_topic = new_topic
        
        # Clear filters as they're typically topic-specific
        self.active_filters = []
        
        # Clear pending actions as they're typically topic-specific
        self.pending_actions = []
        
        # Clear clarification state
        self.clarification_state = self.NONE
        
        # Keep entity and time references for potential cross-topic references,
        # but note in reference history that there was a topic change
        self.reference_history.append({
            'timestamp': datetime.now().isoformat(),
            'event': 'topic_change',
            'from_topic': old_topic,
            'to_topic': new_topic
        })
    
    def resolve_references(self, query: str) -> Dict[str, Any]:
        """
        Resolve entity and time references in a query.
        Enhanced to handle pronoun and reference resolution.
        
        Args:
            query: User's query text
            
        Returns:
            Dict containing resolved references
        """
        resolved = {
            'entities': {},
            'time_period': None,
            'filters': []
        }
        
        # Entity reference resolution (pronouns like "it", "them", "that item", etc.)
        entity_refs = self._resolve_entity_references(query)
        if entity_refs:
            resolved['entities'] = entity_refs
            
            # Record the resolution in reference history
            self.reference_history.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'entity_reference_resolution',
                'query_fragment': query,
                'resolved_entities': entity_refs
            })
        
        # Time reference resolution (like "that time period", "the same period")
        time_ref = self._resolve_time_references(query)
        if time_ref:
            resolved['time_period'] = time_ref
            
            # Record the resolution in reference history
            self.reference_history.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'time_reference_resolution',
                'query_fragment': query,
                'resolved_time_period': time_ref
            })
        
        # Filter reference resolution (like "that filter", "the same condition")
        filter_refs = self._resolve_filter_references(query)
        if filter_refs:
            resolved['filters'] = filter_refs
            
            # Record the resolution in reference history
            self.reference_history.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'filter_reference_resolution',
                'query_fragment': query,
                'resolved_filters': filter_refs
            })
        
        return resolved
    
    def _resolve_entity_references(self, query: str) -> Dict[str, List[Any]]:
        """
        Resolve entity references from context.
        
        Args:
            query: User's query text
            
        Returns:
            Dict mapping entity types to resolved entities
        """
        resolved_entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        
        # Look for pronouns referring to entities
        pronouns = {
            'singular': ['it', 'this', 'that', 'one'],
            'plural': ['they', 'these', 'those', 'ones']
        }
        
        pronoun_patterns = {
            'singular': r'\b(it|this|that|one)\b',
            'plural': r'\b(they|these|those|ones)\b'
        }
        
        # Check for singular pronouns
        if re.search(pronoun_patterns['singular'], query.lower()):
            # Resolve to the most recently mentioned singular entity
            for entity_type, entities in self.last_mentioned_entities.items():
                if entities and len(entities) == 1:
                    resolved_entities[entity_type].extend(entities)
                    break
            
            # If no match in last_mentioned_entities, try active_entities
            if all(len(entities) == 0 for entities in resolved_entities.values()):
                for entity_type, entities in self.active_entities.items():
                    if entities:
                        # Take the most recent entity (last in the list)
                        resolved_entities[entity_type].append(entities[-1])
                        break
        
        # Check for plural pronouns
        if re.search(pronoun_patterns['plural'], query.lower()):
            # Resolve to the most recently mentioned plural entities
            for entity_type, entities in self.last_mentioned_entities.items():
                if entities and len(entities) > 1:
                    resolved_entities[entity_type].extend(entities)
                    break
            
            # If no match in last_mentioned_entities, try active_entities
            if all(len(entities) == 0 for entities in resolved_entities.values()):
                for entity_type, entities in self.active_entities.items():
                    if len(entities) > 1:
                        resolved_entities[entity_type].extend(entities)
                        break
        
        # Check for explicit references like "that category", "the item", etc.
        for entity_type_singular in ['item', 'category', 'option', 'option item']:
            entity_type_plural = entity_type_singular + 's' if entity_type_singular != 'option item' else 'option_items'
            
            # Pattern for "that/the/this {entity_type}"
            pattern = r'\b(that|the|this)\s+' + re.escape(entity_type_singular) + r'\b'
            
            if re.search(pattern, query.lower()):
                # Look for the most recently mentioned entity of this type
                if entity_type_plural in self.last_mentioned_entities and self.last_mentioned_entities[entity_type_plural]:
                    resolved_entities[entity_type_plural].extend(self.last_mentioned_entities[entity_type_plural])
                # If not found in last_mentioned, try active_entities
                elif entity_type_plural in self.active_entities and self.active_entities[entity_type_plural]:
                    # Take the most recent entity of this type
                    resolved_entities[entity_type_plural].append(self.active_entities[entity_type_plural][-1])
        
        return resolved_entities
    
    def _resolve_time_references(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Resolve time references from context.
        
        Args:
            query: User's query text
            
        Returns:
            Resolved time period or None if not found
        """
        # Look for references to previous time periods
        time_ref_patterns = [
            r'\b(that|the|this|same)\s+(time period|time frame|period|timeframe|dates?|time)\b',
            r'\b(those|these)\s+(dates?|times?)\b'
        ]
        
        for pattern in time_ref_patterns:
            if re.search(pattern, query.lower()):
                # Return the previously resolved time period
                return self.time_references['resolved_time_period']
        
        return None
    
    def _resolve_filter_references(self, query: str) -> List[Dict[str, Any]]:
        """
        Resolve filter references from context.
        
        Args:
            query: User's query text
            
        Returns:
            List of resolved filters
        """
        # Look for references to previous filters
        filter_ref_patterns = [
            r'\b(that|the|this|same)\s+(filter|condition|restriction|criteria|criterion)\b',
            r'\b(those|these)\s+(filters|conditions|restrictions|criteria)\b'
        ]
        
        for pattern in filter_ref_patterns:
            if re.search(pattern, query.lower()):
                # Return the current active filters
                return self.active_filters
        
        return []
    
    def clear_clarification_state(self) -> None:
        """Reset the clarification state to NONE."""
        self.clarification_state = self.NONE
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to a dictionary representation.
        
        Returns:
            Dict representation of the context
        """
        return {
            'session_id': self.session_id,
            'conversation_history': self.conversation_history,
            'current_topic': self.current_topic,
            'active_entities': self.active_entities,
            'time_references': self.time_references,
            'active_filters': self.active_filters,
            'clarification_state': self.clarification_state,
            'pending_actions': self.pending_actions,
            'last_mentioned_entities': self.last_mentioned_entities,
            'reference_history': self.reference_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """
        Create a ConversationContext instance from a dictionary.
        
        Args:
            data: Dictionary representation of a context
            
        Returns:
            ConversationContext instance
        """
        context = cls(data['session_id'])
        context.conversation_history = data.get('conversation_history', [])
        context.current_topic = data.get('current_topic')
        context.active_entities = data.get('active_entities', {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        })
        context.time_references = data.get('time_references', {
            'explicit_dates': [],
            'relative_references': [],
            'resolved_time_period': None
        })
        context.active_filters = data.get('active_filters', [])
        context.clarification_state = data.get('clarification_state', cls.NONE)
        context.pending_actions = data.get('pending_actions', [])
        context.last_mentioned_entities = data.get('last_mentioned_entities', {})
        context.reference_history = data.get('reference_history', [])
        return context
    
    def get_recent_queries(self, n: int = 3) -> List[str]:
        """
        Get the N most recent user queries.
        
        Args:
            n: Number of recent queries to retrieve
            
        Returns:
            List of recent query strings
        """
        queries = [query for query, _ in self.conversation_history[-n:]]
        return queries
    
    def get_reference_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the reference resolution history.
        
        Returns:
            Dict summarizing reference resolution events
        """
        return {
            'entity_references': len([r for r in self.reference_history if r['event'] == 'entity_reference_resolution']),
            'time_references': len([r for r in self.reference_history if r['event'] == 'time_reference_resolution']),
            'filter_references': len([r for r in self.reference_history if r['event'] == 'filter_reference_resolution']),
            'topic_changes': len([r for r in self.reference_history if r['event'] == 'topic_change']),
            'last_reference': self.reference_history[-1] if self.reference_history else None
        }


class ContextManager:
    """
    Manages multiple conversation contexts, indexed by session ID.
    """
    
    def __init__(self, expiry_minutes: int = 30):
        """
        Initialize the context manager.
        
        Args:
            expiry_minutes: Number of minutes after which a context expires
        """
        self.contexts = {}  # Mapping of session_id to (context, last_updated_timestamp)
        self.expiry_minutes = expiry_minutes
        logger.info(f"Initialized ContextManager with {expiry_minutes} minute expiry")
    
    def get_context(self, session_id: str) -> ConversationContext:
        """
        Get the context for a session, creating a new one if necessary.
        
        Args:
            session_id: Session identifier
            
        Returns:
            The conversation context for the session
        """
        now = datetime.now()
        
        if session_id in self.contexts:
            context, _ = self.contexts[session_id]
            # Update the timestamp
            self.contexts[session_id] = (context, now)
            return context
        
        # Create a new context
        context = ConversationContext(session_id)
        self.contexts[session_id] = (context, now)
        return context
    
    def cleanup_expired(self) -> int:
        """
        Remove expired contexts.
        
        Returns:
            Number of contexts removed
        """
        now = datetime.now()
        expired_sessions = []
        
        for session_id, (_, timestamp) in self.contexts.items():
            age = now - timestamp
            if age.total_seconds() > self.expiry_minutes * 60:
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            del self.contexts[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired contexts")
        return len(expired_sessions) 