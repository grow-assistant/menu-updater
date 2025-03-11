"""
Response Service Prompt Builder

This module provides functionality for building prompts for the Response Service
using templates and context information.
"""

import os
from typing import Dict, Any, List, Optional

from services.utils.prompt_loader import PromptLoader, get_prompt_loader
from services.utils.logging import get_logger

logger = get_logger(__name__)

class ResponsePromptBuilder:
    """
    Builds prompts for the Response Service using templates.
    
    Note: This class expects the SQL query results to conform to the database schema defined in 
    resources/database_fields.md. In particular, any columns returned (e.g., for menu items from the
    "items" table, or order details from the "orders" table) should match the documented fields.
    """
    
    def __init__(self, config=None):
        """
        Initialize the Response Prompt Builder.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.prompt_loader = PromptLoader()
        logger.info("ResponsePromptBuilder initialized")
    
    def build_response_prompt(
        self, 
        query: str, 
        query_type: str,
        sql_result: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Build a prompt for generating a response based on query results.
        
        Args:
            query: The original user query
            query_type: Type of query (e.g., 'select', 'aggregate', etc.)
            sql_result: Result from SQL execution
            additional_context: Any additional context for response generation
            
        Returns:
            Dictionary with system and user prompt components
        """
        logger.info(f"Building response prompt for query type: {query_type}")
        
        additional_context = additional_context or {}
        
        # Get the appropriate system prompt for the query type
        system_prompt = self.prompt_loader.load_template("response_system")
        
        # Add formatting instructions based on query type
        result_format = self._get_result_format(query_type)
        additional_instructions = self._get_additional_instructions(query_type)
        
        system_prompt = system_prompt.format(
            result_format=result_format,
            additional_instructions=additional_instructions
        )
        
        # Format the user prompt with the query and results
        user_prompt = self._format_user_prompt(query, sql_result)
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _get_result_format(self, query_type: str) -> str:
        """
        Get the appropriate result format instructions based on query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            Formatting instructions string
        """
        format_instructions = {
            "select": "Format the response as a natural language summary of the query results.",
            "aggregate": "Include the aggregated values in your response and explain what they mean.",
            "error": "Explain the error in simple terms and suggest potential fixes."
        }
        
        return format_instructions.get(query_type, 
                                      "Format the response as a natural language answer to the query.")
    
    def _get_additional_instructions(self, query_type: str) -> str:
        """
        Get additional instructions based on query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            Additional instructions string
        """
        additional_instructions = {
            "select": "If the result set is empty, clearly state that no results were found.",
            "aggregate": "For aggregate queries, emphasize the significance of the calculated values.",
            "error": "For errors, be empathetic and constructive in your explanation."
        }
        
        return additional_instructions.get(query_type, "")
    
    def _format_user_prompt(self, query: str, sql_result: Dict[str, Any]) -> str:
        """
        Format the user prompt with query and results.
        
        Args:
            query: The original user query
            sql_result: Result from SQL execution
            
        Returns:
            Formatted user prompt string
        """
        success = sql_result.get("success", False)
        error_message = sql_result.get("error", "")
        
        prompt = f"User query: {query}\n\n"
        
        if success:
            # Format successful results
            columns = sql_result.get("columns", [])
            rows = sql_result.get("rows", [])
            affected_rows = sql_result.get("affected_rows", 0)
            
            if columns and rows:
                prompt += "Query results:\n"
                prompt += self._format_result_data(columns, rows)
            elif affected_rows is not None:
                prompt += f"Affected rows: {affected_rows}\n"
        else:
            # Format error results
            prompt += f"Query error: {error_message}\n"
        
        return prompt
    
    def _format_result_data(self, columns: List[str], rows: List[List[Any]]) -> str:
        """
        Format the result data as a readable string.
        
        Args:
            columns: List of column names
            rows: List of data rows
            
        Returns:
            Formatted data string
        """
        if not columns or not rows:
            return "No data available."
        
        result = ""
        max_rows_to_display = 10  # Limit number of rows in prompt
        
        # Format column headers
        result += " | ".join(columns) + "\n"
        result += "-" * (sum(len(col) for col in columns) + 3 * (len(columns) - 1)) + "\n"
        
        # Format data rows (limited)
        displayed_rows = rows[:max_rows_to_display]
        for row in displayed_rows:
            formatted_row = [str(cell) if cell is not None else "NULL" for cell in row]
            result += " | ".join(formatted_row) + "\n"
        
        # Add a note if not all rows are displayed
        if len(rows) > max_rows_to_display:
            result += f"... (showing {max_rows_to_display} of {len(rows)} rows)\n"
        
        return result


# Create a singleton instance
response_prompt_builder = ResponsePromptBuilder() 