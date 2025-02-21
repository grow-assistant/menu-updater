"""Operation patterns for menu management"""
from typing import Dict, Optional, Any, List
from datetime import datetime
import re
import json

# Common operation patterns
COMMON_OPERATIONS = {
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
    query = query.lower()
    for op_type, op_data in COMMON_OPERATIONS.items():
        for pattern in op_data["patterns"]:
            if re.search(pattern, query):
                return {
                    "type": op_type,
                    "steps": op_data["steps"].copy(),
                    "function": op_data["function"],
                    "item_type": op_data.get("type"),
                    "current_step": 0,
                    "params": {}
                }
    return None

def handle_operation_step(operation: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Handle operation step
    
    Args:
        operation: Operation dict with type, steps, and params
        message: User message
        
    Returns:
        Dict with response type and content
    """
    step = operation["steps"][operation["current_step"]]
    
    if step.startswith("get_"):
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
        operation["params"]["value"] = message
        confirms = {
            "confirm_disable": f"Are you sure you want to disable '{message}'? (yes/no)",
            "confirm_price": f"Set price to ${message}? (yes/no)",
            "confirm_time_range": f"Set time range to {operation['params'].get('start_time', '?')}-{message}? (yes/no)"
        }
        return {
            "role": "assistant",
            "content": confirms.get(step, "Please confirm (yes/no)")
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

def store_operation_history(settings: Dict[str, Any], operation: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
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
