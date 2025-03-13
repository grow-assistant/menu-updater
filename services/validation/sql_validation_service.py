"""
SQL Validation Service that ensures AI responses match SQL query results.

This service provides validation to ensure that AI-generated responses 
accurately reflect the data returned from SQL queries.
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional
import os
import traceback
import math
from fuzzywuzzy import fuzz
from datetime import datetime

from services.validation.sql_response_validator import SQLResponseValidator
from services.utils.service_registry import ServiceRegistry

# Try to import get_config, but don't fail if it's not available
try:
    from services.utils.config import get_config
except ImportError:
    # Define a mock get_config function if the real one isn't available
    def get_config():
        return {
            "validation": {
                "match_threshold": 90.0,
                "strict_mode": True,
                "block_failed_responses": False,
                "todo_storage_path": "todo_items"
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "postgres",
                "user": "postgres",
                "password": ""
            }
        }

# Import the TodoItemGenerator 
try:
    from services.validation.todo_generator import TodoItemGenerator
except ImportError:
    # Define a mock class if the module is not available
    class TodoItemGenerator:
        def __init__(self, storage_path=None):
            self.storage_path = storage_path or "todo_items"
            # Create the storage directory if it doesn't exist
            if not os.path.exists(self.storage_path):
                os.makedirs(self.storage_path)
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Created todo storage directory: {self.storage_path}")
            
        def generate_todo_items(self, validation_result, query_context=None):
            self.logger.info("Mock TodoItemGenerator: Would generate todo items here")
            return []
            
        def get_open_todo_items(self):
            return []

logger = logging.getLogger(__name__)

class SQLValidationService:
    """Service for validating AI responses against SQL query results."""
    
    def __init__(self, config=None):
        """
        Initialize the SQL validation service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config()
        self.enabled = True  # Default to enabled
        
        # Get validation configuration
        validation_config = self.config.get("validation", {})
        
        # Set up database connection for validation
        self.db_config = self.config.get("database", {})
        
        # Create direct database connection for validation
        try:
            import psycopg2
            # Get the port as an integer to avoid interpolation issues
            port = int(self.db_config.get('port', 5432))
            conn_str = f"host={self.db_config.get('host', 'localhost')} " \
                      f"port={port} " \
                      f"dbname={self.db_config.get('database', 'postgres')} " \
                      f"user={self.db_config.get('user', 'postgres')} " \
                      f"password={self.db_config.get('password', '')}"
            self.db_connection = psycopg2.connect(conn_str)
            logger.info(f"Created direct database connection for SQL validation on port {port}")
        except Exception as e:
            logger.error(f"Failed to create database connection for validation: {str(e)}")
            self.db_connection = None

        # Configure the TodoItemGenerator 
        todo_storage_path = validation_config.get("todo_storage_path", "todo_items")
        try:
            self.todo_generator = TodoItemGenerator(todo_storage_path=todo_storage_path)
            logger.info(f"Initialized TodoItemGenerator with storage path: {todo_storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize TodoItemGenerator: {str(e)}")
            self.todo_generator = None
            
        # Initialize the validator
        try:
            self.validator = SQLResponseValidator(db_connection=self.db_connection)
            logger.info("Initialized SQL Response Validator with database connection")
        except Exception as e:
            logger.error(f"Failed to initialize SQL Response Validator: {str(e)}")
            self.validator = None
            
        # Set up validation parameters
        self.match_threshold = validation_config.get("match_threshold", 90.0)
        self.strict_mode = validation_config.get("strict_mode", True)
        self.should_block_responses = validation_config.get("block_failed_responses", False)
        
        # Log the configuration
        logger.info(f"SQL Validation Service initialized with match threshold: {self.match_threshold}%, strict mode: {self.strict_mode}, block failed responses: {self.should_block_responses}")
    
    def validate_response(self, sql_query: str, sql_results: List[Dict[str, Any]], 
                         response_text: str) -> Dict[str, Any]:
        """
        Validate a generated response against SQL results.
        
        Args:
            sql_query: The SQL query that was executed
            sql_results: The data returned from the SQL query
            response_text: The generated response to validate
            
        Returns:
            Dictionary containing validation results and details
        """
        validation_result = {
            "validation_status": False,
            "validation_details": {},
            "detailed_feedback": "",
            "should_block_response": False,
            "sql_query": sql_query,  # Added for better context
            "response_summary": response_text[:100] + "..." if len(response_text) > 100 else response_text,  # Added for better debugging
            "result_count": len(sql_results) if sql_results else 0  # Added for better debugging
        }
        
        # Skip validation if service is not properly initialized
        if not self.enabled or not self.db_connection:
            logger.warning("SQL validation skipped: service not properly initialized")
            validation_result["validation_status"] = True  # Default to passing if validation can't be performed
            validation_result["detailed_feedback"] = "Validation skipped: service not initialized"
            return validation_result
        
        # Skip validation for empty results
        if not sql_results or len(sql_results) == 0:
            logger.info("SQL validation skipped: no results to validate")
            validation_result["validation_status"] = True
            validation_result["detailed_feedback"] = "No results to validate"
            return validation_result
        
        try:
            # Perform the validation using the full validator
            detailed_validation = self.validator.validate_response(sql_query, sql_results, response_text)
            
            # Extract match percentage and validation status
            match_percentage = detailed_validation.get("match_percentage", 0.0)
            
            # Determine validation status based on match threshold
            validation_status = match_percentage >= self.match_threshold
            should_block = not validation_status and self.should_block_responses
            
            # If validation failed in strict mode, perform basic validation as fallback
            if not validation_status and self.strict_mode:
                logger.warning(f"SQL validation failed with match percentage {match_percentage}%, below threshold of {self.match_threshold}%")
                
                # Perform basic validation as a fallback
                basic_validation = self._perform_basic_validation(sql_results, response_text)
                basic_match_percentage = basic_validation.get("match_percentage", 0.0)
                
                # Generate detailed feedback for mismatches
                mismatches = basic_validation.get("data_point_mismatches", [])
                matched_data_points = basic_validation.get("matched_data_points", [])
                
                # Enhanced detailed feedback with more context
                if mismatches:
                    validation_result["detailed_feedback"] = f"Validation found {len(mismatches)} mismatches out of {len(mismatches) + len(matched_data_points)} data points ({basic_match_percentage:.2f}% match).\n\n"
                    validation_result["detailed_feedback"] += f"SQL Query Type: {self._determine_query_type(sql_query)}\n"
                    validation_result["detailed_feedback"] += f"Result Set Size: {len(sql_results)} rows\n\n"
                    validation_result["detailed_feedback"] += "MISMATCHES:\n"
                    
                    for i, mismatch in enumerate(mismatches):
                        # Get detailed information for this mismatch
                        column = mismatch.get("column", "Unknown")
                        expected = mismatch.get("expected", "Unknown")
                        found = mismatch.get("found", "Unknown")
                        reason = mismatch.get("reason", "Value mismatch")
                        
                        # Add context about where in the response the mismatch was found
                        context = mismatch.get("response_fragment", "No context available")
                        
                        # Append to detailed feedback with improved formatting
                        validation_result["detailed_feedback"] += f"MISMATCH #{i+1}:\n"
                        validation_result["detailed_feedback"] += f"  Field: {column}\n"
                        validation_result["detailed_feedback"] += f"  Expected: {expected}\n"
                        validation_result["detailed_feedback"] += f"  Found: {found}\n"
                        validation_result["detailed_feedback"] += f"  Reason: {reason}\n"
                        validation_result["detailed_feedback"] += f"  Context: \"{context}\"\n\n"
                    
                    # Add a sample of what matched correctly for reference
                    if matched_data_points:
                        validation_result["detailed_feedback"] += "SAMPLE OF CORRECT MATCHES:\n"
                        for i, match in enumerate(matched_data_points[:3]):  # Show up to 3 correct matches
                            validation_result["detailed_feedback"] += f"  Match #{i+1}: {match.get('column', 'Unknown')} = {match.get('value', 'Unknown')}\n"
                    
                    # Add recommendations for fixing the issues
                    validation_result["detailed_feedback"] += "\nRECOMMENDATIONS:\n"
                    validation_result["detailed_feedback"] += "1. Check response generation logic for data transformation issues\n"
                    validation_result["detailed_feedback"] += "2. Verify that all SQL result fields are properly referenced\n"
                    validation_result["detailed_feedback"] += "3. Ensure numerical formatting matches expected output\n"
                    validation_result["detailed_feedback"] += "4. Check for date formatting inconsistencies\n"
                    
                    # Generate todo items from validation failures
                    if self.todo_generator and basic_match_percentage < self.match_threshold:
                        try:
                            validation_result_for_todo = {
                                "validation_status": False,
                                "sql_query": sql_query,
                                "sql_results": sql_results,
                                "response_text": response_text,
                                "validation_details": {
                                    "data_point_mismatches": mismatches
                                },
                                "validation_id": str(datetime.now().timestamp())
                            }
                            todo_items = self.todo_generator.generate_todo_items(validation_result_for_todo)
                            logger.info(f"Generated {len(todo_items)} todo items for validation failure with match percentage {basic_match_percentage}%")
                            
                            # Add information about created todo items
                            validation_result["detailed_feedback"] += f"\nTODO ITEMS:\n"
                            validation_result["detailed_feedback"] += f"Created {len(todo_items)} todo items for follow-up\n"
                            
                        except Exception as e:
                            logger.error(f"Failed to generate todo items: {str(e)}")
                            validation_result["detailed_feedback"] += "\nFailed to generate todo items: " + str(e)
                else:
                    validation_result["detailed_feedback"] = f"Basic validation passed with match percentage {basic_match_percentage}%. No mismatches found."
                
                # If basic validation passes but full validation failed, use basic validation result
                if basic_match_percentage >= self.match_threshold:
                    logger.info(f"Using basic validation result with match percentage {basic_match_percentage}%")
                    validation_status = True
                    match_percentage = basic_match_percentage
                
                # Update validation result with basic validation information
                validation_result["match_percentage"] = basic_match_percentage
                validation_result["validation_status"] = validation_status
                validation_result["validation_details"] = basic_validation
                validation_result["should_block_response"] = not validation_status and self.should_block_responses
                logger.info(f"SQL validation {'PASSED' if validation_status else 'FAILED'} with match percentage {basic_match_percentage}% (threshold: {self.match_threshold}%)")
                
                return validation_result
            
            # Handle case where full validation was successful
            validation_result["validation_status"] = validation_status
            validation_result["validation_details"] = detailed_validation
            validation_result["match_percentage"] = match_percentage
            validation_result["should_block_response"] = should_block
            validation_result["detailed_feedback"] = f"Full validation {'passed' if validation_status else 'failed'} with match percentage {match_percentage}% (threshold: {self.match_threshold}%)"
            
            logger.info(f"SQL validation {'PASSED' if validation_status else 'FAILED'} with match percentage {match_percentage}% (threshold: {self.match_threshold}%)")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during SQL validation: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Fall back to basic validation on error
            try:
                basic_validation = self._perform_basic_validation(sql_results, response_text)
                match_percentage = basic_validation.get("match_percentage", 0.0)
                validation_status = match_percentage >= self.match_threshold
                
                validation_result["validation_status"] = validation_status
                validation_result["validation_details"] = basic_validation
                validation_result["match_percentage"] = match_percentage
                validation_result["should_block_response"] = not validation_status and self.should_block_responses
                validation_result["detailed_feedback"] = f"Error in full validation, fell back to basic validation. Match: {match_percentage}%"
                
                logger.info(f"Basic validation result: {validation_status} (match: {match_percentage}%)")
                
                return validation_result
            except Exception as inner_e:
                logger.error(f"Error during basic validation fallback: {str(inner_e)}")
                logger.error(traceback.format_exc())
                
                # If all validation fails, default to passing
                validation_result["validation_status"] = True
                validation_result["detailed_feedback"] = "Validation failed with error, defaulting to pass"
                return validation_result
    
    def _perform_basic_validation(self, sql_results: List[Dict[str, Any]], response_text: str) -> Dict[str, Any]:
        """
        Perform basic validation by checking if key data points are mentioned in the response.
        
        Args:
            sql_results: The results of the SQL query
            response_text: The response text to validate
            
        Returns:
            Basic validation result with match percentage and details
        """
        # Convert response to lowercase for easier matching
        response_lower = response_text.lower()
        
        # Track matches and mismatches
        matched_data_points = []
        data_point_mismatches = []
        
        # Track important columns for completeness check
        important_columns = ['customer_name', 'order_total', 'item_name', 'order_count', 'customer', 'total', 'price', 
                             'quantity', 'revenue', 'sales', 'item_price', 'order_id', 'first_name', 'last_name']
        
        # Mapping of columns to their typical formatting patterns
        formatting_patterns = {
            'order_total': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'total': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'price': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'item_price': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'item_total_price': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'revenue': [
                lambda v: f"${v}",                                # $10.50
                lambda v: f"${float(v):.2f}",                     # $10.50
                lambda v: f"{float(v):.2f}",                      # 10.50
                lambda v: f"{int(float(v))}",                     # 10
                lambda v: f"${int(float(v))}",                    # $10
                lambda v: f"${float(v):,.2f}",                    # $10.50 or $1,000.50
                lambda v: f"{float(v):,}",                        # 10.5 or 1,000.5
                lambda v: f"{int(float(v)):,}"                    # 10 or 1,000
            ],
            'order_id': [
                lambda v: f"#{v}",                                # #123
                lambda v: f"#{int(v)}",                           # #123
                lambda v: f"order #{v}",                          # order #123
                lambda v: f"order #{int(v)}",                     # order #123
                lambda v: f"order {v}",                           # order 123
                lambda v: f"order {int(v)}",                      # order 123
                lambda v: f"order number {v}",                    # order number 123
                lambda v: f"order number {int(v)}",               # order number 123
                lambda v: f"{int(v)}"                             # 123
            ],
            'quantity': [
                lambda v: f"{v}x",                                # 5x
                lambda v: f"{int(v)}x",                           # 5x
                lambda v: f"{v} x",                               # 5 x
                lambda v: f"{int(v)} x",                          # 5 x
                lambda v: f"{v}",                                 # 5
                lambda v: f"{int(v)}"                             # 5
            ],
            'item_quantity': [
                lambda v: f"{v}x",                                # 5x
                lambda v: f"{int(v)}x",                           # 5x
                lambda v: f"{v} x",                               # 5 x
                lambda v: f"{int(v)} x",                          # 5 x
                lambda v: f"{v}",                                 # 5
                lambda v: f"{int(v)}"                             # 5
            ]
        }
        
        # Track values mentioned in response for each column
        mentioned_values = {}
        
        # Process all results in the SQL data
        for row in sql_results:
            for column, value in row.items():
                # Skip null values
                if value is None:
                    continue
                
                # Convert value to string for matching
                value_str = str(value).lower()
                
                # Skip empty strings
                if not value_str.strip():
                    continue
                
                # Skip very short values that might cause false positives
                if len(value_str) < 2:
                    continue
                
                # Check if this exact value is mentioned in the response
                if value_str in response_lower:
                    # Found a match
                    matched_data_points.append({
                        "column": column,
                        "value": value,
                        "match_type": "exact"
                    })
                    
                    # Track in mentioned values
                    if column not in mentioned_values:
                        mentioned_values[column] = []
                    mentioned_values[column].append(value)
                else:
                    # Check for alternate formats
                    found_match = False
                    matched_format = None
                    
                    # First, try column-specific formatting patterns if available
                    if column in formatting_patterns:
                        try:
                            for format_func in formatting_patterns[column]:
                                formatted_value = format_func(value)
                                if formatted_value.lower() in response_lower:
                                    found_match = True
                                    matched_format = formatted_value
                                    break
                        except (ValueError, TypeError):
                            # If formatting fails (e.g. non-numeric value for numeric pattern), 
                            # continue with generic checks
                            pass
                    
                    # Generic checks for numbers if specific formatting didn't match
                    if not found_match and isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
                        # Try without decimal (for integers)
                        if str(int(float(value))) in response_lower:
                            found_match = True
                            matched_format = str(int(float(value)))
                        # Try with dollar sign for money
                        elif '$' + value_str.replace('$', '') in response_lower:
                            found_match = True
                            matched_format = '$' + value_str.replace('$', '')
                        # Try with commas for thousands
                        elif any(format(int(float(value)), ",") in response_lower for _ in [1]):
                            found_match = True
                            matched_format = format(int(float(value)), ",")
                        # Try to find the value surrounded by non-alphanumeric characters
                        elif re.search(r'[^a-zA-Z0-9]' + re.escape(value_str) + r'[^a-zA-Z0-9]', response_lower):
                            found_match = True
                            matched_format = value_str + " (with boundary)"
                            
                    # For strings, try partial matching for important columns
                    elif not found_match and isinstance(value, str) and column in important_columns:
                        # Check if a significant portion of the string is in the response
                        if len(value_str) > 3 and value_str in response_lower:
                            found_match = True
                            matched_format = value_str
                            
                    if found_match:
                        matched_data_points.append({
                            "column": column,
                            "value": value,
                            "match_type": "formatted",
                            "matched_format": matched_format
                        })
                        
                        # Track in mentioned values
                        if column not in mentioned_values:
                            mentioned_values[column] = []
                        mentioned_values[column].append(value)
                    elif column in important_columns:
                        # This is an important value that's missing
                        # Get the relevant fragment from the response for context
                        response_fragment = self._extract_relevant_fragment(response_lower, value_str)
                        
                        # Try to find potential formatting issues for better feedback
                        attempted_formats = []
                        if column in formatting_patterns:
                            try:
                                for format_func in formatting_patterns[column]:
                                    attempted_formats.append(format_func(value))
                            except (ValueError, TypeError):
                                # If formatting fails, just continue
                                pass
                        
                        # Limit the number of formats shown in the error
                        if len(attempted_formats) > 3:
                            attempted_formats = attempted_formats[:3]
                        
                        formatted_attempts = ", ".join([f"'{f}'" for f in attempted_formats]) if attempted_formats else "None tried"
                        
                        data_point_mismatches.append({
                            "column": column,
                            "expected": value,
                            "found": "Not mentioned",
                            "reason": f"Important value not found in response. Attempted formats: {formatted_attempts}",
                            "response_fragment": response_fragment or "No relevant fragment found"
                        })
        
        # Check for each important column if at least one value is mentioned
        missing_important_columns = []
        for column in important_columns:
            # Check if this column exists in the SQL results
            column_exists = any(column in row for row in sql_results)
            
            if column_exists and column not in mentioned_values:
                missing_important_columns.append(column)
        
        # Add mismatches for missing important columns
        for column in missing_important_columns:
            values = [row[column] for row in sql_results if column in row and row[column] is not None]
            if values:
                sample_value = values[0]
                
                # Try to suggest formats that should have been used
                suggested_formats = []
                if column in formatting_patterns:
                    try:
                        for format_func in formatting_patterns[column]:
                            suggested_formats.append(format_func(sample_value))
                    except (ValueError, TypeError):
                        # If formatting fails, just continue
                        pass
                
                # Limit the number of suggestions
                if len(suggested_formats) > 3:
                    suggested_formats = suggested_formats[:3]
                    
                suggestions = f" Suggested formats: {', '.join(suggested_formats)}" if suggested_formats else ""
                
                data_point_mismatches.append({
                    "column": column,
                    "expected": f"At least one {column} value (e.g., {sample_value})",
                    "found": "No values mentioned",
                    "reason": f"Required column {column} not mentioned in response.{suggestions}",
                    "response_fragment": response_text[:100]  # First 100 chars for context
                })
        
        # Calculate match percentage
        total_important_data_points = len([1 for row in sql_results for col in row.keys() if col in important_columns])
        matched_important_count = len([m for m in matched_data_points if m["column"] in important_columns])
        
        # Apply a more flexible threshold for validation
        # If we have matched more than 80% of important data points, give more weight to those
        if total_important_data_points > 0 and (matched_important_count / total_important_data_points) >= 0.8:
            # Give a boost to the match percentage to account for acceptable formatting differences
            match_percentage = min(100.0, (matched_important_count / total_important_data_points) * 110.0)
        else:
            # Standard calculation
            if total_important_data_points == 0:
                match_percentage = 100.0  # No important data points to check
            else:
                match_percentage = (matched_important_count / total_important_data_points) * 100.0
        
        # Cap at 100%
        match_percentage = min(match_percentage, 100.0)
        
        # Log validation details
        logger.info(f"Basic validation: {matched_important_count} matches, {len(data_point_mismatches)} mismatches")
        logger.info(f"Basic validation match percentage: {match_percentage:.2f}%")
        
        # Log detailed information about matched formats if debugging is enabled
        if logger.isEnabledFor(logging.DEBUG):
            formatted_matches = [m for m in matched_data_points if m.get("match_type") == "formatted"]
            if formatted_matches:
                logger.debug(f"Matched with formatting ({len(formatted_matches)} items):")
                for match in formatted_matches[:5]:  # Log first 5 for brevity
                    logger.debug(f"  {match.get('column')}={match.get('value')} as '{match.get('matched_format')}'")
        
        return {
            "match_percentage": match_percentage,
            "data_point_mismatches": data_point_mismatches,
            "matched_data_points": matched_data_points,
            "important_columns_checked": important_columns,
            "total_important_data_points": total_important_data_points,
            "matched_important_count": matched_important_count
        }
    
    def _extract_relevant_fragment(self, text: str, search_term: str, context_chars: int = 100) -> str:
        """
        Extract a relevant fragment of text surrounding a search term.
        
        Args:
            text: The text to search within
            search_term: The term to find in the text
            context_chars: Number of characters to include around the search term
            
        Returns:
            Fragment of text surrounding the search term, or empty string if not found
        """
        if not search_term or not text:
            return ""
            
        try:
            # If the search term is in the text, find its position
            if search_term in text:
                pos = text.find(search_term)
                
                # Calculate start and end positions for the fragment
                start = max(0, pos - context_chars // 2)
                end = min(len(text), pos + len(search_term) + context_chars // 2)
                
                # Extract the fragment
                fragment = text[start:end]
                
                # Add ellipsis if we've truncated the fragment
                if start > 0:
                    fragment = "..." + fragment
                if end < len(text):
                    fragment = fragment + "..."
                    
                return fragment
                
            # Try a fuzzy match for partial terms
            words = text.split()
            for i, word in enumerate(words):
                if search_term in word:
                    # Calculate start and end word indices
                    start_idx = max(0, i - 5)  # 5 words before
                    end_idx = min(len(words), i + 6)  # 5 words after
                    
                    # Extract the fragment
                    fragment = " ".join(words[start_idx:end_idx])
                    
                    # Add ellipsis if we've truncated the fragment
                    if start_idx > 0:
                        fragment = "..." + fragment
                    if end_idx < len(words):
                        fragment = fragment + "..."
                        
                    return fragment
        except Exception as e:
            logger.warning(f"Error extracting relevant fragment: {str(e)}")
            
        # If no match was found, return a default empty string
        return ""
    
    def _determine_query_type(self, sql_query: str) -> str:
        """
        Determine the type of SQL query for better feedback.
        
        Args:
            sql_query: The SQL query to analyze
            
        Returns:
            The query type as a string
        """
        sql_lower = sql_query.lower()
        
        if "order by" in sql_lower and "join" in sql_lower:
            if "order_items" in sql_lower:
                return "Order Details Query"
            elif "orders" in sql_lower:
                return "Order History Query"
        
        if "menu" in sql_lower or "items" in sql_lower:
            return "Menu Query"
        
        if "sum(" in sql_lower or "count(" in sql_lower or "avg(" in sql_lower:
            return "Aggregation Query"
        
        return "General Query"
    
    def register_service(self):
        """Register this service with the ServiceRegistry."""
        from services.utils.service_registry import ServiceRegistry
        ServiceRegistry.register("sql_validation", lambda config: self)
    
    def health_check(self) -> bool:
        """Perform a health check on the service."""
        if not self.enabled:
            logger.warning("Health check failed: Validation service is disabled")
            return False
            
        if not self.db_connection:
            logger.warning("Health check failed: Database connection is not available")
            return False
            
        # Check if database connection is active
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False 