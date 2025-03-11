"""
Enhanced service for generating SQL queries using OpenAI's API.
"""
import logging
import re
import time
import openai
from openai import OpenAI
from typing import Dict, Any, List, Optional, Tuple
import uuid
import os
from datetime import datetime

from services.rules.rules_service import RulesService
from services.utils.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class OpenAISQLGenerator:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the enhanced OpenAI SQL generator."""
        # Configure OpenAI API
        api_key = config["api"]["openai"]["api_key"]
        self.model = config["api"]["openai"].get("model", "gpt-4o-mini")
        self.temperature = config["api"]["openai"].get("temperature", 0.2)
        self.max_tokens = config["api"]["openai"].get("max_tokens", 2000)
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        
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
        
        logger.debug(f"OpenAI SQL Generator initialized with detailed_logging={self.enable_detailed_logging}")
        
        # Load prompt templates
        self.prompt_template_path = config["services"]["sql_generator"].get(
            "prompt_template", "services/sql_generator/templates/sql_prompt.txt"
        )
        
        # Load prompt template
        try:
            with open(self.prompt_template_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception as e:
            logger.warning(f"Failed to load prompt template: {e}")
            self.prompt_template = self._get_default_prompt_template()
        
        # Configuration options
        self.max_retries = config["services"]["sql_generator"].get("max_retries", 2)
        
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
        
        CRITICAL REQUIREMENTS:
        1. FORBIDDEN: DO NOT USE o.order_date - this column does not exist in the database!
        2. The orders table does NOT have an 'order_date' column. ALWAYS use (o.updated_at - INTERVAL '7 hours')::date for date filtering.
        3. NEVER reference o.order_date as it does not exist and will cause database errors!
        4. Every query MUST include proper location filtering via the o.location_id field.

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
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema information for the prompt."""
        schema_str = ""
        
        # Process schema if provided
        if schema:
            schema_str = "Tables:\n"
            for table_name, table_info in schema.items():
                schema_str += f"- {table_name} ({', '.join(table_info.get('columns', []))})\n"
                
                # Add relationships if available
                if "relationships" in table_info:
                    schema_str += "  Relationships:\n"
                    for rel in table_info["relationships"]:
                        schema_str += f"  - {rel}\n"
        
        return schema_str
    
    def _format_rules(self, rules: Dict[str, Any]) -> str:
        """Format business rules for the prompt."""
        rules_str = ""
        
        # Process rules if provided
        if rules:
            # First add critical requirements if they exist
            if "critical_requirements" in rules:
                rules_str = "CRITICAL REQUIREMENTS:\n"
                for rule_name, rule_description in rules["critical_requirements"].items():
                    rules_str += f"- !!! {rule_name}: {rule_description} !!!\n"
                rules_str += "\n"
            
            # Add other rule categories
            rules_str += "Rules:\n"
            for category, category_rules in rules.items():
                if category == "critical_requirements":
                    # Already handled above
                    continue
                    
                if isinstance(category_rules, dict):
                    # Handle nested rule categories
                    rules_str += f"\n{category.upper()} RULES:\n"
                    for rule_name, rule_description in category_rules.items():
                        rules_str += f"- {rule_name}: {rule_description}\n"
                else:
                    # Handle flat rules
                    rules_str += f"- {category}: {category_rules}\n"
        
        return rules_str
    
    def _format_patterns(self, patterns: Dict[str, str]) -> str:
        """Format SQL patterns for the prompt."""
        patterns_str = ""
        
        # Process patterns if provided
        if patterns:
            patterns_str = "Patterns:\n"
            for pattern_name, pattern_sql in patterns.items():
                patterns_str += f"- {pattern_name}:\n```sql\n{pattern_sql}\n```\n"
        
        return patterns_str
    
    def _format_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format SQL examples for the prompt."""
        examples_str = ""
        
        # Format up to 5 examples (to avoid excessive prompt length)
        if examples:
            examples_str = "Examples:\n"
            for i, example in enumerate(examples[:5]):
                examples_str += f"Query: {example.get('query', '')}\n"
                examples_str += f"SQL: ```sql\n{example.get('sql', '')}\n```\n\n"
        
        return examples_str
    
    def _build_prompt(self, query: str, examples: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        Build the prompt for the OpenAI API request.
        
        Args:
            query: User's natural language query
            examples: List of examples for few-shot learning
            context: Additional context for the query
            
        Returns:
            Formatted prompt string
        """
        # Get services via registry to avoid circular imports
        try:
            # Try to get the rules service
            rules_service = ServiceRegistry.get_service("rules")
            if rules_service:
                # Get rules for the category
                category = context.get("category", "")
                rules = rules_service.get_rules_for_category(category) if category else {}
            else:
                rules = {}
                logger.warning("Rules service not found in registry, no rules will be applied")
                
        except Exception as e:
            rules = {}
            logger.error(f"Error getting rules: {str(e)}")
        
        # Construct schema information
        schema_info = context.get("schema", "")
        
        # Format examples
        examples_text = ""
        if examples:
            for i, example in enumerate(examples):
                examples_text += f"Example {i+1}:\n"
                examples_text += f"Question: {example.get('query', '')}\n"
                examples_text += f"SQL: {example.get('sql', '')}\n\n"
        
        # Count examples for logging
        examples_count = len(examples) if examples else 0
        logger.info(f"Building prompt with {examples_count} examples for category: {context.get('category', 'unknown')}")
        
        # Log first example for debugging if available
        if examples_count > 0 and self.enable_detailed_logging:
            logger.debug(f"First example: Question: {examples[0].get('query', '')[:50]}...")
            logger.debug(f"First example: SQL: {examples[0].get('sql', '')[:50]}...")
        
        # Format rules
        rules_text = ""
        if rules:
            rules_text = "Query Rules:\n"
            for rule in rules:
                rules_text += f"- {rule}\n"
        
        # Extract any time period information
        time_period = context.get("time_period", "")
        if time_period:
            logger.info(f"Adding time period to prompt: {time_period}")
            rules_text += f"\nTime Period: {time_period}\n"
        
        # Format any SQL patterns
        patterns_text = context.get("patterns", "")
        
        # Substitute into the prompt template
        prompt = self.prompt_template.format(
            schema=schema_info,
            rules=rules_text,
            patterns=patterns_text,
            examples=examples_text,
            query=query
        )
        
        # Log detailed logging if enabled
        if self.enable_detailed_logging:
            logger.debug(f"Generated prompt (excerpt): {prompt[:500]}...")
        
        return prompt

    def generate_sql(self, query: str, examples: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SQL from natural language using OpenAI.
        
        Args:
            query: Natural language query
            examples: List of examples for few-shot learning
            context: Additional context for query
            
        Returns:
            Dictionary with generated SQL and metadata
        """
        start_time = time.time()
        self.api_call_count += 1
        
        # Build the prompt
        logger.info(f"Building SQL generation prompt with {len(examples)} examples and context for {context.get('category', 'unknown')}")
        prompt = self._build_prompt(query, examples, context)
        
        # Try to get a cached response
        cache_key = f"{query}_{context.get('category', '')}"
        if cache_key in self.prompt_cache:
            cache_time = self.prompt_cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.prompt_cache_ttl:
                logger.info(f"Using cached SQL for query: {query}")
                return self.prompt_cache[cache_key]
        
        # Set up parameters for the API call
        model = context.get("model", self.model)
        max_tokens = context.get("max_tokens", self.max_tokens)
        temperature = context.get("temperature", self.temperature)
        
        # Exponential backoff for retries
        max_retries = self.max_retries
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                logger.info(f"Generating SQL with model: {model}, attempt: {retry_count+1}/{max_retries+1}")
                
                # Log the model and parameters being used
                if self.enable_detailed_logging:
                    logger.debug(f"OpenAI parameters: model={model}, temperature={temperature}, max_tokens={max_tokens}")
                
                # Make the API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a PostgreSQL expert that translates natural language to SQL."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Extract the SQL from the response
                response_text = response.choices[0].message.content
                sql = self._extract_sql(response_text)
                
                # If no SQL was extracted, try to fix it
                if not sql:
                    logger.warning(f"No SQL found in response, attempting to extract from full response")
                    sql = response_text.strip()
                    
                    # If the response doesn't start with SELECT, INSERT, UPDATE, DELETE, WITH, try to find SQL
                    if not any(sql.upper().startswith(keyword) for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE", "WITH"]):
                        # Try to find SQL-like content
                        sql_matches = re.findall(r'(SELECT|INSERT|UPDATE|DELETE|WITH)[\s\S]+?;', sql, re.IGNORECASE)
                        if sql_matches:
                            sql = sql_matches[0]
                        else:
                            # If still no SQL found, raise an error to trigger retry
                            raise ValueError("No SQL statement found in response")
                
                # Calculate token usage and latency
                usage = response.usage
                completion_tokens = usage.completion_tokens if usage else 0
                prompt_tokens = usage.prompt_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else 0
                
                self.total_tokens += total_tokens
                
                end_time = time.time()
                latency = end_time - start_time
                self.total_latency += latency
                
                # Cache the result
                result = {
                    "sql": sql,
                    "model": model,
                    "tokens": {
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
                        "total": total_tokens
                    },
                    "latency": latency,
                    "metadata": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "model": model,
                        "examples_used": len(examples)
                    }
                }
                
                # Store in cache
                self.prompt_cache[cache_key] = result
                self.prompt_cache_timestamps[cache_key] = time.time()
                
                # Log success
                logger.info(f"Successfully generated SQL query in {latency:.2f} seconds")
                if self.enable_detailed_logging:
                    logger.debug(f"Generated SQL: {sql[:100]}...")
                
                return result
                
            except Exception as e:
                retry_count += 1
                self.retry_count += 1
                last_error = str(e)
                
                # Log error with different levels based on retry count
                if retry_count <= max_retries:
                    delay = 2 ** retry_count  # Exponential backoff
                    logger.warning(f"Error generating SQL (attempt {retry_count}/{max_retries+1}): {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    
                    # Try with a different model if available
                    if retry_count == 1 and model != "gpt-4o":
                        model = "gpt-4o"  # Use a more powerful model for the next attempt
                        logger.info(f"Switching to more powerful model for retry: {model}")
                else:
                    logger.error(f"Failed to generate SQL after {max_retries+1} attempts. Last error: {str(e)}")
        
        # If we get here, all retries failed
        end_time = time.time()
        latency = end_time - start_time
        
        error_result = {
            "sql": "",
            "error": last_error,
            "model": model,
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0
            },
            "latency": latency,
            "metadata": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": model,
                "examples_used": len(examples),
                "retry_count": retry_count
            }
        }
        
        return error_result
    
    def _extract_sql(self, text: str) -> str:
        """
        Extract SQL query from the model's response.
        
        Args:
            text: The raw response text
            
        Returns:
            Extracted SQL query
        """
        # Extract SQL between markdown code blocks
        sql_code_block_pattern = r"```(?:sql)?(.*?)```"
        matches = re.findall(sql_code_block_pattern, text, re.DOTALL)
        
        if matches:
            # Take the first SQL block found
            sql = matches[0].strip()
            return sql
            
        # If no matches with ```sql blocks, try to extract just the SQL commands
        # This is a simplistic approach that looks for common SQL keywords
        lines = text.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Look for SQL pattern start
            if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|ALTER|DROP|EXPLAIN|BEGIN|COMMIT|ROLLBACK)', line, re.IGNORECASE):
                in_sql = True
                
            if in_sql:
                sql_lines.append(line)
                
            # Look for SQL pattern end (often a semicolon or a statement terminator)
            if in_sql and line.endswith(';'):
                break
        
        if sql_lines:
            return '\n'.join(sql_lines)
            
        # If no SQL was found, return the entire text as a last resort
        # This is not ideal, but the validation step can help catch issues
        return text.strip()
    
    def health_check(self) -> bool:
        """
        Check if the OpenAI API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple test query to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Generate a simple SELECT statement"}
                ],
                max_tokens=50
            )
            return response is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def generate(self, query: str, category: str, rules_and_examples: Dict[str, Any], 
                additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate SQL for a given query (interface method for OrchestratorService).
        This method adapts the parameters from the orchestrator to the format expected by generate_sql.
        
        Args:
            query: The user's natural language query
            category: The query category as determined by the classifier
            rules_and_examples: Dictionary containing rules and examples for this query type
            additional_context: Optional additional context like previous SQL queries
            
        Returns:
            Dictionary with generated SQL and metadata
        """
        logger.debug(f"Generate called with query: '{query}', category: '{category}'")
        
        # Extract examples from rules_and_examples
        examples = rules_and_examples.get("sql_examples", rules_and_examples.get("examples", []))
        logger.info(f"Found {len(examples)} examples for category '{category}'")
        
        # Create context dictionary from category and rules
        context = {
            "query_type": category,
            "rules": rules_and_examples.get("query_rules", {})
        }
        
        # Add additional context if provided (like previous SQL)
        if additional_context:
            context.update(additional_context)
        
        # Call the actual implementation method
        return self.generate_sql(query, examples, context)
    
    def get_performance_metrics(self):
        """
        Get performance metrics for monitoring.
        
        Returns:
            Dictionary with metrics
        """
        avg_latency = self.total_latency / self.api_call_count if self.api_call_count > 0 else 0
        
        return {
            "api_calls": self.api_call_count,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": self.total_tokens / self.api_call_count if self.api_call_count > 0 else 0,
            "total_latency": self.total_latency,
            "avg_latency": avg_latency,
            "retry_count": self.retry_count,
            "retry_rate": self.retry_count / self.api_call_count if self.api_call_count > 0 else 0,
        } 