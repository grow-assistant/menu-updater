"""
Tests for the Response Service.

These tests validate template management, response formatting, and different response types.
"""
import unittest
from unittest.mock import Mock, patch
import pytest
import pandas as pd
import json
from datetime import datetime
from services.response_service import ResponseService


class TestResponseService(unittest.TestCase):
    """Test cases for the ResponseService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = ResponseService()
        
        # Create some test data
        self.test_data = [
            {"id": 1, "name": "Test Item 1", "value": 100},
            {"id": 2, "name": "Test Item 2", "value": 200}
        ]
        
        # Create a test context
        self.test_context = {
            "session_id": "test_session",
            "entity_type": "item",
            "time_period": "last week",
            "last_query": "How many items were sold last week?"
        }
        
        # Create test metadata
        self.test_metadata = {
            "entity_type": "item",
            "time_period": "last week"
        }
    
    def test_initialization(self):
        """Test that the service initializes properly with default templates."""
        self.assertIsNotNone(self.service)
        self.assertIn('data_response', self.service.templates)
        self.assertIn('error_response', self.service.templates)
        self.assertIn('clarification_response', self.service.templates)
    
    def test_initialization_with_custom_templates(self):
        """Test initialization with custom templates."""
        custom_templates = {
            'data_response': [
                "Custom template: {entity_type} data is {data_summary}"
            ],
            'custom_type': [
                "This is a completely new template type: {custom_var}"
            ]
        }
        
        service = ResponseService(custom_templates)
        
        # Should have both default and custom templates
        self.assertIn(custom_templates['data_response'][0], service.templates['data_response'])
        self.assertIn(custom_templates['custom_type'][0], service.templates['custom_type'])
        
        # Should still have default templates
        self.assertGreater(len(service.templates['data_response']), 1)
    
    def test_format_response_data(self):
        """Test formatting a data response."""
        # Arrange
        
        # Act
        response = self.service.format_response(
            response_type='data',
            data=self.test_data,
            context=self.test_context,
            metadata=self.test_metadata
        )
        
        # Assert
        self.assertEqual(response['type'], 'data')
        self.assertIsNotNone(response['text'])
        self.assertIn('item', response['text'])
        self.assertIn('2', response['text'])  # Should mention count
        self.assertEqual(response['data']['count'], 2)
        self.assertEqual(response['data']['records'], self.test_data)
        self.assertIn('total', response['data']['aggregates'])
        self.assertEqual(response['data']['aggregates']['total'], 300)
    
    def test_format_response_data_dataframe(self):
        """Test formatting a data response with pandas DataFrame input."""
        # Arrange
        df = pd.DataFrame(self.test_data)
        
        # Act
        response = self.service.format_response(
            response_type='data',
            data=df,
            context=self.test_context,
            metadata=self.test_metadata
        )
        
        # Assert
        self.assertEqual(response['type'], 'data')
        self.assertIsNotNone(response['text'])
        self.assertEqual(response['data']['count'], 2)
        self.assertEqual(len(response['data']['records']), 2)
    
    def test_format_response_empty(self):
        """Test formatting a response with empty data."""
        # Act
        response = self.service.format_response(
            response_type='data',
            data=[],
            context=self.test_context,
            metadata=self.test_metadata
        )
        
        # Assert
        self.assertEqual(response['type'], 'data')
        self.assertIsNotNone(response['text'])
        self.assertIn('item', response['text'])
        self.assertIn('No', response['text'])  # Should mention no results
        self.assertTrue(response['is_empty'])
        self.assertIsNone(response['data'])
    
    def test_format_response_action(self):
        """Test formatting an action response."""
        # Arrange
        action_data = {
            'action': 'update',
            'entity_type': 'menu item',
            'entity_name': 'Hamburger',
            'success': True,
            'details': 'Price updated to $10.99.'
        }
        
        # Act
        response = self.service.format_response(
            response_type='action',
            data=action_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'action')
        self.assertIsNotNone(response['text'])
        self.assertIn('updated', response['text'])  # Should use past tense
        self.assertIn('Hamburger', response['text'])
        self.assertEqual(response['action'], 'update')
        self.assertEqual(response['data'], action_data)
    
    def test_format_response_action_failure(self):
        """Test formatting a failed action response."""
        # Arrange
        action_data = {
            'action': 'update',
            'entity_type': 'menu item',
            'entity_name': 'Hamburger',
            'success': False,
            'error': 'not_found',
            'error_message': 'Menu item not found'
        }
        
        # Act
        response = self.service.format_response(
            response_type='action',
            data=action_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'action')
        self.assertIsNotNone(response['text'])
        self.assertIn('error', response['text'].lower())
        self.assertIn('not found', response['text'])
        self.assertEqual(response['error'], 'not_found')
    
    def test_format_response_error(self):
        """Test formatting an error response."""
        # Arrange
        error_data = {
            'error': 'invalid_date',
            'message': 'Could not parse the date you provided',
            'recovery_suggestion': 'Try using a format like MM/DD/YYYY'
        }
        
        # Act
        response = self.service.format_response(
            response_type='error',
            data=error_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'error')
        self.assertIsNotNone(response['text'])
        self.assertIn('error', response['text'].lower())
        self.assertIn('Could not parse', response['text'])
        self.assertIn('Try using', response['text'])  # Should include recovery suggestion
        self.assertEqual(response['error'], 'invalid_date')
    
    def test_format_response_error_with_default_recovery(self):
        """Test formatting an error response with default recovery suggestion."""
        # Arrange
        error_data = {
            'error': 'invalid_date',
            'message': 'Could not parse the date you provided'
            # No recovery_suggestion provided - should use default
        }
        
        # Act
        response = self.service.format_response(
            response_type='error',
            data=error_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'error')
        self.assertIn('Could not parse', response['text'])
        # Should use default recovery suggestion for invalid_date
        self.assertIn('valid date format', response['text'].lower())
    
    def test_format_response_clarification(self):
        """Test formatting a clarification response."""
        # Arrange
        clarification_data = {
            'clarification_type': 'time_period',
            'clarification_subject': 'what time period you are interested in',
            'options': ['last week', 'last month', 'year to date']
        }
        
        # Act
        response = self.service.format_response(
            response_type='clarification',
            data=clarification_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'clarification')
        self.assertIsNotNone(response['text'])
        self.assertIn('time period', response['text'].lower())
        # Should include options
        self.assertIn('last week', response['text'])
        self.assertIn('last month', response['text'])
        self.assertTrue(response['requires_response'])
        self.assertEqual(response['clarification_type'], 'time_period')
    
    def test_format_response_confirmation(self):
        """Test formatting a confirmation response."""
        # Arrange
        confirmation_data = {
            'action': 'delete',
            'entity_type': 'menu item',
            'entity_name': 'Hamburger',
            'consequences': 'This cannot be undone.'
        }
        
        # Act
        response = self.service.format_response(
            response_type='confirmation',
            data=confirmation_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'confirmation')
        self.assertIsNotNone(response['text'])
        self.assertIn('delete', response['text'])
        self.assertIn('Hamburger', response['text'])
        self.assertIn('cannot be undone', response['text'])
        self.assertTrue(response['requires_confirmation'])
        self.assertEqual(response['action'], 'delete')
    
    def test_format_response_summary(self):
        """Test formatting a summary response."""
        # Arrange
        summary_data = {
            'entity_type': 'sales',
            'time_period': 'last quarter',
            'summary_points': [
                'Total revenue was $15,000',
                'Average order value was $35',
                'Best selling item was Hamburger'
            ]
        }
        
        # Act
        response = self.service.format_response(
            response_type='summary',
            data=summary_data,
            context=self.test_context
        )
        
        # Assert
        self.assertEqual(response['type'], 'summary')
        self.assertIsNotNone(response['text'])
        self.assertIn('sales', response['text'])
        self.assertIn('last quarter', response['text'])
        # Should include all summary points in a natural format
        self.assertIn('Total revenue', response['text'])
        self.assertIn('Average order', response['text'])
        self.assertIn('Best selling', response['text'])
        self.assertEqual(response['summary'], summary_data['summary_points'])
    
    def test_template_selection_avoids_repetition(self):
        """Test that template selection avoids repetition."""
        # Call format_response multiple times with the same type
        # and verify we don't get the same template twice in a row
        last_text = None
        
        for _ in range(5):
            response = self.service.format_response(
                response_type='success',
                data={},
                context=self.test_context
            )
            
            if last_text is not None:
                # If we have few templates, they might repeat after cycling through
                # So only check direct repetition
                if len(self.service.templates['success_response']) > 1:
                    self.assertNotEqual(response['text'], last_text)
                    
            last_text = response['text']
    
    def test_error_handling_in_format_response(self):
        """Test that format_response handles exceptions gracefully."""
        # Create a subclass that will raise an exception in a handler
        class BrokenResponseService(ResponseService):
            def data_response(self, data, context, metadata):
                raise ValueError("Test exception")
        
        service = BrokenResponseService()
        
        # Act - should not raise an exception
        response = service.format_response(
            response_type='data',
            data=self.test_data,
            context=self.test_context
        )
        
        # Assert - should fall back to error response
        self.assertEqual(response['type'], 'data')
        self.assertIsNotNone(response['text'])
        self.assertIn('error', response['text'].lower())
        self.assertIn('Test exception', response['text'])
    
    def test_generate_data_summary(self):
        """Test the _generate_data_summary method."""
        # Test with empty data
        summary = self.service._generate_data_summary([], 'item', 'last week')
        self.assertEqual(summary, "No item found for last week.")
        
        # Test with single item
        summary = self.service._generate_data_summary([{'id': 1}], 'item', 'last week')
        self.assertEqual(summary, "1 item found for last week.")
        
        # Test with multiple items
        summary = self.service._generate_data_summary([{'id': 1}, {'id': 2}], 'item', 'last week')
        self.assertEqual(summary, "2 items found for last week.")
    
    def test_format_data_for_output(self):
        """Test the _format_data_for_output method."""
        # Test with regular data
        formatted = self.service._format_data_for_output(self.test_data)
        self.assertEqual(formatted['count'], 2)
        self.assertEqual(formatted['records'], self.test_data)
        self.assertIn('aggregates', formatted)
        self.assertEqual(formatted['aggregates']['total'], 300)
        self.assertEqual(formatted['aggregates']['average'], 150)
        
        # Test with non-numeric data (no aggregates)
        non_numeric_data = [{'id': 1, 'name': 'Test'}, {'id': 2, 'name': 'Test 2'}]
        formatted = self.service._format_data_for_output(non_numeric_data)
        self.assertEqual(formatted['count'], 2)
        self.assertEqual(formatted['records'], non_numeric_data)
        self.assertNotIn('aggregates', formatted)
    
    def test_health_check(self):
        """Test the health_check method."""
        result = self.service.health_check()
        self.assertEqual(result['service'], 'response_service')
        self.assertEqual(result['status'], 'ok')
        self.assertGreater(result['template_types'], 0)
        self.assertGreater(result['total_templates'], 0)
        self.assertEqual(result['template_test'], 'ok')


if __name__ == "__main__":
    unittest.main()
