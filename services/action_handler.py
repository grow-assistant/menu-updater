"""
Action Handler Service for Swoop AI Conversational Query Flow.

This module provides functionality for validating, confirming, and executing 
actions requested by users, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Union, Callable
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    Handles validation, confirmation, and execution of actions requested by users.
    
    Responsibilities:
    - Action validation and authorization
    - Confirmation workflow for critical changes
    - Action execution and result verification
    - Undo/rollback capability
    """
    
    # Action types and their required parameters
    ACTION_TYPES = {
        'update_price': ['item_id', 'new_price'],
        'enable_item': ['item_id'],
        'disable_item': ['item_id'],
        'enable_option': ['option_id'],
        'disable_option': ['option_id'],
        'enable_option_item': ['option_item_id'],
        'disable_option_item': ['option_item_id'],
        'update_option_price': ['option_id', 'new_price'],
        'update_option_item_price': ['option_item_id', 'new_price']
    }
    
    # Actions that require confirmation
    ACTIONS_REQUIRING_CONFIRMATION = [
        'update_price',
        'disable_item',
        'disable_option',
        'disable_option_item',
        'update_option_price', 
        'update_option_item_price'
    ]
    
    def __init__(self, db_connector=None):
        """
        Initialize the action handler service.
        
        Args:
            db_connector: Optional database connector for executing actions
        """
        self.db_connector = db_connector
        self.action_history = []
        self.action_handlers = {
            'update_price': self._handle_update_price,
            'enable_item': self._handle_enable_item,
            'disable_item': self._handle_disable_item,
            'enable_option': self._handle_enable_option,
            'disable_option': self._handle_disable_option,
            'enable_option_item': self._handle_enable_option_item,
            'disable_option_item': self._handle_disable_option_item,
            'update_option_price': self._handle_update_option_price,
            'update_option_item_price': self._handle_update_option_item_price
        }
        logger.info("Initialized ActionHandler")
    
    def validate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an action request.
        
        Args:
            action: Action request with type and parameters
            
        Returns:
            Dict containing:
                - valid: Whether the action is valid
                - missing_parameters: List of required parameters that are missing
                - requires_confirmation: Whether the action requires confirmation
                - error: Error message if invalid
        """
        result = {
            'valid': True,
            'missing_parameters': [],
            'requires_confirmation': False,
            'error': None
        }
        
        # Check if action type is supported
        action_type = action.get('type')
        if not action_type or action_type not in self.ACTION_TYPES:
            result['valid'] = False
            result['error'] = f"Unsupported action type: {action_type}"
            return result
        
        # Check for required parameters
        required_params = self.ACTION_TYPES[action_type]
        for param in required_params:
            if param not in action or action[param] is None:
                result['missing_parameters'].append(param)
                result['valid'] = False
        
        if result['missing_parameters']:
            result['error'] = f"Missing required parameters: {', '.join(result['missing_parameters'])}"
        
        # Check if action requires confirmation
        result['requires_confirmation'] = action_type in self.ACTIONS_REQUIRING_CONFIRMATION
        
        return result
    
    def execute_action(self, action: Dict[str, Any], confirmed: bool = False) -> Dict[str, Any]:
        """
        Execute an action after validation.
        
        Args:
            action: Action request with type and parameters
            confirmed: Whether the action has been confirmed by the user
            
        Returns:
            Dict containing:
                - success: Whether the action was successful
                - requires_confirmation: Whether confirmation is needed before execution
                - message: Success or error message
                - action_id: ID of the executed action (for undo)
                - result: Any result from the action execution
        """
        # First validate the action
        validation = self.validate_action(action)
        
        result = {
            'success': False,
            'requires_confirmation': validation['requires_confirmation'],
            'message': '',
            'action_id': None,
            'result': None
        }
        
        # If the action is invalid, return the validation errors
        if not validation['valid']:
            result['message'] = validation['error']
            return result
        
        # If the action requires confirmation but hasn't been confirmed, request confirmation
        if validation['requires_confirmation'] and not confirmed:
            result['message'] = self._generate_confirmation_message(action)
            return result
        
        # Action is valid and confirmed if needed, so execute it
        try:
            # Record the action in history
            action_id = self._record_action(action)
            result['action_id'] = action_id
            
            # Execute the appropriate handler for this action type
            action_type = action['type']
            if action_type in self.action_handlers:
                handler_result = self.action_handlers[action_type](action)
                result['success'] = handler_result['success']
                result['message'] = handler_result['message']
                result['result'] = handler_result.get('result')
            else:
                result['message'] = f"No handler implemented for action type: {action_type}"
            
            # Update the action history with the result
            self._update_action_result(action_id, result)
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            logger.error(traceback.format_exc())
            result['message'] = f"Error executing action: {str(e)}"
        
        return result
    
    def undo_action(self, action_id: str) -> Dict[str, Any]:
        """
        Undo a previously executed action.
        
        Args:
            action_id: ID of the action to undo
            
        Returns:
            Dict containing:
                - success: Whether the undo was successful
                - message: Success or error message
        """
        result = {
            'success': False,
            'message': ''
        }
        
        # Find the action in history
        action_record = None
        for record in self.action_history:
            if record['id'] == action_id:
                action_record = record
                break
        
        if not action_record:
            result['message'] = f"No action found with ID: {action_id}"
            return result
        
        # Check if the action was already rolled back
        if action_record.get('rolled_back', False):
            result['message'] = "This action has already been rolled back."
            return result
        
        # Perform the rollback based on action type
        try:
            action_type = action_record['action']['type']
            rollback_handler = self._get_rollback_handler(action_type)
            
            if rollback_handler:
                rollback_result = rollback_handler(action_record['action'])
                result['success'] = rollback_result['success']
                result['message'] = rollback_result['message']
                
                # Mark the action as rolled back in history
                if result['success']:
                    action_record['rolled_back'] = True
                    action_record['rollback_timestamp'] = datetime.now().isoformat()
            else:
                result['message'] = f"No rollback handler implemented for action type: {action_type}"
            
        except Exception as e:
            logger.error(f"Error rolling back action: {e}")
            logger.error(traceback.format_exc())
            result['message'] = f"Error rolling back action: {str(e)}"
        
        return result
    
    def _record_action(self, action: Dict[str, Any]) -> str:
        """
        Record an action in the action history.
        
        Args:
            action: The action being executed
            
        Returns:
            The ID assigned to the action
        """
        # Generate a simple timestamp-based ID
        action_id = f"action_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Record the action
        action_record = {
            'id': action_id,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'result': None,
            'rolled_back': False
        }
        
        self.action_history.append(action_record)
        return action_id
    
    def _update_action_result(self, action_id: str, result: Dict[str, Any]) -> None:
        """
        Update the result of an action in the history.
        
        Args:
            action_id: ID of the action
            result: Result of the action execution
        """
        for record in self.action_history:
            if record['id'] == action_id:
                record['result'] = result
                break
    
    def _generate_confirmation_message(self, action: Dict[str, Any]) -> str:
        """
        Generate a confirmation message for an action.
        
        Args:
            action: The action requiring confirmation
            
        Returns:
            A confirmation message
        """
        action_type = action['type']
        
        if action_type == 'update_price':
            return f"Are you sure you want to update the price of item ID {action['item_id']} to ${action['new_price']}?"
        elif action_type == 'disable_item':
            return f"Are you sure you want to disable item ID {action['item_id']}? This will make it unavailable for ordering."
        elif action_type == 'disable_option':
            return f"Are you sure you want to disable option ID {action['option_id']}? This will make it unavailable for ordering."
        elif action_type == 'disable_option_item':
            return f"Are you sure you want to disable option item ID {action['option_item_id']}? This will make it unavailable for ordering."
        elif action_type == 'update_option_price':
            return f"Are you sure you want to update the price of option ID {action['option_id']} to ${action['new_price']}?"
        elif action_type == 'update_option_item_price':
            return f"Are you sure you want to update the price of option item ID {action['option_item_id']} to ${action['new_price']}?"
        
        return f"Are you sure you want to perform this {action_type} action?"
    
    def _get_rollback_handler(self, action_type: str) -> Optional[Callable]:
        """
        Get the appropriate rollback handler for an action type.
        
        Args:
            action_type: Type of the action
            
        Returns:
            Rollback handler function or None if not implemented
        """
        # Map of action types to their rollback handlers
        rollback_handlers = {
            'update_price': self._rollback_update_price,
            'enable_item': self._rollback_enable_item,
            'disable_item': self._rollback_disable_item,
            'enable_option': self._rollback_enable_option,
            'disable_option': self._rollback_disable_option,
            'enable_option_item': self._rollback_enable_option_item,
            'disable_option_item': self._rollback_disable_option_item,
            'update_option_price': self._rollback_update_option_price,
            'update_option_item_price': self._rollback_update_option_item_price
        }
        
        return rollback_handlers.get(action_type)
    
    # Action handler implementations
    
    def _handle_update_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle updating an item's price."""
        # This would be implemented to update the database
        # Placeholder implementation for now
        return {
            'success': True,
            'message': f"Price updated for item ID {action['item_id']} to ${action['new_price']}."
        }
    
    def _handle_enable_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enabling an item."""
        return {
            'success': True,
            'message': f"Item ID {action['item_id']} has been enabled."
        }
    
    def _handle_disable_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disabling an item."""
        return {
            'success': True,
            'message': f"Item ID {action['item_id']} has been disabled."
        }
    
    def _handle_enable_option(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enabling an option."""
        return {
            'success': True,
            'message': f"Option ID {action['option_id']} has been enabled."
        }
    
    def _handle_disable_option(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disabling an option."""
        return {
            'success': True,
            'message': f"Option ID {action['option_id']} has been disabled."
        }
    
    def _handle_enable_option_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enabling an option item."""
        return {
            'success': True,
            'message': f"Option item ID {action['option_item_id']} has been enabled."
        }
    
    def _handle_disable_option_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disabling an option item."""
        return {
            'success': True,
            'message': f"Option item ID {action['option_item_id']} has been disabled."
        }
    
    def _handle_update_option_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle updating an option's price."""
        return {
            'success': True,
            'message': f"Price updated for option ID {action['option_id']} to ${action['new_price']}."
        }
    
    def _handle_update_option_item_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle updating an option item's price."""
        return {
            'success': True,
            'message': f"Price updated for option item ID {action['option_item_id']} to ${action['new_price']}."
        }
    
    # Rollback handler implementations
    
    def _rollback_update_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a price update."""
        # In a real implementation, this would restore the previous price from a backup
        return {
            'success': True,
            'message': f"Price change for item ID {action['item_id']} has been rolled back."
        }
    
    def _rollback_enable_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback enabling an item."""
        return {
            'success': True,
            'message': f"Item ID {action['item_id']} has been disabled again."
        }
    
    def _rollback_disable_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback disabling an item."""
        return {
            'success': True,
            'message': f"Item ID {action['item_id']} has been re-enabled."
        }
    
    def _rollback_enable_option(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback enabling an option."""
        return {
            'success': True,
            'message': f"Option ID {action['option_id']} has been disabled again."
        }
    
    def _rollback_disable_option(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback disabling an option."""
        return {
            'success': True,
            'message': f"Option ID {action['option_id']} has been re-enabled."
        }
    
    def _rollback_enable_option_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback enabling an option item."""
        return {
            'success': True,
            'message': f"Option item ID {action['option_item_id']} has been disabled again."
        }
    
    def _rollback_disable_option_item(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback disabling an option item."""
        return {
            'success': True,
            'message': f"Option item ID {action['option_item_id']} has been re-enabled."
        }
    
    def _rollback_update_option_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback an option price update."""
        return {
            'success': True,
            'message': f"Price change for option ID {action['option_id']} has been rolled back."
        }
    
    def _rollback_update_option_item_price(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback an option item price update."""
        return {
            'success': True,
            'message': f"Price change for option item ID {action['option_item_id']} has been rolled back."
        }
    
    def get_action_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent action history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent action records
        """
        # Return the most recent actions, limited to the specified number
        return sorted(
            self.action_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the action handler service.
        
        Returns:
            Dict with health status information
        """
        status = {
            'service': 'action_handler',
            'status': 'ok',
            'db_connector': self.db_connector is not None,
            'history_size': len(self.action_history),
            'handlers_implemented': len(self.action_handlers),
            'supported_actions': list(self.ACTION_TYPES.keys())
        }
        
        return status 