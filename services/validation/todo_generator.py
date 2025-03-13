"""
Todo Item Generator Service.

This service transforms SQL validation failures into actionable todo items for developers,
enabling the circular feedback mechanism described in the AI Agent Development Plan.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import json

logger = logging.getLogger(__name__)

class TodoItemGenerator:
    """Service to generate todo items from validation failures."""
    
    def __init__(self, todo_storage_path="todo_items", storage_path=None):
        """
        Initialize the todo item generator.
        
        Args:
            todo_storage_path: Path to store todo items (default parameter name)
            storage_path: Alternate name for todo_storage_path (for compatibility)
        """
        # Support both parameter names for compatibility
        self.todo_storage_path = storage_path if storage_path is not None else todo_storage_path
        
        # Create the directory if it doesn't exist
        if not os.path.exists(self.todo_storage_path):
            try:
                os.makedirs(self.todo_storage_path)
                logger.info(f"Created todo storage directory: {self.todo_storage_path}")
            except Exception as e:
                logger.error(f"Failed to create todo storage directory: {e}")
    
    def generate_todo_items(self, validation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate todo items from validation failures.
        
        Args:
            validation_result: The validation result from SQL validation
            
        Returns:
            List of todo items
        """
        todo_items = []
        
        # Check if validation failed
        if not validation_result.get("validation_status", True):
            # Get validation details
            validation_details = validation_result.get("validation_details", {})
            
            # Get mismatches
            mismatches = validation_details.get("data_point_mismatches", [])
            
            # Create a todo item for each mismatch
            for i, mismatch in enumerate(mismatches):
                todo_item = self._create_todo_item(validation_result, mismatch, i+1)
                todo_items.append(todo_item)
                
        # Save todo items to file
        if todo_items:
            self._save_todo_items(todo_items, validation_result)
            
        return todo_items
    
    def _create_todo_item(self, validation_result: Dict[str, Any], 
                          mismatch: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Create a todo item for a specific mismatch.
        
        Args:
            validation_result: The validation result
            mismatch: The specific mismatch
            index: The index of the mismatch
            
        Returns:
            A todo item dictionary
        """
        # Generate a unique ID for the todo item
        todo_id = str(uuid.uuid4())
        
        # Get the query that produced the issue
        sql_query = validation_result.get("sql_query", "")
        
        # Get the response fragment with the issue
        response_fragment = mismatch.get("response_fragment", "")
        
        # Generate a descriptive title based on the mismatch
        title = f"Fix response accuracy issue: {response_fragment[:50]}..." if response_fragment else "Fix response accuracy issue"
        
        # Generate a detailed description
        description = self._generate_description(validation_result, mismatch)
        
        # Create todo item
        todo_item = {
            "id": todo_id,
            "title": title,
            "description": description,
            "severity": "HIGH" if "customer" in str(mismatch) else "MEDIUM",
            "status": "OPEN",
            "created_at": datetime.now().isoformat(),
            "validation_id": validation_result.get("validation_id", ""),
            "sql_query": sql_query,
            "response_fragment": response_fragment,
            "expected_values": self._extract_expected_values(mismatch),
            "component": "ResponseGenerator",
            "assigned_to": "",
            "due_date": "",
            "tags": ["ai_response", "data_accuracy", "critique_agent"]
        }
        
        return todo_item
    
    def _generate_description(self, validation_result: Dict[str, Any], 
                             mismatch: Dict[str, Any]) -> str:
        """
        Generate a detailed description for the todo item.
        
        Args:
            validation_result: The validation result
            mismatch: The specific mismatch
            
        Returns:
            A detailed description
        """
        response_fragment = mismatch.get("response_fragment", "")
        reason = mismatch.get("reason", "No reason provided")
        
        # Get the SQL query and results
        sql_query = validation_result.get("sql_query", "")
        sql_results = validation_result.get("sql_results", [])
        
        # Get the response text
        response_text = validation_result.get("response_text", "")
        
        # Format the expected values
        expected_values = self._extract_expected_values(mismatch)
        expected_values_str = "\n".join([f"- {k}: {v}" for k, v in expected_values.items()])
        
        description = f"""
# Response Accuracy Issue

## Issue Details
The response contains information that does not match the SQL results.

### Response Fragment with Issue
```
{response_fragment}
```

### Reason for Mismatch
{reason}

### Expected Values from SQL Data
{expected_values_str}

## SQL Query
```sql
{sql_query}
```

## SQL Results (Sample)
```json
{json.dumps(sql_results[:2], indent=2) if sql_results else "No results"}
```

## Full Response Text
```
{response_text}
```

## Remediation Steps
1. Analyze the mismatch between the response and SQL results
2. Update the response generation logic to ensure data accuracy
3. Add specific checks for this type of data in the validation service
4. Verify the fix with the SQL validation service
"""
        
        return description
    
    def _extract_expected_values(self, mismatch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract expected values from the mismatch.
        
        Args:
            mismatch: The mismatch information
            
        Returns:
            Dictionary of expected values
        """
        expected_values = {}
        
        # If the mismatch has SQL data, extract values from it
        sql_data = mismatch.get("sql_data", {})
        if sql_data:
            column = sql_data.get("column", "")
            value = sql_data.get("value", "")
            if column and value is not None:
                expected_values[column] = value
        
        # If there are no extracted values, provide a placeholder
        if not expected_values:
            expected_values["unknown_field"] = "Could not determine expected value"
        
        return expected_values
    
    def _save_todo_items(self, todo_items: List[Dict[str, Any]], 
                        validation_result: Dict[str, Any]) -> None:
        """
        Save todo items to a file.
        
        Args:
            todo_items: List of todo items
            validation_result: The validation result
        """
        try:
            # Generate a filename based on the validation ID
            validation_id = validation_result.get("validation_id", str(uuid.uuid4()))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.todo_storage_path}/todo_{validation_id}_{timestamp}.json"
            
            # Write todo items to file
            with open(filename, 'w') as f:
                json.dump(todo_items, f, indent=2)
                
            logger.info(f"Saved {len(todo_items)} todo items to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving todo items: {e}")
    
    def get_all_open_todos(self) -> List[Dict[str, Any]]:
        """
        Get all open todo items.
        
        Returns:
            List of open todo items
        """
        todos = []
        
        try:
            # Iterate through all todo files
            for filename in os.listdir(self.todo_storage_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.todo_storage_path, filename)
                    with open(file_path, 'r') as f:
                        file_todos = json.load(f)
                        # Filter for open todos
                        open_todos = [todo for todo in file_todos if todo.get("status") == "OPEN"]
                        todos.extend(open_todos)
        except Exception as e:
            logger.error(f"Error loading todo items: {e}")
            
        return todos 