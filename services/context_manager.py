"""
Context Manager for Swoop AI Conversational Query Flow.

This module implements the ConversationContext class which maintains 
conversation state across turns, as specified in the SWOOP development plan.
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import logging
import re
from collections import defaultdict, Counter
import time
import uuid
import json
import copy
import string
import os

logger = logging.getLogger(__name__)


class UserProfile:
    """
    Maintains user-specific preferences and behavior patterns to enable response personalization.
    
    Tracks:
    - Preferred response styles (detail level, tone)
    - Frequently queried entities and topics
    - Query patterns and habits
    - Personalization preferences
    - Usage statistics
    """
    
    # Personalization preference settings
    DETAIL_LEVELS = ["concise", "standard", "detailed"]
    RESPONSE_TONES = ["formal", "professional", "casual", "friendly"]
    
    def __init__(self, user_id: str):
        """
        Initialize a new user profile.
        
        Args:
            user_id: Unique identifier for the user
        """
        self.user_id = user_id
        self.creation_date = datetime.now()
        self.last_active = datetime.now()
        
        # Personalization preferences (with defaults)
        self.preferences = {
            "detail_level": "standard",  # concise, standard, detailed
            "response_tone": "professional",  # formal, professional, casual, friendly
            "chart_preference": "auto",  # never, auto, always
            "voice_enabled": False,
            "timezone": "UTC",
        }
        
        # Usage statistics
        self.stats = {
            "total_queries": 0,
            "queries_by_category": defaultdict(int),
            "queries_by_day_of_week": defaultdict(int),
            "queries_by_hour": defaultdict(int),
            "average_session_length": 0,
            "total_sessions": 0,
            "total_time_spent": 0,
        }
        
        # Entity and topic tracking
        self.frequent_entities = Counter()  # Counter of entities
        self.frequent_topics = Counter()  # Counter of topics
        self.topic_transitions = defaultdict(Counter)  # From topic -> to topic
        
        # Query pattern tracking
        self.query_patterns = []
        self.recent_queries = []
        self.max_recent_queries = 50
    
    def update_with_query(self, query_text: str, query_type: str, 
                         entities: Dict[str, Any], topic: str) -> None:
        """
        Update the user profile with information from a new query.
        
        Args:
            query_text: The raw query text
            query_type: The classification of the query
            entities: Entities mentioned in the query
            topic: The query topic
        """
        self.last_active = datetime.now()
        
        # Update stats
        self.stats["total_queries"] += 1
        self.stats["queries_by_category"][query_type] += 1
        self.stats["queries_by_day_of_week"][self.last_active.strftime("%A")] += 1
        self.stats["queries_by_hour"][self.last_active.hour] += 1
        
        # Update entity tracking
        if entities:
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_name = entity.get("name", "")
                    if entity_name:
                        self.frequent_entities[f"{entity_type}:{entity_name}"] += 1
        
        # Update topic tracking
        if topic:
            self.frequent_topics[topic] += 1
            
            # If we have a previous query, track the topic transition
            if self.recent_queries and self.recent_queries[-1].get("topic"):
                prev_topic = self.recent_queries[-1].get("topic")
                if prev_topic != topic:
                    self.topic_transitions[prev_topic][topic] += 1
        
        # Store query for pattern analysis
        query_info = {
            "text": query_text,
            "type": query_type,
            "topic": topic,
            "timestamp": self.last_active.isoformat(),
            "entities": [f"{entity_type}:{e.get('name', '')}" 
                        for entity_type, entity_list in entities.items() 
                        for e in entity_list if e.get("name")]
        }
        
        self.recent_queries.append(query_info)
        
        # Keep only the most recent queries
        if len(self.recent_queries) > self.max_recent_queries:
            self.recent_queries = self.recent_queries[-self.max_recent_queries:]
        
        # Analyze for patterns (every 10 queries)
        if self.stats["total_queries"] % 10 == 0:
            self._analyze_query_patterns()
    
    def _analyze_query_patterns(self) -> None:
        """
        Analyze recent queries for patterns to inform personalization.
        """
        # This is a simple implementation; a more sophisticated analysis 
        # would use ML techniques for pattern recognition
        
        # Example pattern: Time of day preference
        hour_counts = Counter([datetime.fromisoformat(q["timestamp"]).hour 
                               for q in self.recent_queries])
        peak_hours = [hour for hour, count in hour_counts.items() 
                     if count > len(self.recent_queries) / 10]  # 10% threshold
        
        # Example pattern: Recurring entity interest
        entity_counts = Counter([entity for q in self.recent_queries 
                                for entity in q.get("entities", [])])
        frequent_entities = [entity for entity, count in entity_counts.items() 
                            if count > len(self.recent_queries) / 5]  # 20% threshold
        
        # Example pattern: Topic focus
        topic_counts = Counter([q.get("topic") for q in self.recent_queries if q.get("topic")])
        primary_topics = [topic for topic, count in topic_counts.items() 
                         if count > len(self.recent_queries) / 3]  # 33% threshold
        
        # Store discovered patterns
        new_pattern = {
            "timestamp": datetime.now().isoformat(),
            "peak_hours": peak_hours,
            "frequent_entities": frequent_entities,
            "primary_topics": primary_topics
        }
        
        self.query_patterns.append(new_pattern)
        logger.debug(f"Analyzed query patterns for user {self.user_id}: {new_pattern}")
    
    def update_preference(self, preference_name: str, value: Any) -> bool:
        """
        Update a user preference setting.
        
        Args:
            preference_name: The preference to update
            value: The new value for the preference
            
        Returns:
            True if successful, False otherwise
        """
        if preference_name in self.preferences:
            # Validate specific preference values
            if preference_name == "detail_level" and value not in self.DETAIL_LEVELS:
                return False
            elif preference_name == "response_tone" and value not in self.RESPONSE_TONES:
                return False
                
            # Update the preference
            self.preferences[preference_name] = value
            logger.info(f"Updated user {self.user_id} preference: {preference_name}={value}")
            return True
        
        return False
    
    def start_session(self) -> None:
        """
        Mark the start of a new user session.
        """
        self.stats["total_sessions"] += 1
        self.session_start_time = datetime.now()
    
    def end_session(self) -> None:
        """
        Mark the end of the current user session and update statistics.
        """
        if hasattr(self, 'session_start_time'):
            session_duration = (datetime.now() - self.session_start_time).total_seconds()
            self.stats["total_time_spent"] += session_duration
            
            # Update average session length
            new_avg = (
                (self.stats["average_session_length"] * (self.stats["total_sessions"] - 1))
                + session_duration
            ) / self.stats["total_sessions"]
            
            self.stats["average_session_length"] = new_avg
            delattr(self, 'session_start_time')
    
    def get_personalization_context(self) -> Dict[str, Any]:
        """
        Get personalization context for enhancing responses.
        
        Returns:
            Dictionary with personalization information
        """
        # Get top entities and topics
        top_entities = [entity.split(":", 1)[1] for entity, _ in self.frequent_entities.most_common(5)]
        top_topics = [topic for topic, _ in self.frequent_topics.most_common(3)]
        
        # Current time-based patterns
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")
        
        # Get latest pattern analysis if available
        latest_pattern = self.query_patterns[-1] if self.query_patterns else {}
        
        return {
            "preferences": self.preferences,
            "frequent_entities": top_entities,
            "frequent_topics": top_topics,
            "is_peak_hour": current_hour in latest_pattern.get("peak_hours", []),
            "day_pattern": self.stats["queries_by_day_of_week"].get(current_day, 0) > 
                           sum(self.stats["queries_by_day_of_week"].values()) / 7,  # Above average
            "expertise_level": self._calculate_expertise_level(),
        }
    
    def _calculate_expertise_level(self) -> str:
        """
        Calculate the user's expertise level based on usage patterns.
        
        Returns:
            Expertise level: "beginner", "intermediate", or "advanced"
        """
        if self.stats["total_queries"] < 20:
            return "beginner"
        elif self.stats["total_queries"] < 100:
            return "intermediate"
        else:
            return "advanced"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user profile to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the user profile
        """
        # Convert defaultdict and Counter objects to regular dicts for serialization
        stats_dict = {
            k: dict(v) if isinstance(v, defaultdict) else v
            for k, v in self.stats.items()
        }
        
        return {
            "user_id": self.user_id,
            "creation_date": self.creation_date.isoformat(),
            "last_active": self.last_active.isoformat(),
            "preferences": self.preferences,
            "stats": stats_dict,
            "frequent_entities": dict(self.frequent_entities),
            "frequent_topics": dict(self.frequent_topics),
            "topic_transitions": {k: dict(v) for k, v in self.topic_transitions.items()},
            "query_patterns": self.query_patterns,
            "recent_queries": self.recent_queries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """
        Create a user profile from a dictionary.
        
        Args:
            data: Dictionary representation of a user profile
            
        Returns:
            UserProfile instance
        """
        profile = cls(data["user_id"])
        profile.creation_date = datetime.fromisoformat(data["creation_date"])
        profile.last_active = datetime.fromisoformat(data["last_active"])
        profile.preferences = data["preferences"]
        
        # Restore statistics
        for k, v in data["stats"].items():
            if isinstance(v, dict):
                profile.stats[k] = defaultdict(int, v)
            else:
                profile.stats[k] = v
        
        # Restore frequency counters
        profile.frequent_entities = Counter(data["frequent_entities"])
        profile.frequent_topics = Counter(data["frequent_topics"])
        
        # Restore topic transitions
        for from_topic, transitions in data["topic_transitions"].items():
            profile.topic_transitions[from_topic] = Counter(transitions)
        
        # Restore query patterns and recent queries
        profile.query_patterns = data.get("query_patterns", [])
        profile.recent_queries = data.get("recent_queries", [])
        
        return profile


class ConversationContext:
    """
    Maintains conversation state across turns, including:
    - Conversation history
    - Current topic/intent
    - Previous topics/intents
    - Active entities
    - Time references and resolutions
    - Active filters
    - Clarification state
    - Pending actions
    - Topic-specific context preservation
    - Multi-intent support
    - User profile for personalization
    """
    
    # Clarification states
    NONE = "NONE"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"
    CLARIFYING = "CLARIFYING"
    RECEIVED_CLARIFICATION = "RECEIVED_CLARIFICATION"
    RESOLVED = "RESOLVED"
    
    # Topic sensitivity thresholds
    TOPIC_CHANGE_CONFIDENCE = 0.75  # Minimum confidence to trigger a topic change
    TOPIC_SIMILARITY_THRESHOLD = 0.4  # Threshold for detecting similar topics
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        """
        Initialize a new conversation context.
        
        Args:
            session_id: Unique identifier for the user session
            user_id: Unique identifier for the user (optional)
        """
        self.session_id = session_id
        self.conversation_history = []  # List of (query, response) tuples
        self.current_topic = None  # 'order_history', 'menu', 'action'
        self.previous_topic = None  # Track the previous topic 
        
        # Topic history and management
        self.topic_history = []  # List of previous topics
        self.topic_timestamps = {}  # Timestamps of when topics were active
        self.topic_specific_context = defaultdict(dict)  # Context preserved per topic
        self.secondary_topics = []  # For multi-intent support
        self.primary_intent = None  # Primary intent for multi-intent support
        self.intents = []  # List of all intents in the conversation
        
        # User profile integration
        self.user_id = user_id or session_id  # Default to session_id if no user_id provided
        self.user_profile = UserProfile(self.user_id)
        self.user_profile.start_session()
        
        self.active_entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        
        # Entity tracking for personalization
        self.tracked_entities = defaultdict(set)  # Tracked entities by type
        self.entity_ids = {}  # Mapping of entity names to IDs
        self.top_entities = []  # Most frequently referenced entities
        self.entity_focus = []  # Current focus entities
        
        self.time_references = {
            'explicit_date': None,  # "March 15, 2023"
            'explicit_range': None,  # "from Jan 1 to Feb 28"
            'relative_date': None,  # "yesterday", "last month"
            'relative_range': None,  # "past 7 days"
            'resolution': {
                'start_date': None,
                'end_date': None
            }
        }
        
        # Add time_range attribute to match async implementation
        self.time_range = {}
        
        self.active_filters = []  # List of active filters
        self.filters = {}  # For compatibility with async implementation
        
        self.clarification_state = self.NONE
        self.clarification_context = {
            'type': None,  # 'entity', 'time', 'filter'
            'param': None,  # Which specific parameter needs clarification
            'options': [],  # Possible options for clarification
            'original_query': None  # The original query that needed clarification
        }
        
        self.pending_actions = []  # List of pending actions
        
        # For tracking topic continuity and transitions
        self.topic_confidence = 0.0  # Confidence in current topic
        self.last_query_timestamp = time.time()
        self.topic_transition_count = 0  # Count of topic transitions in session
        
        # Multi-intent tracking
        self.intents = []  # List of detected intents in current conversation
        self.intent_confidences = {}  # Confidence scores for each intent
        self.last_intent = None  # Most recent intent
        self.primary_intent = None  # Primary intent for current query
        
        # Query characteristics for topic analysis
        self.query_keywords = set()  # Important keywords from queries
        self.recurring_entities = defaultdict(int)  # Count entities by frequency
        
        # Reference history for tracking resolved references and topic changes
        self.reference_history = []  # Track references and their resolutions
        
        # Last mentioned entities for reference resolution
        self.last_mentioned_entities = {}
        
        logger.info(f"Initialized new conversation context for session {session_id}")

    def update_with_query(self, query: str, classification_result: Dict[str, Any]) -> None:
        """
        Update context with a new query and its classification result.
        
        Args:
            query: The user's query
            classification_result: The classification result for the query
        """
        # Get query properties
        query_type = classification_result.get("query_type", "unknown")
        confidence = classification_result.get("confidence", 0.0)
        parameters = classification_result.get("parameters", {})
        intent_type = classification_result.get("intent_type", query_type)
        
        # Add to conversation history
        query_record = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "confidence": confidence,
            "classification": classification_result
        }
        self.conversation_history.append(query_record)
        
        # Extract entities from parameters
        entities = parameters.get("entities", {})
        
        # Handle time references
        time_references = classification_result.get("time_references") or parameters.get("time_references", {})
        if time_references:
            # Update the time_references attribute
            for key, value in time_references.items():
                self.time_references[key] = value
            
            # Also update time_range for compatibility
            if "resolution" in time_references and time_references["resolution"]:
                resolution = time_references["resolution"]
                if "start_date" in resolution:
                    self.time_range["start_date"] = resolution["start_date"]
                if "end_date" in resolution:
                    self.time_range["end_date"] = resolution["end_date"]
        
        # Check for topic change based on query_type and confidence
        is_topic_change = self.detect_topic_change(query_type, confidence)
        
        # If topic change detected, update topic tracking
        if is_topic_change:
            # Store previous topic before changing
            self.previous_topic = self.current_topic
            
            if self.previous_topic:
                self.topic_history.append(self.previous_topic)
                
                # Preserve context before switching topics
                self.preserve_topic_context(self.previous_topic)
            
            # Check if we're returning to a topic we've seen before
            if query_type in self.topic_specific_context:
                # Restore the context for this topic
                stored_context = self.topic_specific_context[query_type]
                self.restore_topic_context(query_type, stored_context)
            else:
                # Update current topic for a new topic
                self.current_topic = query_type
                self.topic_timestamps[query_type] = datetime.now().isoformat()
        
        # Handle multiple intents
        is_multi_intent = classification_result.get("multiple_intents", False)
        if is_multi_intent:
            # Set primary intent from intent_type
            self.primary_intent = intent_type
            
            # Add primary intent to overall intents list
            if intent_type not in self.intents:
                self.intents.append(intent_type)
            
            # Handle secondary intents
            secondary_intents = classification_result.get("secondary_intents", [])
            for secondary_intent in secondary_intents:
                secondary_intent_type = secondary_intent.get("intent_type")
                if secondary_intent_type and secondary_intent_type not in self.secondary_topics:
                    self.secondary_topics.append(secondary_intent_type)
                if secondary_intent_type and secondary_intent_type not in self.intents:
                    self.intents.append(secondary_intent_type)
        else:
            # For single intent queries, just set the primary intent
            self.primary_intent = intent_type
            if intent_type not in self.intents:
                self.intents.append(intent_type)
        
        # Handle entities based on query type
        self._process_entities_by_query_type(query_type, parameters)
        
        # Update active filters
        filters = parameters.get("filters", [])
        if filters:
            for filter_item in filters:
                if filter_item.get("type") and filter_item.get("value"):
                    self.active_filters[filter_item["type"]] = filter_item["value"]
                    
        # Update user profile with query information
        # Ensure we're properly extracting entities for the user profile
        entities_for_profile = parameters.get("entities", {})
        self.user_profile.update_with_query(
            query_text=query,
            query_type=query_type,
            entities=entities_for_profile,
            topic=self.current_topic
        )
    
    def _process_entities_by_query_type(self, query_type: str, parameters: Dict[str, Any]) -> None:
        """
        Process entities based on query type to update context information.
        
        Args:
            query_type: The type of query being processed
            parameters: The parameters from query classification
        """
        entities = parameters.get("entities", {})
        
        # Special case for the 'category' key that might be a direct string value
        if entities and isinstance(entities, dict) and "category" in entities and isinstance(entities["category"], str):
            category_name = entities["category"]
            # Update recurring entities counter for this category
            entity_key = f"category:{category_name}"
            self.recurring_entities[entity_key] += 1
            # Also add to tracked_entities
            self.tracked_entities["category"].add(category_name)
        
        # Track recurring entities - process all entity types
        if entities:
            for entity_type, entity_values in entities.items():
                # Handle both list and dictionary formats
                if isinstance(entity_values, list):
                    for entity in entity_values:
                        entity_name = entity if isinstance(entity, str) else entity.get("name", "")
                        if entity_name:
                            entity_key = f"{entity_type}:{entity_name}"
                            self.recurring_entities[entity_key] += 1
                elif isinstance(entity_values, dict):
                    for key, value in entity_values.items():
                        entity_key = f"{entity_type}:{key}"
                        self.recurring_entities[entity_key] += 1
                elif isinstance(entity_values, str):
                    # Handle direct string values
                    entity_key = f"{entity_type}:{entity_values}"
                    self.recurring_entities[entity_key] += 1
        
        # Handle data query entities
        if query_type == "data_query":
            # Extract and track menu items
            if "menu_items" in entities:
                for item in entities["menu_items"]:
                    item_name = item.get("name", "")
                    item_id = item.get("id", "")
                    if item_name:
                        self.tracked_entities["menu_item"].add(item_name)
                        if item_id:
                            self.entity_ids[f"menu_item:{item_name}"] = item_id
            
            # Extract and track categories
            if "categories" in entities:
                for category in entities["categories"]:
                    cat_name = category.get("name", "")
                    cat_id = category.get("id", "")
                    if cat_name:
                        self.tracked_entities["category"].add(cat_name)
                        if cat_id:
                            self.entity_ids[f"category:{cat_name}"] = cat_id
            
            # Extract time periods
            if "time_period" in entities:
                for period in entities["time_period"]:
                    period_name = period.get("name", "")
                    if period_name:
                        self.tracked_entities["time_period"].add(period_name)
        
        # Handle action request entities
        elif query_type == "action_request":
            # Extract actions
            if "action" in entities:
                for action in entities["action"]:
                    action_name = action.get("name", "")
                    if action_name:
                        self.tracked_entities["action"].add(action_name)
        
        # Update top_entities cache with most frequent entities
        all_entities = []
        for entity_type, entity_set in self.tracked_entities.items():
            all_entities.extend([f"{entity_type}:{entity}" for entity in entity_set])
        
        # Use Counter to find most common entities
        entity_counter = Counter(all_entities)
        self.top_entities = [entity.split(":", 1)[1] for entity, _ in entity_counter.most_common(5)]
        
        # Update entity focus based on current query
        current_query_entities = []
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity_name = entity.get("name", "")
                if entity_name:
                    current_query_entities.append(entity_name)
        
        if current_query_entities:
            self.entity_focus = current_query_entities
        
        # Log entity processing
        logger.debug(f"Processed entities for query type {query_type}: {entities}")
        logger.debug(f"Updated entity focus: {self.entity_focus}")
        logger.debug(f"Top entities: {self.top_entities}")
    
    def preserve_topic_context(self, topic: str) -> None:
        """
        Preserve context for the current topic before switching to a new one.
        
        Args:
            topic: The topic whose context should be preserved
        """
        # Log what we're preserving
        logger.info(f"Active entities before preservation: {self.active_entities}")
        
        # Create a snapshot of the current context
        context_snapshot = {
            'active_entities': copy.deepcopy(self.active_entities),
            'time_references': copy.deepcopy(self.time_references),
            'time_range': copy.deepcopy(self.time_range),
            'active_filters': copy.deepcopy(self.active_filters),
            'filters': copy.deepcopy(self.filters),
            'query_keywords': copy.deepcopy(self.query_keywords)
        }
        
        # Store in topic-specific context
        self.topic_specific_context[topic] = context_snapshot
        
        logger.info(f"Storing context for topic '{topic}': {context_snapshot}")
        logger.info(f"Preserved context for topic '{topic}'")
        
        # Reset active_entities when switching topics
        self.active_entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }

    def restore_topic_context(self, topic: str, stored_context: Dict[str, Any]) -> None:
        """
        Restore context values for a topic from stored context.
        
        Args:
            topic: The topic to restore
            stored_context: The stored context data for the topic
        """
        # Restore active entities
        if 'active_entities' in stored_context:
            self.active_entities = stored_context['active_entities'].copy()
            
        # Restore time references
        if 'time_references' in stored_context:
            self.time_references = stored_context['time_references'].copy()
            
        # Restore time_range
        if 'time_range' in stored_context:
            self.time_range = stored_context['time_range'].copy()
            
        # Restore active filters
        if 'active_filters' in stored_context:
            self.active_filters = stored_context['active_filters'].copy()
            
        # Restore other relevant attributes
        if 'filters' in stored_context:
            self.filters = stored_context['filters'].copy()
            
        # Set current topic
        self.current_topic = topic

    def detect_topic_change(self, new_topic: str, confidence: float = 0.0) -> bool:
        """
        Enhanced topic change detection with confidence and continuity analysis.
        
        Args:
            new_topic: The new topic from the latest query
            confidence: Confidence score for the new topic classification
            
        Returns:
            True if the topic has changed, False otherwise
        """
        # If no current topic, this is a topic change
        if not self.current_topic:
            return True
            
        # Direct topic match - no change
        if new_topic == self.current_topic:
            return False
            
        # Topic change with high confidence should be accepted
        if confidence > self.TOPIC_CHANGE_CONFIDENCE:
            logger.info(f"High confidence topic change detected: {confidence} > {self.TOPIC_CHANGE_CONFIDENCE}")
            return True
            
        # Calculate topic similarity using simple string matching
        # This could be enhanced with embeddings or semantic similarity
        similarity = self._calculate_topic_similarity(new_topic, self.current_topic)
        if similarity > self.TOPIC_SIMILARITY_THRESHOLD:
            # Topics are similar enough to consider it a continuation
            logger.info(f"Topics are similar (similarity: {similarity}), not changing topic")
            return False
            
        # Check for recurring entities across topics
        # If there are shared entities between old and new topics, may not be a topic change
        recurring_entities_count = sum(count for entity, count in self.recurring_entities.items() if count > 1)
        if recurring_entities_count >= 2:
            logger.info(f"Found {recurring_entities_count} recurring entities - topics may be related")
            # Only change topic if confidence is higher than a threshold
            if confidence > 0.85:
                return True
            else:
                logger.info(f"Low confidence ({confidence}) with recurring entities, staying with current topic")
                return False
        
        # Low confidence should NOT change topic
        if confidence < 0.6:
            logger.info(f"Low confidence topic change ignored: {confidence} < 0.6")
            return False
            
        # Default: topic has changed
        return True
    
    def _calculate_topic_similarity(self, topic1: str, topic2: str) -> float:
        """
        Calculate similarity between two topics.
        
        Args:
            topic1: First topic
            topic2: Second topic
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple similarity based on shared words
        words1 = set(topic1.lower().replace('_', ' ').split())
        words2 = set(topic2.lower().replace('_', ' ').split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def reset_for_new_topic(self, new_topic: str) -> None:
        """
        Reset relevant parts of the context when the topic changes, with improved context preservation.
        
        Args:
            new_topic: The new conversation topic
        """
        logger.info(f"Topic change detected: {self.current_topic} -> {new_topic}")
        logger.info(f"Active entities before topic change: {self.active_entities}")
        
        # Store the old topic in topic history
        if self.current_topic:
            self.topic_history.append(self.current_topic)
            # Also preserve context of the current topic before switching
            self.preserve_topic_context(self.current_topic)
            
        # Track topic transition count
        self.topic_transition_count += 1
        
        # Check if we're returning to a previous topic
        returning_to_previous = new_topic in self.topic_history
        
        # If returning to a previous topic, restore its context
        if returning_to_previous:
            logger.info(f"Returning to previous topic: {new_topic}")
            self.restore_topic_context(new_topic)
        # Only clear entities when we have a current topic and we're switching to a new one
        # This preserves manual entity changes for the first topic
        elif self.current_topic is not None:
            # For a new topic, we should clear the active entities
            logger.info(f"New topic, initializing defaults and clearing entities")
            
            # Initialize empty entities
            self.active_entities = {
                'items': [],
                'categories': [],
                'options': [],
                'option_items': []
            }
            
            # Clear filters as they're typically topic-specific
            self.active_filters = []
            self.filters = {}
            
            # Clear pending actions as they're typically topic-specific
            self.pending_actions = []
            
            # Start with clean clarification state
            self.clarification_state = self.NONE
            self.clarification_context = {
                'type': None,
                'param': None,
                'options': [],
                'original_query': None
            }
        else:
            # This is the first topic, so don't clear entities
            logger.info(f"First topic, preserving entities")
        
        # Store the previous topic before updating the current topic
        self.previous_topic = self.current_topic
        
        # Update the current topic
        old_topic = self.current_topic
        self.current_topic = new_topic
        
        logger.info(f"Active entities after topic change: {self.active_entities}")

    def update_with_response(self, response: str) -> None:
        """
        Update context with a response.
        
        Args:
            response: Response text to add to the conversation history
        """
        # Update the most recent entry in the conversation history
        if self.conversation_history:
            # The conversation history is now a list of dictionaries, not tuples
            latest_entry = self.conversation_history[-1]
            latest_entry["response"] = response
    
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
        Convert the context to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the context
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_history": self.conversation_history,
            "current_topic": self.current_topic,
            "topic_history": self.topic_history,
            "topic_timestamps": self.topic_timestamps,
            "topic_specific_context": {
                k: dict(v) for k, v in self.topic_specific_context.items()
            },
            "secondary_topics": self.secondary_topics,
            "active_entities": self.active_entities,
            "active_filters": self.active_filters,
            "clarification_state": self.clarification_state,
            "clarification_context": self.clarification_context,
            "user_profile": self.user_profile.to_dict() if hasattr(self, 'user_profile') else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """
        Create a context from a dictionary.
        
        Args:
            data: Dictionary representation of a context
            
        Returns:
            ConversationContext instance
        """
        context = cls(data["session_id"], data.get("user_id"))
        
        context.conversation_history = data.get("conversation_history", [])
        context.current_topic = data.get("current_topic")
        context.topic_history = data.get("topic_history", [])
        context.topic_timestamps = data.get("topic_timestamps", {})
        
        # Restore topic-specific context
        for topic, topic_data in data.get("topic_specific_context", {}).items():
            context.topic_specific_context[topic] = topic_data
        
        context.secondary_topics = data.get("secondary_topics", [])
        
        # Restore active entities
        if "active_entities" in data:
            context.active_entities = data["active_entities"]
        
        # Restore active filters
        if "active_filters" in data:
            context.active_filters = data["active_filters"]
        
        # Restore clarification state
        if "clarification_state" in data:
            context.clarification_state = data["clarification_state"]
        
        if "clarification_context" in data:
            context.clarification_context = data["clarification_context"]
        
        # Restore user profile if present
        if "user_profile" in data and data["user_profile"]:
            context.user_profile = UserProfile.from_dict(data["user_profile"])
        
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
        # Backward compatibility with older tests
        if not hasattr(self, 'reference_history'):
            self.reference_history = []
            
        # Add topic transition events to reference history if missing
        if self.topic_history and not any(r.get('event') == 'topic_change' for r in self.reference_history):
            for i, topic in enumerate(self.topic_history):
                next_topic = self.topic_history[i+1] if i+1 < len(self.topic_history) else self.current_topic
                if next_topic:
                    self.reference_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'event': 'topic_change',
                        'from_topic': topic,
                        'to_topic': next_topic
                    })
        
        # Get entity references
        entity_references = {}
        for entity_type, entities in self.active_entities.items():
            if entities:
                entity_references[entity_type] = entities
        
        # Return updated summary
        return {
            'active_entities': entity_references,
            'entity_type': next(iter(entity_references.keys())) if entity_references else None,
            'time_references': self.time_range if hasattr(self, 'time_range') else {},
            'current_topic': self.current_topic,
            'topic_history': self.topic_history
        }

    def get_personalization_hints(self) -> Dict[str, Any]:
        """
        Get personalization hints for the response generator.
        
        Returns:
            Dictionary with personalization hints
        """
        if not hasattr(self, 'user_profile'):
            return {}
            
        personalization = self.user_profile.get_personalization_context()
        
        # Add context-specific information
        personalization.update({
            "session_context": {
                "current_topic": self.current_topic,
                "topic_history": self.topic_history[-3:] if self.topic_history else [],
                "entity_focus": self._get_entity_focus(),
                "conversation_length": len(self.conversation_history),
                "recent_queries": [item.get("query") for item in self.conversation_history[-3:]]
            }
        })
        
        return personalization
    
    def _get_entity_focus(self) -> List[str]:
        """
        Get the entities that appear to be the focus of the current conversation.
        
        Returns:
            List of focused entity names
        """
        # Simple heuristic: get entities that appear in multiple recent queries
        entity_mentions = defaultdict(int)
        
        # Look at the 5 most recent queries
        recent_history = self.conversation_history[-5:]
        
        for item in recent_history:
            classification = item.get("classification", {})
            parameters = classification.get("parameters", {})
            entities = parameters.get("entities", {})
            
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_name = entity.get("name", "")
                    if entity_name:
                        entity_mentions[entity_name] += 1
        
        # Return entities mentioned more than once
        return [entity for entity, count in entity_mentions.items() if count > 1]
    
    def update_user_preference(self, preference_name: str, value: Any) -> bool:
        """
        Update a user preference in the user profile.
        
        Args:
            preference_name: The preference to update
            value: The new value for the preference
        
        Returns:
            True if successful, False otherwise
        """
        if hasattr(self, 'user_profile'):
            return self.user_profile.update_preference(preference_name, value)
        return False
    
    def end_session(self) -> None:
        """
        End the current conversation session.
        """
        if hasattr(self, 'user_profile'):
            self.user_profile.end_session()


class ContextManager:
    """
    Manages conversation contexts for multiple user sessions.
    Provides context persistence, retrieval, and cleanup.
    """
    
    def __init__(self, expiry_minutes: int = 30, profile_storage_path: Optional[str] = None):
        """
        Initialize the context manager.
        
        Args:
            expiry_minutes: Minutes after which a context is considered expired
            profile_storage_path: Path to store user profiles (if None, profiles are kept in memory only)
        """
        self.contexts = {}  # Session ID -> ConversationContext
        self.expiry_minutes = expiry_minutes
        self.last_access_times = {}  # Session ID -> last access timestamp
        
        # For tracking topic transition patterns
        self.topic_transition_stats = defaultdict(int)  # Track common topic transitions
        self.topic_occurrence_stats = defaultdict(int)  # Track frequency of topics
        
        # User profile management
        self.user_profiles = {}  # User ID -> UserProfile
        self.profile_storage_path = profile_storage_path
        
        # Create storage directory if it doesn't exist
        if profile_storage_path:
            os.makedirs(profile_storage_path, exist_ok=True)
        
        logger.info(f"Initialized ContextManager with {expiry_minutes}-minute expiry")
    
    def get_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """
        Get the context for a session, creating a new one if it doesn't exist.
        
        Args:
            session_id: The session identifier
            user_id: The user identifier (optional)
            
        Returns:
            The conversation context for the session
        """
        # Record access time
        self.last_access_times[session_id] = time.time()
        
        # Create new context if it doesn't exist
        if session_id not in self.contexts:
            # If user_id is provided, check if we have a stored profile
            if user_id and user_id in self.user_profiles:
                context = ConversationContext(session_id, user_id)
                context.user_profile = self.user_profiles[user_id]
                context.user_profile.start_session()
            else:
                # Create a new context with an optional user ID
                context = ConversationContext(session_id, user_id)
                
                # If user_id is provided, load user profile from storage
                if user_id and self.profile_storage_path:
                    profile_path = os.path.join(self.profile_storage_path, f"{user_id}.json")
                    if os.path.exists(profile_path):
                        try:
                            with open(profile_path, 'r') as f:
                                profile_data = json.load(f)
                                context.user_profile = UserProfile.from_dict(profile_data)
                                context.user_profile.start_session()
                                logger.info(f"Loaded user profile for user_id={user_id}")
                        except Exception as e:
                            logger.error(f"Error loading user profile for user_id={user_id}: {str(e)}")
                            # Use the default profile created during context initialization
                
                # Store the user profile for future reference
                if user_id:
                    self.user_profiles[user_id] = context.user_profile
                
            self.contexts[session_id] = context
            logger.info(f"Created new context for session_id={session_id}, user_id={user_id}")
        
        return self.contexts[session_id]
    
    def update_context(self, 
                     session_id: str, 
                     query_text: str, 
                     classification_result: Dict[str, Any],
                     additional_context: Optional[Dict[str, Any]] = None) -> ConversationContext:
        """
        Update a session's context with new information.
        
        Args:
            session_id: The session identifier
            query_text: The user's query text
            classification_result: Classification data from the query classifier
            additional_context: Any additional context information
            
        Returns:
            The updated conversation context
        """
        # Get the context
        context = self.get_context(session_id)
        
        # Get the topic before updating
        prev_topic = context.current_topic
        
        # Update the context with the query
        context.update_with_query(query_text, classification_result)
        
        # If additional context is provided, incorporate it
        if additional_context:
            for key, value in additional_context.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        
        # Track topic transitions for analysis
        if prev_topic and context.current_topic and prev_topic != context.current_topic:
            transition_key = f"{prev_topic}->{context.current_topic}"
            self.topic_transition_stats[transition_key] += 1
            
        # Track topic occurrence
        if context.current_topic:
            self.topic_occurrence_stats[context.current_topic] += 1
        
        return context
    
    def handle_interruption(self, 
                          session_id: str, 
                          interruption_type: str, 
                          query_text: str) -> Dict[str, Any]:
        """
        Handle a conversation interruption, such as a topic change or clarification.
        
        Args:
            session_id: The session identifier
            interruption_type: Type of interruption (e.g., "topic_change", "clarification")
            query_text: The user's query text that caused the interruption
            
        Returns:
            Information about how the interruption was handled
        """
        context = self.get_context(session_id)
        
        response = {
            "handled": False,
            "action_taken": None,
            "message": ""
        }
        
        # Handle different types of interruptions
        if interruption_type == "topic_change":
            # Preserve context of the current topic before changing
            if context.current_topic:
                context.preserve_topic_context(context.current_topic)
                response["action_taken"] = "preserved_previous_topic"
                response["message"] = f"Preserved context for topic '{context.current_topic}'"
                response["handled"] = True
                
        elif interruption_type == "clarification":
            # If we were in the middle of a different clarification, reset it
            if context.clarification_state not in [ConversationContext.NONE, ConversationContext.RESOLVED]:
                context.clear_clarification_state()
                response["action_taken"] = "reset_clarification"
                response["message"] = "Reset previous clarification state"
                response["handled"] = True
                
        elif interruption_type == "return_to_previous_topic":
            # Return to the most recent topic in history
            if context.topic_history:
                previous_topic = context.topic_history[-1]
                
                # Restore the context for that topic
                if previous_topic in context.topic_specific_context:
                    stored_context = context.topic_specific_context[previous_topic]
                    context.restore_topic_context(previous_topic, stored_context)
                    
                    # Update the response
                    response["action_taken"] = "restored_previous_topic"
                    response["message"] = f"Returned to previous topic '{previous_topic}'"
                    response["handled"] = True
                    
                    # Remove this topic from history since we're now using it
                    context.topic_history.pop()
                    
                    # Set as current topic
                    context.current_topic = previous_topic
                
        # Update conversation history with the interruption
        context.update_with_response(f"SYSTEM: Detected {interruption_type}")
        
        # Log the interruption
        logger.info(f"Handled interruption type={interruption_type} for session={session_id}")
        
        return response
    
    def handle_correction(self,
                        session_id: str,
                        correction_result: Dict[str, Any],
                        original_query_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a correction to a previous query.
        
        Args:
            session_id: The session identifier
            correction_result: The classification result for the correction query
            original_query_id: Optional ID of the query being corrected
            
        Returns:
            Information about how the correction was handled
        """
        context = self.get_context(session_id)
        
        response = {
            "handled": False,
            "action_taken": None,
            "message": "",
            "original_query": None,
            "correction_applied": False
        }
        
        # Get conversation history to find the original query
        history = context.conversation_history
        
        # If we have a specific original_query_id, find that query
        original_query = None
        original_index = -1
        
        if original_query_id:
            for i, entry in enumerate(history):
                if entry.get("id") == original_query_id and entry.get("role") == "user":
                    original_query = entry
                    original_index = i
                    break
        else:
            # Otherwise, find the most recent user query that isn't the correction
            # Skip the current correction query
            for i in range(len(history) - 2, -1, -1):
                if history[i].get("role") == "user":
                    original_query = history[i]
                    original_index = i
                    break
        
        if not original_query:
            response["message"] = "Could not find original query to correct"
            return response
        
        # Extract correction parameters
        correction_params = correction_result.get("parameters", {})
        correction_target = correction_params.get("correction_target", "unknown")
        
        # Get the original query text and classification
        original_text = original_query.get("text", "")
        original_classification = original_query.get("classification", {})
        
        response["original_query"] = {
            "id": original_query.get("id"),
            "text": original_text,
            "classification": original_classification
        }
        
        # Mark this as a correction in the context
        context.conversation_history.append({
            "role": "system",
            "text": f"CORRECTION: User corrected {correction_target} in previous query",
            "timestamp": datetime.now().isoformat()
        })
        
        # Update active entities or references based on correction target
        if correction_target == "time_period":
            # Update time references in context
            if "time_references" in correction_params:
                context.time_references = correction_params["time_references"]
                response["action_taken"] = "updated_time_references"
                response["handled"] = True
                response["correction_applied"] = True
                
        elif correction_target in ["item", "category"]:
            # Update entities in context
            if "entities" in correction_params and correction_params["entities"]:
                entities = correction_params["entities"]
                
                if correction_target == "item" and entities.get("items"):
                    context.active_entities["items"] = entities["items"]
                    response["action_taken"] = "updated_active_items"
                    
                elif correction_target == "category" and entities.get("categories"):
                    context.active_entities["categories"] = entities["categories"]
                    response["action_taken"] = "updated_active_categories"
                    
                response["handled"] = True
                response["correction_applied"] = True
                
        elif correction_target == "price" or correction_target == "action":
            # Update action information
            if "actions" in correction_params and correction_params["actions"]:
                context.pending_actions = correction_params["actions"]
                response["action_taken"] = "updated_pending_actions"
                response["handled"] = True
                response["correction_applied"] = True
        
        # Create a more detailed message about what was corrected
        if response["correction_applied"]:
            response["message"] = f"Applied correction to {correction_target} from previous query"
        else:
            response["message"] = f"Noted correction attempt but could not apply changes"
            
        # Log the correction
        logger.info(f"Handled correction target={correction_target} for session={session_id}, success={response['correction_applied']}")
        
        return response
    
    def persist_user_profile(self, user_id: str) -> bool:
        """
        Persist a user profile to storage.
        
        Args:
            user_id: The user identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.profile_storage_path or user_id not in self.user_profiles:
            return False
            
        try:
            profile_path = os.path.join(self.profile_storage_path, f"{user_id}.json")
            with open(profile_path, 'w') as f:
                json.dump(self.user_profiles[user_id].to_dict(), f, indent=2)
            logger.info(f"Persisted user profile for user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"Error persisting user profile for user_id={user_id}: {str(e)}")
            return False
    
    def persist_all_user_profiles(self) -> Dict[str, bool]:
        """
        Persist all user profiles to storage.
        
        Returns:
            Dictionary mapping user_id to success/failure
        """
        results = {}
        
        for user_id in self.user_profiles:
            results[user_id] = self.persist_user_profile(user_id)
            
        return results
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user profile by user ID.
        
        Args:
            user_id: The user identifier
            
        Returns:
            UserProfile if found, None otherwise
        """
        # Check if profile is in memory
        if user_id in self.user_profiles:
            return self.user_profiles[user_id]
            
        # Check if profile is in storage
        if self.profile_storage_path:
            profile_path = os.path.join(self.profile_storage_path, f"{user_id}.json")
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, 'r') as f:
                        profile_data = json.load(f)
                        profile = UserProfile.from_dict(profile_data)
                        self.user_profiles[user_id] = profile  # Cache in memory
                        return profile
                except Exception as e:
                    logger.error(f"Error loading user profile for user_id={user_id}: {str(e)}")
        
        return None
    
    def update_user_preference(self, user_id: str, preference_name: str, value: Any) -> bool:
        """
        Update a user preference.
        
        Args:
            user_id: The user identifier
            preference_name: The preference to update
            value: The new value for the preference
        
        Returns:
            True if successful, False otherwise
        """
        profile = self.get_user_profile(user_id)
        if profile:
            success = profile.update_preference(preference_name, value)
            if success and self.profile_storage_path:
                self.persist_user_profile(user_id)
            return success
        return False
    
    def get_user_personalization(self, user_id: str) -> Dict[str, Any]:
        """
        Get personalization context for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Dictionary with personalization information, or empty dict if user not found
        """
        profile = self.get_user_profile(user_id)
        if profile:
            return profile.get_personalization_context()
        return {}
    
    def cleanup_expired(self) -> int:
        """
        Remove expired contexts and persist user profiles.
        
        Returns:
            Number of removed contexts
        """
        current_time = time.time()
        removed_count = 0
        
        for session_id in list(self.contexts.keys()):
            last_access = self.last_access_times.get(session_id, 0)
            expiry_time = self.expiry_minutes * 60
            
            if current_time - last_access > expiry_time:
                context = self.contexts[session_id]
                
                # End the session in the user profile
                if hasattr(context, 'user_profile'):
                    context.user_profile.end_session()
                    
                    # If there's a user_id, persist the profile before removing
                    if hasattr(context, 'user_id') and context.user_id:
                        self.persist_user_profile(context.user_id)
                
                # Remove the context
                del self.contexts[session_id]
                
                # Clean up the access time
                if session_id in self.last_access_times:
                    del self.last_access_times[session_id]
                    
                removed_count += 1
                logger.info(f"Removed expired context for session_id={session_id}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired contexts")
            
        return removed_count
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active sessions and topic transitions.
        
        Returns:
            Dictionary with session statistics
        """
        active_sessions = len(self.contexts)
        
        # Get top topic transitions
        top_transitions = sorted(
            self.topic_transition_stats.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Get most common topics
        top_topics = sorted(
            self.topic_occurrence_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "active_sessions": active_sessions,
            "top_topic_transitions": dict(top_transitions),
            "top_topics": dict(top_topics)
        } 