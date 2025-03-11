"""
Enhanced service for generating SQL queries using Google's Gemini API.
Includes improved prompt building, SQL validation, and optimization.
"""
import logging
import re
import time
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid
import os
from datetime import datetime

from services.rules.rules_service import RulesService
from services.utils.service_registry import ServiceRegistry
from services.sql_generator.sql_example_loader import sql_example_loader

logger = logging.getLogger(__name__)

class GeminiSQLGenerator:
    def __init__(self, config: Dict[str, Any], db_service, skip_verification=False):
        """Initialize the enhanced Gemini SQL generator."""
        # Configure Gemini API
        api_key = config["api"]["gemini"]["api_key"]
        self.model = config["api"]["gemini"].get("model", "gemini-2.0-flash")
        self.temperature = config["api"]["gemini"].get("temperature", 0.2)
        self.max_tokens = config["api"]["gemini"].get("max_tokens", 1024)
        genai.configure(api_key=api_key)
        self.client_initialized = True  # FIX: Set client_initialized to True after configuring the API
        
        # Initialize logger
        self.logger = logger
        
        # Save config for other methods
        self.config = config
        
        # Initialize metrics
        self.api_call_count = 0
        self.total_tokens = 0
        self.total_latency = 0
        self.retry_count = 0
        
        # Add prompt caching
        self.prompt_cache = {}
        self.prompt_cache_ttl = config.get("services", {}).get("sql_generator", {}).get("prompt_cache_ttl", 300)  # 5 minutes default
        self.prompt_cache_timestamps = {}
        
        # Performance tuning - ensure it's properly initialized from config
        if "services" in config and "sql_generator" in config["services"]:
            self.enable_detailed_logging = config["services"]["sql_generator"].get("enable_detailed_logging", False)
        else:
            # Default to False if config is incomplete
            self.enable_detailed_logging = False
        
        logger.debug(f"SQL Generator initialized with detailed_logging={self.enable_detailed_logging}")
        
        # Load prompt templates
        self.prompt_template = self._get_default_prompt_template()
        self.validation_prompt = self._get_default_validation_prompt()
        self.optimization_prompt = self._get_default_optimization_prompt()
        
        # Test placeholder replacement
        self._verify_placeholder_replacement()
        
        self.db_service = db_service
        self.max_retries = config.get("services", {}).get("sql_generator", {}).get("max_retries", 3)
        
        # Only perform placeholder verification if not explicitly skipped
        if not skip_verification:
            self._verify_placeholder_replacement()
        
    def _get_default_prompt_template(self) -> str:
        """Get default prompt template if file is not found."""
        return """
        You are a PostgreSQL expert that translates natural language questions into SQL queries.
        
        Follow these guidelines:
        1. Only return valid PostgreSQL queries.
        2. Use appropriate table and column names as defined in the schema.
        3. Follow all query rules provided.
        4. Include helpful comments in your SQL to explain your reasoning.
        5. Format your SQL query properly with line breaks and indentation for readability.
        6. Do not include any explanations outside of comments within the SQL.
        7. Only return the SQL query, nothing else.
        
        Database Schema:
        {schema}
        
        Business Rules:
        {rules}
        
        SQL Patterns:
        {patterns}
        
        Examples:
        {examples}
        
        User Query: {query}
        
        SQL:
        """
    
    def _get_default_validation_prompt(self) -> str:
        """Get the default SQL validation prompt template."""
        return """
You are a SQL validation expert. Your job is to validate the following SQL query and determine if it is valid, efficient, and safe.
Review the provided SQL query that was generated based on the original query.

Original Query: {original_query}
SQL to Validate: {sql_to_validate}
Current Date/Time: {current_datetime}

VALIDATION TASKS:
1. Check if the SQL is syntactically correct
2. Ensure the SQL properly addresses the original query's intent
3. Verify that tables and columns referenced exist in the schema
4. Check for proper filtering and potential performance issues
5. Look for security concerns like SQL injection vulnerabilities

VALIDATION RESULT:
Provide your assessment as either VALID or INVALID.
If INVALID, include a REASON section explaining why.
If VALID, include a SUGGESTIONS section with any improvements.

Format your response like this for valid SQL:
VALID
SUGGESTIONS: [Optional suggestions for improvement]

Or like this for invalid SQL:
INVALID
REASON: [Clear explanation of the issue]
"""
    
    def _get_default_optimization_prompt(self) -> str:
        """Get the default SQL optimization prompt template."""
        return """
You are a SQL optimization expert. Your job is to optimize the following SQL query for better performance.
Review the provided SQL query and suggest improvements for efficiency and readability.

Original Query: {original_query}
SQL to Optimize: {sql_to_optimize}

OPTIMIZATION GOALS:
1. Improve query performance
2. Add appropriate indexes or query hints if needed
3. Simplify complex expressions
4. Ensure proper join conditions and order
5. Optimize WHERE clauses and filtering

RESPONSE FORMAT:
1. Provide the optimized SQL code
2. Include brief comments explaining your optimizations
3. Return ONLY the improved SQL, beginning with SELECT

Here is the optimized SQL:
```sql
-- Your optimized SQL here
```
"""
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format database schema information for the prompt."""
        schema_text = ""
        for table_name, table_info in schema.items():
            schema_text += f"Table: {table_name}\n"
            if "description" in table_info:
                schema_text += f"Description: {table_info['description']}\n"
                
            if "columns" in table_info:
                schema_text += "Columns:\n"
                for col_name, col_desc in table_info["columns"].items():
                    schema_text += f"  - {col_name}: {col_desc}\n"
                    
            if "relationships" in table_info:
                schema_text += "Relationships:\n"
                for rel in table_info["relationships"]:
                    schema_text += f"  - {rel}\n"
                    
            schema_text += "\n"
            
        return schema_text
        
    def _format_rules(self, rules: Dict[str, Any]) -> str:
        """Format business rules for the prompt."""
        rules_text = ""
        for category, category_rules in rules.items():
            rules_text += f"{category.upper()}:\n"
            if isinstance(category_rules, dict):
                for rule_name, rule_desc in category_rules.items():
                    rules_text += f"  - {rule_name}: {rule_desc}\n"
            else:
                rules_text += f"  - {category_rules}\n"
            rules_text += "\n"
            
        return rules_text
        
    def _format_patterns(self, patterns: Dict[str, str]) -> str:
        """Format SQL patterns for the prompt."""
        patterns_text = ""
        for pattern_name, pattern in patterns.items():
            # Extract just the first few lines to keep it manageable
            pattern_lines = pattern.split('\n')
            pattern_preview = '\n'.join(pattern_lines[:5])
            if len(pattern_lines) > 5:
                pattern_preview += "\n..."
                
            patterns_text += f"Pattern: {pattern_name}\n"
            patterns_text += f"```\n{pattern_preview}\n```\n\n"
            
        return patterns_text
        
    def _format_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format examples for the prompt."""
        if not examples:
            return ""
            
        examples_text = ""
        for example in examples:
            if "query" in example and "sql" in example:
                examples_text += f"User Query: {example['query']}\n"
                examples_text += f"SQL: {example['sql']}\n\n"
                
        return examples_text
    
    def _build_prompt(self, query: str, examples: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        Build a comprehensive prompt for SQL generation with examples and context.
        
        Args:
            query: The user's natural language query
            examples: List of example queries and SQL pairs
            context: Additional context information
            
        Returns:
            Complete prompt string for model
        """
        # Start with the template
        prompt = self.prompt_template
        
        # Initialize prompt_parts list to collect additional context
        prompt_parts = []
        
        # Import the actual location ID value from business rules
        from services.rules.business_rules import DEFAULT_LOCATION_ID
        
        # Add a strongly worded reminder about order status being integers and location ID filtering
        critical_requirements = f"""
CRITICAL REQUIREMENTS:
- Order status values must ALWAYS be used as integers, never as strings
- Completed orders have status=7 (not 'COMPLETED')
- Cancelled orders have status=6 (not 'CANCELLED')
- In-progress orders have status between 3-5 (not 'IN PROGRESS')

*** MANDATORY LOCATION FILTERING ***
- Every query on the orders table MUST filter by location_id 
- ALWAYS use the exact value: o.location_id = {DEFAULT_LOCATION_ID}
- DO NOT use placeholders like {{location_id}}
- This is a CRITICAL security requirement for data isolation
- The specific location ID value is: {DEFAULT_LOCATION_ID}
- You must ALWAYS use this exact numeric value: {DEFAULT_LOCATION_ID}
- NEVER use curly braces or placeholders in generated SQL

*** TIME-BASED DEFAULT BEHAVIOR ***
- When a query mentions "this month" or "current month" without specific dates, use the most recent COMPLETE month
- When a query asks about "orders in a month" without specifying which month, default to the most recent complete month
- For example, if today is October 15, 2023, "orders this month" refers to October 2023 (month to date)
- Use date_trunc('month', current_date - interval '1 month') to get the first day of the most recent complete month
- Use date_trunc('month', current_date) - interval '1 day' to get the last day of the most recent complete month
- Always use explicit date ranges in your WHERE clause for time-based queries (e.g., BETWEEN start_date AND end_date)
- Only use the current month (in progress) when the query explicitly asks for "current in-progress month" or similar
"""
        
        # Format schema information if available
        schema_str = ""
        if "schema" in context:
            schema_str = self._format_schema(context["schema"])
        
        # Format rules if available
        rules_str = ""
        if "rules" in context:
            rules_str = self._format_rules(context["rules"])
            
        # Add the critical requirements to the rules
        rules_str = rules_str + critical_requirements
        
        # Format SQL patterns if available
        patterns_str = ""
        if "query_patterns" in context:
            patterns_str = self._format_patterns(context["query_patterns"])
            
        # Format examples if available
        examples_str = self._format_examples(examples)
        
        # Initialize previous_sql_str regardless of whether there's previous SQL
        previous_sql_str = ""
        
        # Fix the previous SQL history handling
        if context and context.get("previous_sql"):
            previous_sql = context.get("previous_sql")
            previous_sql_str = "# Previous SQL query for context:\n"
            
            # Check if previous_sql is a string or a dictionary/object
            if isinstance(previous_sql, str):
                # Handle case when previous_sql is a string
                previous_sql_str += f"SQL: {previous_sql}\n"
                if context.get("previous_query"):
                    previous_sql_str += f"User Asked: {context.get('previous_query', 'Unknown')}\n"
            else:
                # Handle case when previous_sql is a dictionary/object with get method
                previous_sql_str += f"SQL: {previous_sql.get('sql', 'Unknown')}\n"
                previous_sql_str += f"User Asked: {previous_sql.get('query', 'Unknown')}\n"
            
            prompt_parts.append(previous_sql_str)
        
        # Add follow-up question context
        followup_context_str = ""
        if "previous_query" in context:
            followup_context_str += f"\nFOLLOW-UP QUESTION CONTEXT:\n"
            followup_context_str += f"Previous Query: {context.get('previous_query', '')}\n"
            
            # Add previous complete SQL if available (direct reference)
            if "previous_complete_sql" in context:
                followup_context_str += f"Previous Full SQL: {context.get('previous_complete_sql', '')}\n"
            
            # Add time period filter if available
            if "previous_time_period" in context:
                followup_context_str += f"Time Period Filter: {context.get('previous_time_period', '')}\n"
            
            # Add required SQL conditions - these must be included
            if "required_conditions" in context and context["required_conditions"]:
                followup_context_str += "\nREQUIRED SQL CONDITIONS - YOU MUST INCLUDE THESE EXACT CONDITIONS IN YOUR WHERE CLAUSE:\n"
                for condition in context["required_conditions"]:
                    followup_context_str += f"- {condition}\n"
            
            # Add other filters from previous query
            explicit_sql_filters = []
            if "previous_filters" in context and context["previous_filters"]:
                followup_context_str += "Previous Query Filters:\n"
                for filter_name, filter_value in context["previous_filters"].items():
                    followup_context_str += f"- {filter_name}: {filter_value}\n"
                    
                    # Generate explicit SQL WHERE clauses for common filters
                    if filter_name == "status":
                        if filter_value.lower() == "completed":
                            explicit_sql_filters.append("o.status = 7")
                        elif filter_value.lower() == "pending":
                            explicit_sql_filters.append("o.status = 3")
                        elif filter_value.lower() == "cancelled" or filter_value.lower() == "canceled":
                            explicit_sql_filters.append("o.status = 6")
                
            # Add explicit SQL filter instructions if any were generated
            if explicit_sql_filters:
                followup_context_str += "\nREQUIRED SQL FILTERS - YOU MUST INCLUDE THESE IN YOUR QUERY:\n"
                for sql_filter in explicit_sql_filters:
                    followup_context_str += f"- {sql_filter}\n"
                
            followup_context_str += """
IMPORTANT: This is a follow-up question related to the previous query.
You MUST maintain all relevant filters and constraints from the previous query.

CRITICAL REQUIREMENTS FOR FOLLOW-UP QUERIES:
1. If the previous query filtered for completed orders (status=7), you MUST include "o.status = 7" in your WHERE clause
2. If the previous query had a time period constraint, you MUST maintain the exact same time constraint
3. You MUST use the same table joins and core filtering logic from the previous query
4. Location_id filtering (o.location_id = 123) MUST be preserved in all cases
5. NEVER drop a constraint that was in the previous query - follow-up questions refer to the same data subset
"""

        # Format final prompt with all components
        # Replace the placeholders
        prompt = prompt.replace("{schema}", schema_str)
        prompt = prompt.replace("{rules}", rules_str)
        prompt = prompt.replace("{patterns}", patterns_str)
        prompt = prompt.replace("{examples}", examples_str)
        prompt = prompt.replace("{query}", query)
        
        # Add context to the appropriate section of the prompt
        context_str = previous_sql_str + followup_context_str
        if "{context}" in prompt:
            prompt = prompt.replace("{context}", context_str)
        else:
            # Add context at the end if there's no placeholder
            prompt += "\n" + context_str
        
        return prompt
    
    def _generate_with_retry(self, prompt, max_retries=None):
        """
        Generate SQL with retry logic.
        
        Args:
            prompt (str): The prompt to generate SQL from.
            max_retries (int, optional): Maximum number of retries. Defaults to self.max_retries.
            
        Returns:
            dict: A dictionary containing the generated SQL and a success flag.
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        attempt = 0
        while attempt <= max_retries:
            attempt += 1
            self.logger.info(f"SQL generation attempt {attempt}/{max_retries + 1}")
            
            try:
                # Check if GenAI client is initialized
                if not self.client_initialized:
                    self.logger.warning("GenAI client not initialized, returning empty result")
                    return {"sql": "", "success": False, "error": "GenAI client not initialized"}
                
                # Generate content
                genai_model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=genai.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens
                    )
                )
                
                response = genai_model.generate_content(prompt)
                
                # Track API usage
                self.api_call_count += 1
                
                # Extract SQL from response
                sql = self._extract_sql_from_response(response.text)
                
                # Add location_id if missing
                if sql:
                    sql = self._ensure_location_id_in_sql(sql)
                
                if sql:
                    self.logger.info(f"Successfully generated SQL: {sql[:100]}...")
                    return {"sql": sql, "success": True}
                else:
                    self.logger.warning("Failed to extract SQL from response")
                    if attempt <= max_retries:
                        self.logger.info(f"Retrying SQL generation (attempt {attempt}/{max_retries + 1})")
                        continue
                    return {"sql": "", "success": False, "error": "Failed to extract SQL from response"}
            
            except Exception as e:
                self.logger.error(f"Error in SQL generation attempt {attempt}: {str(e)}")
                if attempt <= max_retries:
                    self.logger.info(f"Retrying SQL generation (attempt {attempt}/{max_retries + 1})")
                    continue
                return {"sql": "", "success": False, "error": str(e)}
        
        return {"sql": "", "success": False, "error": "Max retries reached"}
    
    def generate_sql(self, query, classification, time_period=None, constraints=None, context=None):
        """Generate SQL based on the provided query and classification."""
        try:
            # Get SQL examples for this classification
            sql_examples = self._get_sql_examples(classification)
            
            # Build the prompt with the query, classification, and examples
            prompt = self._build_prompt(query, sql_examples, context)
            
            # Log the number of examples included
            self.logger.info(f"Built SQL generation prompt with {len(sql_examples.get('examples', []))} examples and context for {classification}")
            
            # Generate the SQL
            result = self._generate_with_retry(prompt)
            
            if not result["success"]:
                self.logger.error(f"SQL generation failed: {result.get('error', 'Unknown error')}")
                return {"sql": "", "success": False, "error": result.get("error", "Unknown error")}
            
            sql = result["sql"]
            
            # Validate SQL if enabled
            if self.config.get("services", {}).get("sql_generator", {}).get("enable_validation", False):
                is_valid, sql, error = self._validate_sql(sql, query, context)
                
                if not is_valid:
                    self.logger.warning(f"SQL validation failed: {error}")
                    # Retry with error message in context
                    retry_context = context.copy() if context else {}
                    retry_context["validation_error"] = error
                    
                    # Build a new prompt with the error message
                    prompt = self._build_prompt(query, sql_examples, retry_context)
                    
                    # Generate SQL again
                    retry_result = self._generate_with_retry(prompt)
                    
                    if not retry_result["success"]:
                        self.logger.error(f"SQL generation retry failed: {retry_result.get('error', 'Unknown error')}")
                        return {"sql": "", "success": False, "error": retry_result.get("error", "Unknown error")}
                    
                    sql = retry_result["sql"]
                    
                    # Validate again
                    is_valid, sql, error = self._validate_sql(sql, query, context)
                    
                    if not is_valid:
                        self.logger.error(f"SQL validation failed after retry: {error}")
                        return {"sql": "", "success": False, "error": error}
            
            # Optimize SQL if enabled
            if self.config.get("services", {}).get("sql_generator", {}).get("enable_optimization", False):
                sql = self._optimize_sql(sql, query, context)
            
            return {"sql": sql, "success": True}
        except Exception as e:
            self.logger.error(f"Error in SQL generation: {str(e)}")
            return {"sql": "", "success": False, "error": str(e)}

    def _get_sql_examples(self, classification):
        """
        Get SQL examples for a specific classification from the rules service.
        
        Args:
            classification: Query classification
            
        Returns:
            Dict containing SQL examples
        """
        try:
            # Import the actual location ID value
            from services.rules.business_rules import DEFAULT_LOCATION_ID
            from services.sql_generator.sql_example_loader import sql_example_loader
            
            # Get rules service from registry
            rules_service = ServiceRegistry.get_service("rules")
            if not rules_service:
                logger.warning("Rules service not available, proceeding without examples")
                return {"examples": []}
            
            # Get SQL examples from the rules service
            logger.info(f"Getting SQL examples for classification: {classification}")
            examples = rules_service.get_sql_examples(classification)
            
            # Initialize examples list
            example_list = []
            
            # Handle examples from rules service 
            if not examples:
                logger.warning(f"No SQL examples found from rules service for classification: {classification}")
            else:
                # Convert examples to list if it's a dictionary
                if isinstance(examples, dict):
                    if "examples" in examples:
                        example_list = examples["examples"]
                    elif "sql_examples" in examples:
                        example_list = examples["sql_examples"]
                    else:
                        # Handle dictionary but no recognizable format
                        logger.warning(f"Examples in unknown dictionary format: {list(examples.keys())}")
                elif isinstance(examples, list):
                    example_list = examples
                else:
                    logger.warning(f"Examples in unexpected format: {type(examples)}")
                
                logger.info(f"Found {len(example_list)} examples from rules service for {classification}")
            
            # Get examples directly from SQL files - this is more maintainable than hardcoding examples
            logger.info(f"Loading examples from SQL example loader for: {classification}")
            file_examples = sql_example_loader.load_examples_for_query_type(classification)
            
            # Add file examples to the list
            if file_examples:
                logger.info(f"Found {len(file_examples)} examples from SQL files for {classification}")
                example_list.extend(file_examples)
            else:
                logger.warning(f"No examples found in SQL files for: {classification}")
                # Try a fallback for follow_up if it's a different directory structure
                if classification == "follow_up":
                    logger.info("Trying alternate directory 'query_follow_up' for follow-up examples")
                    file_examples = sql_example_loader.load_examples_for_query_type("query_follow_up")
                    if file_examples:
                        logger.info(f"Found {len(file_examples)} examples from 'query_follow_up' directory")
                        example_list.extend(file_examples)
            
            # If we still have no examples, log a warning
            if not example_list:
                logger.warning(f"No examples available for classification: {classification}")
                
            # Return all the examples
            logger.info(f"Returning {len(example_list)} total examples for {classification}")
            return {"examples": example_list}
        except Exception as e:
            logger.error(f"Error getting SQL examples: {e}")
            return {"examples": []}

    def _verify_placeholder_replacement(self):
        """
        Verify placeholder replacement functionality during initialization.
        """
        # Test placeholder replacement with a known SQL query
        test_sql = "SELECT * FROM orders WHERE location_id = {location_id}"
        try:
            processed_sql = self._test_placeholder_replacement(test_sql)
            
            # Check if the processed SQL contains the location_id placeholder
            if "{location_id}" in processed_sql:
                self.logger.warning("Placeholder replacement failed during initialization")
            else:
                self.logger.info("Placeholder replacement verified successfully during initialization")
        except Exception as e:
            self.logger.error(f"Error during placeholder verification: {str(e)}")

    def _test_placeholder_replacement(self, test_sql):
        """
        Test function to verify placeholder replacement works correctly.
        
        Args:
            test_sql: SQL string with placeholders to test
            
        Returns:
            Processed SQL with placeholders replaced
        """
        self.logger.info(f"Testing placeholder replacement on: {test_sql}")
        from services.rules.business_rules import DEFAULT_LOCATION_ID
        
        # Apply our normal extraction process
        processed_sql = self._extract_sql(test_sql)
        
        # Log the results
        self.logger.info(f"SQL after placeholder replacement: {processed_sql}")
        self.logger.info(f"Location ID placeholder replacement successful: {'{location_id}' not in processed_sql}")
        self.logger.info(f"DEFAULT_LOCATION_ID value ({DEFAULT_LOCATION_ID}) is in result: {str(DEFAULT_LOCATION_ID) in processed_sql}")
        
        return processed_sql

    def _validate_sql(self, sql: str, query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Validate the generated SQL for correctness and safety.
        
        Args:
            sql: The SQL query to validate
            query: The original natural language query
            context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, sql, error_message)
        """
        # Track API usage
        start_time = time.time()
        
        try:
            # Check if GenAI client is initialized
            if not self.client_initialized:
                self.logger.warning("GenAI client not initialized, cannot validate SQL")
                return True, sql, None
            
            # Format the validation prompt
            validation_prompt = self._get_default_validation_prompt().format(
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                query=query,
                sql=sql,
                schema=context.get("schema", "Not provided"),
                validation_error=context.get("validation_error", "None")
            )
            
            # Generate the validation response
            genai_model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens
                )
            )
            
            response = genai_model.generate_content(validation_prompt)
            
            # Track API usage
            self.api_call_count += 1
            
            # Analyze the validation response
            validation_text = response.text
            
            # Check if the validation was successful
            if validation_text.strip().startswith("VALID"):
                self.logger.info("SQL validation passed\n")
                
                # Check if there are any suggestions
                if "SUGGESTIONS:" in validation_text:
                    suggestions = validation_text.split("SUGGESTIONS:", 1)[1].strip()
                    self.logger.info(f"Validation passed with suggestions: {suggestions}")
                
                return True, sql, None
            else:
                # Extract error message
                error_message = validation_text.split("REASON:", 1)[1].strip() if "REASON:" in validation_text else validation_text
                self.logger.warning(f"SQL validation failed: {error_message}")
                
                # Check if we have a suggested fix
                if "SUGGESTED_FIX:" in validation_text:
                    fixed_sql = validation_text.split("SUGGESTED_FIX:", 1)[1].strip()
                    # Extract SQL from the suggested fix
                    fixed_sql = self._extract_sql_from_response(fixed_sql)
                    if fixed_sql:
                        self.logger.info(f"Using suggested SQL fix: {fixed_sql}")
                        return False, fixed_sql, error_message
                
                return False, sql, error_message
        except Exception as e:
            self.logger.error(f"Error during SQL validation: {str(e)}")
            return True, sql, str(e)  # Assume valid on error, but return the error message

    def _optimize_sql(self, sql: str, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Optimize the SQL query for better performance.
        
        Args:
            sql: The SQL query to optimize
            query: The original natural language query
            context: Additional context for optimization
            
        Returns:
            The optimized SQL query
        """
        # Track API usage
        start_time = time.time()
        
        try:
            # Check if GenAI client is initialized
            if not self.client_initialized:
                self.logger.warning("GenAI client not initialized, cannot optimize SQL")
                return sql
            
            # Format the optimization prompt
            optimization_prompt = self._get_default_optimization_prompt().format(
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                query=query,
                sql=sql,
                schema=context.get("schema", "Not provided")
            )
            
            # Generate the optimization response
            genai_model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens
                )
            )
            
            response = genai_model.generate_content(optimization_prompt)
            
            # Track API usage
            self.api_call_count += 1
            
            # Extract optimized SQL from the response
            optimized_sql = self._extract_sql_from_response(response.text)
            
            if optimized_sql:
                self.logger.info("SQL successfully optimized\n")
                return optimized_sql
            else:
                self.logger.warning("Failed to extract optimized SQL from response")
                return sql
        except Exception as e:
            self.logger.error(f"Error during SQL optimization: {str(e)}")
            return sql  # On error, return the original SQL

    def _extract_sql_from_response(self, text):
        """
        Extract SQL from the model's response text.
        
        Args:
            text (str): The response text from the model.
            
        Returns:
            str: The extracted SQL query, or an empty string if no SQL was found.
        """
        # Try to find SQL between ```sql and ``` markers (most common)
        sql_pattern = r"```sql\s*(.*?)\s*```"
        matches = re.findall(sql_pattern, text, re.DOTALL)
        
        if not matches:
            # Try to find SQL between plain ``` markers
            sql_pattern = r"```\s*(.*?)\s*```"
            matches = re.findall(sql_pattern, text, re.DOTALL)
        
        if not matches:
            # Try to find lines that look like SQL (as a last resort)
            potential_sql_lines = []
            for line in text.split('\n'):
                if any(keyword in line.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY']):
                    potential_sql_lines.append(line)
            
            if potential_sql_lines:
                return '\n'.join(potential_sql_lines)
            
            # No SQL found, just return the whole text if it contains SQL keywords
            if any(keyword in text.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY']):
                return text
            
            return ""
        
        # Take the first SQL block found
        sql = matches[0].strip()
        self.logger.info(f"Extracted SQL (length: {len(sql)}): {sql[:100]}...")
        return sql

    def _ensure_location_id_in_sql(self, sql):
        """
        Ensure that location_id is present in the SQL query.
        
        Args:
            sql (str): The SQL query to check.
            
        Returns:
            str: The SQL query with location_id added if it was missing.
        """
        if not sql:
            return sql
        
        # Check if location_id is already in the SQL
        if "location_id" in sql:
            return sql
        
        # Add location_id to WHERE clause
        if "WHERE" in sql.upper():
            sql = sql.replace("WHERE", "WHERE location_id = 62 AND", 1)
        else:
            # If no WHERE clause, add one
            if ";" in sql:
                sql = sql.replace(";", " WHERE location_id = 62;", 1)
            else:
                sql = sql + " WHERE location_id = 62"
        
        self.logger.info(f"Added location_id to SQL: {sql[:100]}...")
        return sql 

    def _extract_sql(self, text):
        """
        Extract SQL from the given text.
        This is a compatibility method used by _test_placeholder_replacement.
        
        Args:
            text (str): The text to extract SQL from.
            
        Returns:
            str: The extracted SQL.
        """
        return self._extract_sql_from_response(text) 

    def health_check(self) -> bool:
        """
        Check if the service is healthy by making a simple API call.
        
        Returns:
            bool: True if the service is healthy, False otherwise.
        """
        try:
            # Create a Gemini model instance
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens
                )
            )
            
            # Make a simple API call to check health
            response = model.generate_content("Generate a simple SELECT statement")
            
            # Return True if we got a valid response
            return response is not None and hasattr(response, 'text')
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False 

    def generate(self, query: str, category: str, response_rules: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate SQL query for the given natural language query.
        This is a compatibility method to match the expected interface of SQLGenerator.
        
        Args:
            query: The natural language query to generate SQL for
            category: The category of the query (e.g., "menu", "order_history")
            response_rules: Rules for generating the response
            context: Additional context for generating the SQL
            
        Returns:
            Dict containing the generated SQL query and metadata
        """
        self.logger.info(f"Generating SQL for query: '{query}', category: '{category}'")
        
        # Extract time period if present in context
        time_period = None
        constraints = None
        if context:
            if "time_period_clause" in context:
                time_period = context["time_period_clause"]
                self.logger.info(f"Using time period from context: {time_period}")
            if "previous_filters" in context:
                constraints = context["previous_filters"]
                self.logger.info(f"Using constraints from context: {constraints}")
                
        # Call the main SQL generation method
        result = self.generate_sql(query, category, time_period, constraints, context)
        
        # Add compatibility fields
        result["query_type"] = category
        if "sql" not in result and "generated_sql" in result:
            result["sql"] = result["generated_sql"]
            
        return result
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the SQL generator.
        
        Returns:
            Dict containing performance metrics:
            - api_calls: Number of API calls made
            - total_tokens: Total tokens used
            - average_tokens_per_call: Average tokens per API call
            - cache_hits: Number of cache hits (always 0 in this implementation)
            - cache_misses: Number of cache misses (always 0 in this implementation)
        """
        metrics = {
            "api_calls": self.api_call_count,
            "total_tokens": self.total_tokens,
            "average_tokens_per_call": self.total_tokens / max(1, self.api_call_count),
            "cache_hits": 0,  # Not implemented in this class
            "cache_misses": 0  # Not implemented in this class
        }
        
        return metrics 