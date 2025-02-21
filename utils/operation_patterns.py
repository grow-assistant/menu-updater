"""Operation patterns for menu management"""
from typing import Dict, Optional, Any
from datetime import datetime
import re

# Common operation patterns
COMMON_OPERATIONS = {
    "disable_bulk": {
        "patterns": [
            r"disable (?:all|every) (.+)",
            r"turn off (?:all|every) (.+)",
            r"deactivate (?:all|every) (.+)"  # Matches bulk disable patterns
        ],
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_by_pattern",
        "type": "Menu Item"
    },
    "disable_bulk_options": {
        "patterns": [
            r"disable all options? (?:for|in|on) (.+)",
            r"turn off all options? (?:for|in|on) (.+)",
            r"deactivate all options? (?:for|in|on) (.+)"  # Matches option disable patterns
        ],
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_options_by_pattern",
        "type": "Item Option"
    },
    "disable_bulk_option_items": {
        "patterns": [
            r"disable all option items? (?:for|in|on) (.+)",
            r"turn off all option items? (?:for|in|on) (.+)",
            r"deactivate all option items? (?:for|in|on) (.+)"
        ],
        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
        "function": "disable_option_items_by_pattern",
        "type": "Option Item"
    },
    "disable_item": {
        "patterns": [
            r"disable (?:the )?(?:menu )?item",
            r"turn off (?:the )?(?:menu )?item",
            r"deactivate (?:the )?(?:menu )?item"
        ],
        "steps": ["get_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "type": "Menu Item"
    },
    "disable_option": {
        "patterns": [
            r"disable (?:the )?(?:menu )?option",
            r"turn off (?:the )?(?:menu )?option",
            r"deactivate (?:the )?(?:menu )?option"
        ],
        "steps": ["get_option_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "type": "Item Option"
    },
    "disable_option_item": {
        "patterns": [
            r"disable (?:the )?option item",
            r"turn off (?:the )?option item",
            r"deactivate (?:the )?option item"
        ],
        "steps": ["get_option_item_name", "confirm_disable", "execute_disable"],
        "function": "disable_by_name",
        "type": "Option Item"
    },
    "update_price": {
        "patterns": [
            r"update (?:the )?price",
            r"change (?:the )?price",
            r"set (?:the )?price"
        ],
        "steps": ["get_item_name", "get_new_price", "confirm_price", "execute_price_update"],
        "function": "update_menu_item_price"
    },
    "update_time_range": {
        "patterns": [
            r"update (?:the )?time range",
            r"change (?:the )?time range",
            r"set (?:the )?time range"
        ],
        "steps": ["get_category_name", "get_start_time", "get_end_time", "confirm_time_range", "execute_time_update"],
        "function": "update_category_time_range"
    }
}


def match_operation(query: str) -> Optional[Dict[str, Any]]:
    """Match query against common operation patterns
    
    Args:
        query: User query string
        
    Returns:
        Dict with operation type and parameters if matched,
        None otherwise
    """
    query_lower = query.lower()
    for op_type, op_data in COMMON_OPERATIONS.items():
        for pattern in op_data["patterns"]:
            if match := re.search(pattern, query_lower):
                operation = {
                    "type": op_type,
                    "steps": op_data["steps"].copy(),
                    "function": op_data["function"],
                    "item_type": op_data.get("type"),
                    "current_step": 0,
                    "params": {}
                }
                if len(match.groups()) > 0:
                    # Extract pattern from original query
                    start, end = match.span(1)
                    original_text = query[start:end]
                    # For options and option items, extract just the item name
                    if "option items" in query.lower():
                        # Extract item name after "for"
                        parts = query.split(" for ")
                        if len(parts) > 1:
                            # Get original case item name
                            item_name = parts[1].strip()
                            return {
                                "type": "disable_bulk_option_items",
                                "steps": ["confirm_items", "confirm_disable", "execute_disable"],
                                "function": "disable_option_items_by_pattern",
                                "item_type": "Option Item",
                                "current_step": 0,
                                "params": {"pattern": item_name}
                            }
                    elif "options" in query.lower():
                        # Extract item name after "for"
                        parts = query.split(" for ")
                        if len(parts) > 1:
                            # Get original case item name
                            item_name = parts[1].strip()
                            return {
                                "type": "disable_bulk_options",
                                "steps": ["confirm_items", "confirm_disable", "execute_disable"],
                                "function": "disable_options_by_pattern",
                                "item_type": "Item Option",
                                "current_step": 0,
                                "params": {"pattern": item_name}
                            }
                    # For regular items
                    return {
                        "type": "disable_bulk",
                        "steps": ["confirm_items", "confirm_disable", "execute_disable"],
                        "function": "disable_by_pattern",
                        "item_type": "Menu Item",
                        "current_step": 0,
                        "params": {"pattern": original_text.lower()}
                    }
                return operation
    return None


def handle_operation_step(
    operation: Dict[str, Any], 
    message: str
) -> Dict[str, Any]:
    """Handle operation step including bulk operations
    
    Args:
        operation: Operation dict with type, steps, and params
        message: User message
        
    Returns:
        Dict with response type and content
    """
    # Convert pattern to lowercase for consistency
    if "pattern" in operation.get("params", {}):
        operation["params"]["pattern"] = operation["params"]["pattern"].lower()
        
    step = operation["steps"][operation["current_step"]]
    
    if step == "confirm_items":
        # For bulk operations, show matching items
        try:
            from utils.menu_operations import (
                disable_by_pattern,
                disable_options_by_pattern,
                disable_option_items_by_pattern
            )
            from utils.database_functions import get_db_connection
            
            pattern = operation["params"]["pattern"]
            conn = get_db_connection()
            
            # Get current state
            if operation["type"] == "disable_bulk":
                success, result = disable_by_pattern(conn, pattern)
            elif operation["type"] == "disable_bulk_options":
                success, result = disable_options_by_pattern(conn, pattern)
            elif operation["type"] == "disable_bulk_option_items":
                success, result = disable_option_items_by_pattern(conn, pattern)
            else:
                return {"role": "assistant", "content": "Invalid operation type"}
                
            if not success:
                return {"role": "assistant", "content": result}
                
            confirmation_msg = (
                f"Found these items:\n{result}\n"
                "Would you like to proceed with disabling them? (yes/no)"
            )
            return {
                "role": "assistant",
                "content": confirmation_msg
            }
            
        except Exception as e:
            return {"role": "assistant", "content": f"Error finding items: {str(e)}"}
    
    elif step.startswith("get_"):
        # Get item/option name or value
        prompts = {
            "get_item_name": "Which menu item?",
            "get_option_name": "Which menu option?",
            "get_option_item_name": "Which option item?",
            "get_new_price": "What should the new price be?",
            "get_category_name": "Which category?",
            "get_start_time": "What should the start time be? (0000-2359)",
            "get_end_time": "What should the end time be? (0000-2359)"
        }
        return {
            "role": "assistant",
            "content": prompts.get(step, "Please provide more information")
        }
        
    elif step.startswith("confirm_"):
        # Confirm operation
        if step == "confirm_disable":
            if message.lower() != "yes":
                return {
                "role": "assistant",
                "content": "Operation cancelled"
            }
            return {
                "role": "assistant",
                "content": "Are you absolutely sure? This operation cannot be undone. (yes/no)"
            }
        else:
            operation["params"]["value"] = message
            confirms = {
                "confirm_price": f"Set price to ${message}? (yes/no)",
                "confirm_time_range": f"Set time range to {operation['params'].get('start_time', '?')}-{message}? (yes/no)"
            }
            prompt = confirms.get(step, "Please confirm (yes/no)")
            return {
                "role": "assistant",
                "content": prompt
            }
        
    elif step.startswith("execute_"):
        # Execute operation if confirmed
        if message.lower() == "yes":
            return {
                "role": "function",
                "name": operation["function"],
                "params": operation["params"]
            }
        else:
            return {
                "role": "assistant",
                "content": "Operation cancelled"
            }
            
    return {
        "role": "assistant",
        "content": "I didn't understand that. Please try again."
    }


def store_operation_history(
    settings: Dict[str, Any], 
    operation: Dict[str, Any], 
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """Store operation in history
    
    Args:
        settings: Location settings dict
        operation: Operation that was executed
        result: Result of the operation
        
    Returns:
        Updated settings dict
    """
    if "operation_history" not in settings:
        settings["operation_history"] = []
        
    history_entry = {
        "type": operation["type"],
        "params": operation["params"],
        "result": result,
        "timestamp": str(datetime.now())
    }
    
    settings["operation_history"].append(history_entry)
    
    # Keep last 50 operations
    if len(settings["operation_history"]) > 50:
        settings["operation_history"] = settings["operation_history"][-50:]
        
    return settings
