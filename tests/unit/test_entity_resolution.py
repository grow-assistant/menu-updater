"""Unit tests for the Entity Resolution Service."""
import unittest
from unittest.mock import MagicMock, patch
import pytest
from services.entity_resolution import EntityResolutionService


class TestEntityResolutionService(unittest.TestCase):
    """Test cases for EntityResolutionService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = EntityResolutionService()
    
    def test_initialization(self):
        """Test that the service initializes properly."""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.FUZZY_MATCH_THRESHOLD, 0.8)
        self.assertDictEqual(self.service.entity_cache, {
            'items': {},
            'categories': {},
            'options': {},
            'option_items': {}
        })
    
    def test_extract_direct_entities_with_db_connector(self):
        """Test extracting direct entities with a DB connector."""
        # Create a mock DB connector
        mock_db = MagicMock()
        
        # Setup the service with the mock DB
        service = EntityResolutionService(db_connector=mock_db)
        
        # Call the method
        result = service._extract_direct_entities("Show me the chicken burger item")
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('items', result)
        self.assertIn('categories', result)
        self.assertIn('options', result)
        self.assertIn('option_items', result)
    
    def test_extract_references(self):
        """Test extracting entity references from a query."""
        # Test singular pronouns
        refs = self.service._extract_references("Can you show me it?")
        self.assertTrue(any(ref['text'] == 'it' for ref in refs))
        self.assertTrue(any(ref['type'] == 'pronoun' for ref in refs))
        self.assertTrue(any(ref['plurality'] == 'singular' for ref in refs))
        
        # Test plural pronouns
        refs = self.service._extract_references("What are these?")
        self.assertTrue(any(ref['text'] == 'these' for ref in refs))
        self.assertTrue(any(ref['type'] == 'pronoun' for ref in refs))
        self.assertTrue(any(ref['plurality'] == 'plural' for ref in refs))
        
        # Test explicit references
        refs = self.service._extract_references("Tell me about that category.")
        # Check that we have a reference with "category" in the text
        self.assertTrue(any('category' in ref['text'] for ref in refs))
        # Check that we have an explicit reference type
        self.assertTrue(any(ref['type'] == 'explicit_reference' for ref in refs))
        # For references with explicit_reference type, check entity_type
        explicit_refs = [ref for ref in refs if ref['type'] == 'explicit_reference']
        if explicit_refs:
            self.assertEqual(explicit_refs[0]['entity_type'], 'categorys')
    
    def test_resolve_references_singular_pronoun(self):
        """Test resolving singular pronouns to entities."""
        # Setup context with some entities
        context = {
            'active_entities': {
                'items': [{'id': 1, 'name': 'Burger'}],
                'categories': [],
                'options': [],
                'option_items': []
            }
        }
        
        # Create a reference to resolve
        refs = [
            {
                'text': 'it', 
                'start': 0, 
                'end': 2, 
                'type': 'pronoun', 
                'plurality': 'singular'
            }
        ]
        
        # Resolve the references
        resolved_refs = self.service._resolve_references(refs, context)
        
        # Check the results
        self.assertEqual(len(resolved_refs), 1)
        self.assertEqual(resolved_refs[0]['entity_type'], 'items')
        self.assertEqual(resolved_refs[0]['resolution'], {'id': 1, 'name': 'Burger'})
        self.assertFalse(resolved_refs[0].get('is_ambiguous', False))
    
    def test_resolve_references_plural_pronoun(self):
        """Test resolving plural pronouns to entities."""
        # Setup context with some entities
        context = {
            'active_entities': {
                'items': [{'id': 1, 'name': 'Burger'}, {'id': 2, 'name': 'Pizza'}],
                'categories': [],
                'options': [],
                'option_items': []
            }
        }
        
        # Create a reference to resolve
        refs = [
            {
                'text': 'they', 
                'start': 0, 
                'end': 4, 
                'type': 'pronoun', 
                'plurality': 'plural'
            }
        ]
        
        # Resolve the references
        resolved_refs = self.service._resolve_references(refs, context)
        
        # Check the results
        self.assertEqual(len(resolved_refs), 1)
        self.assertEqual(resolved_refs[0]['entity_type'], 'items')
        self.assertListEqual(resolved_refs[0]['resolution'], [{'id': 1, 'name': 'Burger'}, {'id': 2, 'name': 'Pizza'}])
        self.assertFalse(resolved_refs[0].get('is_ambiguous', False))
    
    def test_resolve_references_explicit_reference(self):
        """Test resolving explicit references like 'that category'."""
        # Setup context with some entities
        context = {
            'active_entities': {
                'items': [],
                'categories': [{'id': 1, 'name': 'Burgers'}],
                'options': [],
                'option_items': []
            }
        }
        
        # Create a reference to resolve
        refs = [
            {
                'text': 'that category', 
                'start': 0, 
                'end': 13, 
                'type': 'explicit_reference', 
                'entity_type': 'categories'
            }
        ]
        
        # Resolve the references
        resolved_refs = self.service._resolve_references(refs, context)
        
        # Check the results
        self.assertEqual(len(resolved_refs), 1)
        self.assertEqual(resolved_refs[0]['entity_type'], 'categories')
        self.assertEqual(resolved_refs[0]['resolution'], {'id': 1, 'name': 'Burgers'})
        self.assertFalse(resolved_refs[0].get('is_ambiguous', False))
    
    def test_resolve_references_ambiguous(self):
        """Test resolving references that are ambiguous."""
        # Setup context with no matching entities
        context = {
            'active_entities': {
                'items': [],
                'categories': [],
                'options': [],
                'option_items': []
            }
        }
        
        # Create a reference to resolve
        refs = [
            {
                'text': 'it', 
                'start': 0, 
                'end': 2, 
                'type': 'pronoun', 
                'plurality': 'singular'
            }
        ]
        
        # Resolve the references
        resolved_refs = self.service._resolve_references(refs, context)
        
        # Check the results
        self.assertEqual(len(resolved_refs), 1)
        self.assertTrue(resolved_refs[0].get('is_ambiguous', False))
        self.assertIsNone(resolved_refs[0].get('resolution'))
    
    def test_resolve_entities_integration(self):
        """Test the full entity resolution flow."""
        # Setup context with some entities
        context = {
            'active_entities': {
                'items': [{'id': 1, 'name': 'Burger'}],
                'categories': [{'id': 1, 'name': 'Burgers'}],
                'options': [],
                'option_items': []
            }
        }
        
        # Resolve entities in a query
        result = self.service.resolve_entities("Can you tell me more about it?", context)
        
        # Check the results
        self.assertIn('entities', result)
        self.assertIn('is_ambiguous', result)
        self.assertIn('needs_clarification', result)
        self.assertIn('references', result)
    
    def test_generate_clarification_question(self):
        """Test generating clarification questions for ambiguous references."""
        # Test singular pronoun
        ambiguous_ref = {
            'text': 'it', 
            'type': 'pronoun', 
            'plurality': 'singular'
        }
        question = self.service._generate_clarification_question(ambiguous_ref)
        self.assertIn("What it are you referring to?", question)
        
        # Test plural pronoun
        ambiguous_ref = {
            'text': 'these', 
            'type': 'pronoun', 
            'plurality': 'plural'
        }
        question = self.service._generate_clarification_question(ambiguous_ref)
        self.assertIn("Which these are you referring to?", question)
        
        # Test explicit reference
        ambiguous_ref = {
            'text': 'that category', 
            'type': 'explicit_reference', 
            'entity_type': 'categories'
        }
        question = self.service._generate_clarification_question(ambiguous_ref)
        self.assertIn("Which category are you referring to?", question)
    
    def test_fuzzy_match(self):
        """Test fuzzy matching of strings."""
        # Test exact match
        match, ratio = self.service.fuzzy_match("burger", ["burger", "pizza", "salad"])
        self.assertEqual(match, "burger")
        self.assertEqual(ratio, 1.0)
        
        # Test close match
        match, ratio = self.service.fuzzy_match("burgr", ["burger", "pizza", "salad"])
        self.assertEqual(match, "burger")
        self.assertTrue(ratio > 0.8)
        
        # Test no match above threshold
        match, ratio = self.service.fuzzy_match("xyz", ["burger", "pizza", "salad"])
        self.assertIsNone(match)
        self.assertEqual(ratio, 0)
        
        # Test empty choices
        match, ratio = self.service.fuzzy_match("burger", [])
        self.assertIsNone(match)
        self.assertEqual(ratio, 0)
        
        # Test with custom threshold
        # Use a much higher threshold to ensure no match
        match, ratio = self.service.fuzzy_match("burgr", ["burger", "pizza", "salad"], threshold=0.99)
        self.assertIsNone(match)  # Should not match with higher threshold
    
    def test_health_check(self):
        """Test the health check function."""
        health = self.service.health_check()
        self.assertEqual(health['service'], 'entity_resolution')
        self.assertEqual(health['status'], 'ok')
        self.assertFalse(health['db_connector'])
        self.assertIn('cache_stats', health)


if __name__ == '__main__':
    unittest.main() 