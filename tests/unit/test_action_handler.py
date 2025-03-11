"""Unit tests for the Action Handler Service."""
import unittest
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime
from services.action_handler import ActionHandler


class TestActionHandler(unittest.TestCase):
    """Test cases for ActionHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = ActionHandler()
    
    def test_initialization(self):
        """Test that the handler initializes properly."""
        self.assertIsNotNone(self.handler)
        self.assertEqual(len(self.handler.action_history), 0)
        self.assertEqual(len(self.handler.ACTION_TYPES), 9)  # Should have 9 action types
        self.assertEqual(len(self.handler.ACTIONS_REQUIRING_CONFIRMATION), 6)  # 6 actions require confirmation
    
    def test_validate_action_valid(self):
        """Test validating a valid action."""
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        result = self.handler.validate_action(action)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['missing_parameters']), 0)
        self.assertTrue(result['requires_confirmation'])
        self.assertIsNone(result['error'])
    
    def test_validate_action_invalid_type(self):
        """Test validating an action with an invalid type."""
        action = {
            'type': 'nonexistent_action',
            'item_id': 123
        }
        
        result = self.handler.validate_action(action)
        
        self.assertFalse(result['valid'])
        self.assertIn('Unsupported action type', result['error'])
    
    def test_validate_action_missing_parameters(self):
        """Test validating an action with missing required parameters."""
        action = {
            'type': 'update_price',
            'item_id': 123
            # Missing 'new_price'
        }
        
        result = self.handler.validate_action(action)
        
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['missing_parameters']), 1)
        self.assertIn('new_price', result['missing_parameters'])
        self.assertIn('Missing required parameters', result['error'])
    
    def test_execute_action_invalid(self):
        """Test executing an invalid action."""
        action = {
            'type': 'update_price',
            # Missing required parameters
        }
        
        result = self.handler.execute_action(action)
        
        self.assertFalse(result['success'])
        self.assertIn('message', result)
        self.assertIsNone(result['action_id'])
    
    def test_execute_action_requires_confirmation(self):
        """Test executing an action that requires confirmation without confirmation."""
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        result = self.handler.execute_action(action, confirmed=False)
        
        self.assertFalse(result['success'])
        self.assertTrue(result['requires_confirmation'])
        self.assertIn('Are you sure', result['message'])
        self.assertIsNone(result['action_id'])
    
    def test_execute_action_confirmed(self):
        """Test executing an action with confirmation."""
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        result = self.handler.execute_action(action, confirmed=True)
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['action_id'])
        self.assertEqual(len(self.handler.action_history), 1)
        self.assertIn('Price updated', result['message'])
    
    def test_execute_action_no_confirmation_needed(self):
        """Test executing an action that doesn't require confirmation."""
        action = {
            'type': 'enable_item',
            'item_id': 123
        }
        
        result = self.handler.execute_action(action)
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['action_id'])
        self.assertEqual(len(self.handler.action_history), 1)
        self.assertIn('enabled', result['message'])
    
    def test_undo_action_nonexistent(self):
        """Test undoing a nonexistent action."""
        result = self.handler.undo_action("nonexistent_id")
        
        self.assertFalse(result['success'])
        self.assertIn('No action found', result['message'])
    
    def test_undo_action_already_rolled_back(self):
        """Test undoing an action that's already been rolled back."""
        # First execute and roll back an action
        action = {
            'type': 'enable_item',
            'item_id': 123
        }
        
        execute_result = self.handler.execute_action(action)
        action_id = execute_result['action_id']
        
        # Mark it as rolled back
        for record in self.handler.action_history:
            if record['id'] == action_id:
                record['rolled_back'] = True
                break
        
        # Try to roll it back again
        result = self.handler.undo_action(action_id)
        
        self.assertFalse(result['success'])
        self.assertIn('already been rolled back', result['message'])
    
    def test_undo_action_successful(self):
        """Test successfully undoing an action."""
        # First execute an action
        action = {
            'type': 'enable_item',
            'item_id': 123
        }
        
        execute_result = self.handler.execute_action(action)
        action_id = execute_result['action_id']
        
        # Now undo it
        result = self.handler.undo_action(action_id)
        
        self.assertTrue(result['success'])
        self.assertIn('disabled again', result['message'])
        
        # Check that it's marked as rolled back in history
        for record in self.handler.action_history:
            if record['id'] == action_id:
                self.assertTrue(record['rolled_back'])
                self.assertIn('rollback_timestamp', record)
    
    def test_record_action(self):
        """Test recording an action in history."""
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        action_id = self.handler._record_action(action)
        
        self.assertIsNotNone(action_id)
        self.assertEqual(len(self.handler.action_history), 1)
        
        # Check that the record has the expected structure
        record = self.handler.action_history[0]
        self.assertEqual(record['id'], action_id)
        self.assertEqual(record['action'], action)
        self.assertIn('timestamp', record)
        self.assertIsNone(record['result'])
        self.assertFalse(record['rolled_back'])
    
    def test_update_action_result(self):
        """Test updating an action result in history."""
        # First record an action
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        action_id = self.handler._record_action(action)
        
        # Now update its result
        result = {
            'success': True,
            'message': 'Price updated successfully'
        }
        
        self.handler._update_action_result(action_id, result)
        
        # Check that the result was updated
        record = self.handler.action_history[0]
        self.assertEqual(record['result'], result)
    
    def test_generate_confirmation_message(self):
        """Test generating confirmation messages for different actions."""
        # Test update_price
        action = {
            'type': 'update_price',
            'item_id': 123,
            'new_price': 9.99
        }
        
        message = self.handler._generate_confirmation_message(action)
        self.assertIn('Are you sure you want to update the price', message)
        self.assertIn('123', message)
        self.assertIn('9.99', message)
        
        # Test disable_item
        action = {
            'type': 'disable_item',
            'item_id': 123
        }
        
        message = self.handler._generate_confirmation_message(action)
        self.assertIn('Are you sure you want to disable item', message)
        self.assertIn('123', message)
        self.assertIn('unavailable', message)
        
        # Test a generic action
        action = {
            'type': 'custom_action',
            'param': 'value'
        }
        
        message = self.handler._generate_confirmation_message(action)
        self.assertIn('Are you sure you want to perform this custom_action', message)
    
    def test_get_rollback_handler(self):
        """Test getting rollback handlers for different action types."""
        # Should have a handler for update_price
        handler = self.handler._get_rollback_handler('update_price')
        self.assertIsNotNone(handler)
        
        # Should have a handler for enable_item
        handler = self.handler._get_rollback_handler('enable_item')
        self.assertIsNotNone(handler)
        
        # Should return None for an unknown action type
        handler = self.handler._get_rollback_handler('nonexistent_action')
        self.assertIsNone(handler)
    
    def test_action_handlers(self):
        """Test that all action handlers work correctly."""
        for action_type, params in self.handler.ACTION_TYPES.items():
            # Create an action with the required parameters
            action = {'type': action_type}
            for param in params:
                if 'id' in param:
                    action[param] = 123
                elif 'price' in param:
                    action[param] = 9.99
            
            # Get the handler for this action type
            handler = self.handler.action_handlers.get(action_type)
            self.assertIsNotNone(handler, f"No handler for {action_type}")
            
            # Call the handler
            result = handler(action)
            
            # Check the result
            self.assertTrue(result['success'])
            self.assertIn('message', result)
    
    def test_get_action_history(self):
        """Test getting action history."""
        # Add some actions to history
        for i in range(15):
            action = {
                'type': 'update_price',
                'item_id': i,
                'new_price': 9.99
            }
            self.handler.execute_action(action, confirmed=True)
        
        # Get the history with default limit
        history = self.handler.get_action_history()
        self.assertEqual(len(history), 10)  # Default limit is 10
        
        # Check that it's sorted by timestamp descending
        for i in range(1, len(history)):
            self.assertGreaterEqual(
                datetime.fromisoformat(history[i-1]['timestamp']),
                datetime.fromisoformat(history[i]['timestamp'])
            )
        
        # Get the history with custom limit
        history = self.handler.get_action_history(limit=5)
        self.assertEqual(len(history), 5)
    
    def test_health_check(self):
        """Test the health check function."""
        health = self.handler.health_check()
        self.assertEqual(health['service'], 'action_handler')
        self.assertEqual(health['status'], 'ok')
        self.assertFalse(health['db_connector'])
        self.assertEqual(health['history_size'], 0)
        self.assertEqual(health['handlers_implemented'], 9)
        self.assertEqual(len(health['supported_actions']), 9)


if __name__ == '__main__':
    unittest.main() 