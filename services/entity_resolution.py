"""
Entity Resolution Service for Swoop AI Conversational Query Flow.

This module provides functionality for resolving entity references in natural language queries,
matching them to known entities in the system, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """
    Handles resolution of entity references in queries.
    
    Responsibilities:
    - Menu item/category lookup and matching
    - Fuzzy matching for approximate names
    - Pronoun and reference resolution
    - Entity type classification
    """
    
    # Maximum Levenshtein distance ratio for fuzzy matching
    FUZZY_MATCH_THRESHOLD = 0.8
    
    # Common pronouns that might refer to entities
    ENTITY_PRONOUNS = {
        'singular': ['it', 'this', 'that', 'one'],
        'plural': ['they', 'these', 'those', 'ones']
    }
    
    def __init__(self, db_connector=None):
        """
        Initialize the entity resolution service.
        
        Args:
            db_connector: Optional database connector for entity lookups
        """
        self.db_connector = db_connector
        self.entity_cache = {
            'items': {},
            'categories': {},
            'options': {},
            'option_items': {}
        }
        logger.info("Initialized EntityResolutionService")
    
    def resolve_entities(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and resolve entity references in a query.
        
        Args:
            query_text: Original user query
            context: Conversation context with history and active entities
            
        Returns:
            Dict containing:
                - entities: Dict of resolved entities by type
                - references: List of references found and their resolutions
                - is_ambiguous: Whether any reference is ambiguous
                - needs_clarification: Whether clarification is needed
                - clarification_question: Suggested question if clarification is needed
        """
        result = {
            'entities': {
                'items': [],
                'categories': [],
                'options': [],
                'option_items': []
            },
            'references': [],
            'is_ambiguous': False,
            'needs_clarification': False,
            'clarification_question': None
        }
        
        # Extract direct entity mentions
        direct_entities = self._extract_direct_entities(query_text)
        for entity_type, entities in direct_entities.items():
            result['entities'][entity_type].extend(entities)
            
        # Resolve pronouns and references
        references = self._extract_references(query_text)
        if references:
            resolved_refs = self._resolve_references(references, context)
            result['references'] = resolved_refs
            
            # Add resolved entities to the result
            for ref in resolved_refs:
                if ref.get('resolution') and ref.get('entity_type'):
                    if not ref.get('is_ambiguous', False):
                        result['entities'][ref['entity_type']].append(ref['resolution'])
                    else:
                        result['is_ambiguous'] = True
            
            # Check if any reference is ambiguous and needs clarification
            ambiguous_refs = [r for r in resolved_refs if r.get('is_ambiguous', False)]
            if ambiguous_refs:
                result['is_ambiguous'] = True
                result['needs_clarification'] = True
                result['clarification_question'] = self._generate_clarification_question(ambiguous_refs[0])
        
        return result
    
    def _extract_direct_entities(self, query_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract directly mentioned entities from the query.
        
        Args:
            query_text: The user query
            
        Returns:
            Dict of entity lists by type
        """
        result = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        
        # Search for entities in the database or cache
        # This is a simplified implementation - in a real system, we would query the database
        
        # Example implementation:
        if self.db_connector:
            try:
                # Look for menu items
                items = self._search_entities('items', query_text)
                result['items'] = items
                
                # Look for categories
                categories = self._search_entities('categories', query_text)
                result['categories'] = categories
                
                # Look for options
                options = self._search_entities('options', query_text)
                result['options'] = options
                
                # Look for option items
                option_items = self._search_entities('option_items', query_text)
                result['option_items'] = option_items
            except Exception as e:
                logger.error(f"Error extracting direct entities: {e}")
        
        return result
    
    def _search_entities(self, entity_type: str, query_text: str) -> List[Dict[str, Any]]:
        """
        Search for entities of a given type in the query.
        
        Args:
            entity_type: Type of entity to search for
            query_text: User's query
            
        Returns:
            List of matching entities
        """
        # In a real implementation, this would query the database
        # For now, we'll return an empty list as a placeholder
        return []
    
    def _extract_references(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Extract entity references (like pronouns) from the query.
        
        Args:
            query_text: The user query
            
        Returns:
            List of reference objects with original text and position
        """
        references = []
        
        # Extract pronouns
        for pronoun_type, pronouns in self.ENTITY_PRONOUNS.items():
            for pronoun in pronouns:
                # Find all occurrences of the pronoun
                for match in re.finditer(r'\b' + re.escape(pronoun) + r'\b', query_text.lower()):
                    references.append({
                        'text': match.group(0),
                        'start': match.start(),
                        'end': match.end(),
                        'type': 'pronoun',
                        'plurality': pronoun_type
                    })
        
        # Extract "the X" references (like "the category", "the item")
        for entity_type in ['item', 'category', 'option', 'order']:
            pattern = r'\b(that|the|this|those)\s+(' + re.escape(entity_type) + r'(?:s)?)\b'
            for match in re.finditer(pattern, query_text.lower()):
                # Get the full matched text
                full_text = match.group(0)
                entity_type_matched = match.group(2)  # The entity type mentioned in the text
                
                # Check if the entity is already plural
                if entity_type_matched.endswith('s'):
                    entity_type_plural = entity_type_matched
                    plurality = 'plural'
                else:
                    entity_type_plural = entity_type_matched + 's'  # Convert to plural for key lookup
                    plurality = 'singular'
                
                references.append({
                    'text': full_text,
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'explicit_reference',
                    'entity_type': entity_type_plural,
                    'plurality': plurality
                })
        
        # Special case for domain-specific references (like "those orders")
        domain_specific_patterns = [
            (r'\b(those|these)\s+(orders|items|categories|options)\b', 'plural'),
            (r'\b(that|this)\s+(order|item|category|option)\b', 'singular')
        ]
        
        for pattern, plurality in domain_specific_patterns:
            for match in re.finditer(pattern, query_text.lower()):
                entity_type = match.group(2)  # The entity type (orders, items, etc.)
                
                # Ensure it's in plural form for consistency with our keys
                if not entity_type.endswith('s'):
                    entity_type += 's'
                
                references.append({
                    'text': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'domain_reference',
                    'entity_type': entity_type,
                    'plurality': plurality
                })
        
        return references
    
    def _resolve_references(self, references: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Resolve references to actual entities using conversation context.
        
        Args:
            references: List of reference objects
            context: Conversation context with history and active entities
            
        Returns:
            List of references with added resolution information
        """
        resolved_references = []
        
        # Extract previous query information from session history
        previous_entities = {}
        previous_query_type = None
        previous_filters = {}
        
        if 'session_history' in context and context['session_history']:
            # Get the most recent query
            last_query = context['session_history'][-1]
            
            # Extract query type
            previous_query_type = last_query.get('category')
            
            # Extract entities
            previous_entities = last_query.get('entities', {})
            
            # Extract filters (like date filters)
            if 'sql_query' in last_query:
                # Extract date filters from SQL
                sql = last_query.get('sql_query', '')
                if 'WHERE' in sql:
                    # Simple extraction of date filters for now
                    date_match = re.search(r'WHERE\s+.*?(date\s*[>=<]+\s*[\'"].*?[\'"])', sql, re.IGNORECASE)
                    if date_match:
                        previous_filters['date_filter'] = date_match.group(1)
        
        for ref in references:
            resolved_ref = ref.copy()
            
            # Handle pronouns based on context
            if ref['type'] == 'pronoun':
                # Get the most recently mentioned entities
                active_entities = context.get('active_entities', {})
                
                # Determine which entity types to consider based on plurality
                if ref['plurality'] == 'singular':
                    # Look for the most recent singular entity
                    entity_found = False
                    for entity_type in ['items', 'categories', 'options', 'option_items']:
                        entities = active_entities.get(entity_type, [])
                        if entities:
                            # Use the most recent entity of this type
                            resolved_ref['resolution'] = entities[-1]
                            resolved_ref['entity_type'] = entity_type
                            entity_found = True
                            break
                    
                    if not entity_found:
                        resolved_ref['is_ambiguous'] = True
                        resolved_ref['entity_type'] = None
                        resolved_ref['resolution'] = None
                
                elif ref['plurality'] == 'plural':
                    # For plural pronouns, collect all relevant entities
                    all_entities = []
                    entity_type_found = None
                    for entity_type in ['items', 'categories', 'options', 'option_items']:
                        entities = active_entities.get(entity_type, [])
                        if entities and len(entities) > 1:
                            all_entities.extend(entities)
                            if not entity_type_found:
                                entity_type_found = entity_type
                    
                    if all_entities:
                        resolved_ref['resolution'] = all_entities
                        resolved_ref['entity_type'] = entity_type_found
                    else:
                        resolved_ref['is_ambiguous'] = True
                        resolved_ref['entity_type'] = None
                        resolved_ref['resolution'] = None
            
            # Handle domain-specific references (like "those orders")
            elif ref['type'] == 'domain_reference':
                entity_type = ref['entity_type']  # e.g., 'orders'
                
                # Special case for "those orders" when previous query was about orders
                if entity_type == 'orders' and previous_query_type == 'order_history':
                    # Create a reference to the previous query's parameters
                    resolved_ref['resolution'] = {
                        'type': 'query_reference',
                        'query_type': 'order_history',
                        'filters': previous_filters
                    }
                    resolved_ref['entity_type'] = 'orders'
                    resolved_ref['is_query_reference'] = True
                else:
                    # Handle other domain references
                    entities = previous_entities.get(entity_type, [])
                    if entities:
                        resolved_ref['resolution'] = entities
                        resolved_ref['entity_type'] = entity_type
                    else:
                        resolved_ref['is_ambiguous'] = True
                        resolved_ref['entity_type'] = entity_type
                        resolved_ref['resolution'] = None
            
            # Handle explicit references (like "the category")
            elif ref['type'] == 'explicit_reference':
                entity_type = ref['entity_type']
                
                # Get active entities of this type
                active_entities = context.get('active_entities', {})
                entities = active_entities.get(entity_type, [])
                
                if entities:
                    if ref.get('plurality') == 'singular' or len(entities) == 1:
                        # Use the most recent entity for singular reference or when only one entity exists
                        resolved_ref['resolution'] = entities[-1]
                    else:
                        # Use all entities of this type for plural references
                        resolved_ref['resolution'] = entities
                else:
                    resolved_ref['is_ambiguous'] = True
                    resolved_ref['resolution'] = None
            
            resolved_references.append(resolved_ref)
        
        return resolved_references
    
    def _generate_clarification_question(self, ambiguous_ref: Dict[str, Any]) -> str:
        """
        Generate a clarification question for an ambiguous reference.
        
        Args:
            ambiguous_ref: The ambiguous reference
            
        Returns:
            A clarification question
        """
        if ambiguous_ref['type'] == 'pronoun':
            if ambiguous_ref['plurality'] == 'singular':
                return f"What {ambiguous_ref['text']} are you referring to?"
            else:
                return f"Which {ambiguous_ref['text']} are you referring to?"
        elif ambiguous_ref['type'] == 'explicit_reference':
            entity_type = ambiguous_ref['entity_type']
            # Convert to singular form correctly
            if entity_type == 'categories':
                singular = 'category'
            elif entity_type.endswith('s'):
                singular = entity_type[:-1]
            else:
                singular = entity_type
                
            return f"Which {singular} are you referring to?"
        
        return "Can you be more specific about what you're referring to?"
    
    def fuzzy_match(self, target: str, choices: List[str], threshold: float = None) -> Tuple[Optional[str], float]:
        """
        Find the best fuzzy match for a target string from a list of choices.
        
        Args:
            target: The string to match
            choices: List of possible matches
            threshold: Optional custom threshold (defaults to class threshold)
            
        Returns:
            Tuple of (best_match, similarity_ratio) or (None, 0) if no match found
        """
        if threshold is None:
            threshold = self.FUZZY_MATCH_THRESHOLD
            
        if not choices:
            return None, 0
        
        best_match = None
        best_ratio = 0
        
        for choice in choices:
            # Calculate similarity ratio using SequenceMatcher
            ratio = SequenceMatcher(None, target.lower(), choice.lower()).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = choice
        
        # Return the best match if it's above the threshold
        if best_ratio >= threshold:
            return best_match, best_ratio
        
        return None, 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the entity resolution service.
        
        Returns:
            Dict with health status information
        """
        status = {
            'service': 'entity_resolution',
            'status': 'ok',
            'db_connector': self.db_connector is not None,
            'cache_stats': {
                'items': len(self.entity_cache['items']),
                'categories': len(self.entity_cache['categories']),
                'options': len(self.entity_cache['options']),
                'option_items': len(self.entity_cache['option_items'])
            }
        }
        
        return status 