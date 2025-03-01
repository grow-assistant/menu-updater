"""
Menu tools for the AI Menu Updater application.
Creates LangChain tools for updating menu items.
"""

import json
import logging
from typing import Callable, Dict, Any, Optional

# Configure logger
logger = logging.getLogger("ai_menu_updater")

# LangChain imports - make backward compatible
try:
    # Try newer LangChain versions
    from langchain_core.tools import BaseTool, Tool
    from pydantic import BaseModel, Field
    
    class MenuUpdateToolInput(BaseModel):
        """Input for MenuUpdateTool."""
        update_spec: str = Field(description="JSON string with menu update specifications")
        
    class MenuUpdateTool(BaseTool):
        """Tool for updating menu items."""
        name = "update_menu"
        description = """Useful for updating menu items, prices, or enabling/disabling items.

The input should be a JSON object with the following structure:
{
  "item_name": "The name of the menu item to update",
  "new_price": 10.99,  // Optional: The new price of the item
  "disabled": true     // Optional: Set to true to disable, false to enable
}

You must include either new_price or disabled, but not necessarily both.
The item_name is always required.

Examples:
- Update price: {"item_name": "French Fries", "new_price": 5.99}
- Disable item: {"item_name": "Club Sandwich", "disabled": true}
- Enable item: {"item_name": "Caesar Salad", "disabled": false}
"""
        
        # Define the input schema
        args_schema = MenuUpdateToolInput
        
        # Store the execute_update_func in a private attribute
        _execute_update_func: Optional[Callable] = None
        
        def __init__(self, execute_update_func: Callable):
            """Initialize with the function to execute updates"""
            super().__init__()
            self._execute_update_func = execute_update_func
            
        def _run(self, update_spec: str) -> str:
            """Run the update through the execute_update_func and return results"""
            try:
                # Parse the update specification
                spec = json.loads(update_spec)
                
                # Log the update
                logger.info(f"Executing menu update: {update_spec}")

                # Execute the update
                result = self._execute_update_func(spec)

                if result.get("success", False):
                    return f"Update successful. Affected {result.get('affected_rows', 0)} rows."
                else:
                    return f"Error updating menu: {result.get('error', 'Unknown error')}"
            except json.JSONDecodeError:
                return "Error: Invalid JSON in update specification"
            except Exception as e:
                return f"Error parsing update specification: {str(e)}"
                
        def _arun(self, update_spec: str):
            """Async version - just calls the normal one for now"""
            raise NotImplementedError("Async execution not implemented")
    
except ImportError:
    # Fallback to older LangChain
    from langchain.tools import Tool

def create_menu_update_tool(execute_update_func: Callable):
    """
    Create a Tool for updating menu items.

    Args:
        execute_update_func: Function that executes menu updates

    Returns:
        Tool: A LangChain Tool for updating menu items
    """
    try:
        # Try to use the new style tool class
        try:
            from langchain_core.tools import BaseTool
            # Check if we're dealing with the version that needs Pydantic
            return MenuUpdateTool(execute_update_func=execute_update_func)
        except (ValueError, AttributeError):
            # This error happens when the BaseTool implementation changed but we have
            # an older LangChain version that doesn't expect Pydantic models
            logger.warning("Falling back to older Tool creation method")
            raise ImportError("Incompatible BaseTool version")
    except (ImportError, NameError):
        # Use old style Tool creation
        def _run_update(update_spec: str) -> str:
            """
            Execute a menu update and return the results as a string.
            
            Args:
                update_spec: JSON string with update specifications
                
            Returns:
                str: String representation of the update results
            """
            try:
                # Parse the update specification
                spec = json.loads(update_spec)
                
                # Log the update
                logger.info(f"Executing menu update: {update_spec}")

                # Execute the update
                result = execute_update_func(spec)

                if result.get("success", False):
                    return f"Update successful. Affected {result.get('affected_rows', 0)} rows."
                else:
                    return f"Error updating menu: {result.get('error', 'Unknown error')}"
            except json.JSONDecodeError:
                return "Error: Invalid JSON in update specification"
            except Exception as e:
                return f"Error parsing update specification: {str(e)}"

        # Create the tool
        return Tool(
            name="update_menu",
            func=_run_update,
            description="""Useful for updating menu items, prices, or enabling/disabling items.

The input should be a JSON object with the following structure:
{
  "item_name": "The name of the menu item to update",
  "new_price": 10.99,  // Optional: The new price of the item
  "disabled": true     // Optional: Set to true to disable, false to enable
}

You must include either new_price or disabled, but not necessarily both.
The item_name is always required.

Examples:
- Update price: {"item_name": "French Fries", "new_price": 5.99}
- Disable item: {"item_name": "Club Sandwich", "disabled": true}
- Enable item: {"item_name": "Caesar Salad", "disabled": false}
""",
        ) 