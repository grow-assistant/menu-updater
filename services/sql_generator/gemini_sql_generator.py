"""
Enhanced service for generating SQL queries using Google's Gemini API.
Includes improved prompt building, SQL validation, and optimization.
"""
import logging
import re
import time
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Tuple
import uuid
import os
from datetime import datetime

from services.rules.rules_service import RulesService
from services.utils.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class GeminiSQLGenerator:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the enhanced Gemini SQL generator."""
        # Configure Gemini API
        api_key = config["api"]["gemini"]["api_key"]
        self.model = config["api"]["gemini"].get("model", "gemini-1.5-Flash")
        self.temperature = config["api"]["gemini"].get("temperature", 0.2)
        self.max_tokens = config["api"]["gemini"].get("max_tokens", 1024)
        genai.configure(api_key=api_key)
        
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
        self.prompt_template_path = config["services"]["sql_generator"].get(
            "prompt_template", "services/sql_generator/templates/sql_prompt.txt"
        )
        self.validation_prompt_path = config["services"]["sql_generator"].get(
            "validation_prompt", "services/sql_generator/templates/sql_validator.txt"
        )
        self.optimization_prompt_path = config["services"]["sql_generator"].get(
            "optimization_prompt", "services/sql_generator/templates/sql_optimizer.txt"
        )
        
        # Load prompt templates
        try:
            with open(self.prompt_template_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception as e:
            logger.warning(f"Failed to load prompt template: {e}")
            self.prompt_template = self._get_default_prompt_template()
            
        try:
            with open(self.validation_prompt_path, "r", encoding="utf-8") as f:
                self.validation_prompt = f.read()
        except Exception as e:
            logger.warning(f"Failed to load validation prompt: {e}")
            self.validation_prompt = self._get_default_validation_prompt()
            
        try:
            with open(self.optimization_prompt_path, "r", encoding="utf-8") as f:
                self.optimization_prompt = f.read()
        except Exception as e:
            logger.warning(f"Failed to load optimization prompt: {e}")
            self.optimization_prompt = self._get_default_optimization_prompt()
        
        # Initialize the model
        try:
            self.model_instance = genai.GenerativeModel(model_name=self.model)
            logger.info(f"SQLGenerator initialized with max_tokens={self.max_tokens}, temperature={self.temperature}")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
            self.model_instance = None
        
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
        """Get default validation prompt if file is not found."""
        return """
        You are a PostgreSQL expert that validates SQL queries for correctness and security.
        
        Analyze the following SQL query and identify any issues:
        1. Syntax errors
        2. Security vulnerabilities (SQL injection risks)
        3. Potential performance issues
        4. Compliance with database schema
        
        Database Schema:
        {schema}
        
        SQL Query to validate:
        {sql}
        
        Provide your analysis in the following format:
        - Valid: [Yes/No]
        - Issues: [List of issues found]
        - Corrected SQL: [Corrected SQL if issues were found]
        """
    
    def _get_default_optimization_prompt(self) -> str:
        """Get default optimization prompt if file is not found."""
        return """
        You are a PostgreSQL performance optimization expert.
        
        Optimize the following SQL query for better performance:
        
        {sql}
        
        Database Schema:
        {schema}
        
        Consider the following optimization techniques:
        1. Proper indexing suggestions
        2. Query restructuring
        3. Avoiding full table scans
        4. Optimizing JOIN operations
        5. Using appropriate WHERE clauses
        
        Provide your optimized query and explain the improvements:
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
        
        # Import the actual location ID value from business rules
        from services.rules.business_rules import DEFAULT_LOCATION_ID
        
        # Add a strongly worded reminder about order status being integers and location ID filtering
        critical_requirements = """
CRITICAL REQUIREMENTS:
- Order status values must ALWAYS be used as integers, never as strings
- Completed orders have status=7 (not 'COMPLETED')
- Cancelled orders have status=6 (not 'CANCELLED')
- In-progress orders have status between 3-5 (not 'IN PROGRESS')

*** MANDATORY LOCATION FILTERING ***
- Every query on the orders table MUST filter by location_id
- You MUST include: o.location_id = {location_id}
- This is a CRITICAL security requirement for data isolation
- Without this filter, results will include data from all locations
- The specific location ID to use is: {location_id}
""".format(location_id=DEFAULT_LOCATION_ID)
        
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
        
        # Add previous SQL queries as context if available
        previous_sql_str = ""
        if "previous_sql" in context and context["previous_sql"]:
            previous_sql = context["previous_sql"]
            previous_sql_str = "\nPrevious Related SQL Queries (for context):\n"
            
            for i, sql_entry in enumerate(reversed(previous_sql), 1):
                previous_sql_str += f"Previous Query {i}:\n"
                previous_sql_str += f"User Asked: {sql_entry.get('query', 'Unknown')}\n"
                previous_sql_str += f"SQL Generated: {sql_entry.get('sql', 'Unknown')}\n\n"
                
            previous_sql_str += """
IMPORTANT CONTEXT MAINTENANCE INSTRUCTIONS:
1. If the current question contains terms like "those", "these", or otherwise refers to previous results, it's a follow-up query.
2. For follow-up queries, ALWAYS maintain the same filtering conditions (WHERE clauses) from the most recent relevant query.
3. Pay special attention to date filters, status filters, and location filters - these should be preserved exactly.
4. Example: If previous query filtered "orders on 2/21/2025 with status 7", and current query asks "who placed those orders", 
   your new query MUST include "WHERE (o.updated_at - INTERVAL '7 hours')::date = '2025-02-21' AND o.status = 7".
5. Never drop important filters when answering follow-up questions - context continuity is critical.
"""
        
        # Replace the placeholders
        prompt = prompt.replace("{schema}", schema_str)
        prompt = prompt.replace("{rules}", rules_str)
        prompt = prompt.replace("{patterns}", patterns_str)
        prompt = prompt.replace("{examples}", examples_str)
        prompt = prompt.replace("{query}", query)
        
        # Add previous SQL context to the end of the prompt
        if previous_sql_str:
            prompt += "\n" + previous_sql_str
        
        return prompt
    
    def generate_sql(self, query: str, examples: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SQL from the user query using Gemini with validation and optimization.
        
        Args:
            query: The user's query text
            examples: List of relevant SQL examples
            context: Additional context information
            
        Returns:
            Dictionary containing the generated SQL and metadata
        """
        start_time = time.time()
        query_type = context.get('query_type', 'unknown')
        
        # Check if we have a cached prompt for this query type
        cache_key = f"{query_type}_{hash(str(examples))}"
        current_time = time.time()
        
        # Build or use cached prompt
        if (cache_key in self.prompt_cache and 
            current_time - self.prompt_cache_timestamps.get(cache_key, 0) < self.prompt_cache_ttl):
            # Use cached prompt
            prompt = self.prompt_cache[cache_key].replace("{{QUERY}}", query)
            logger.debug(f"Using cached prompt template for {query_type}")
        else:
            # Build new prompt
            prompt = self._build_prompt(query, examples, context)
            
            # Cache the prompt with a placeholder for the query
            cacheable_prompt = prompt.replace(query, "{{QUERY}}")
            self.prompt_cache[cache_key] = cacheable_prompt
            self.prompt_cache_timestamps[cache_key] = current_time
        
        logger.info(f"Built SQL generation prompt with {len(examples)} examples and context for {query_type}")
        
        # Initialize log_file regardless of detailed logging setting
        session_id = str(uuid.uuid4())[:8]
        log_dir = os.path.join("logs", "ai_prompts")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"gemini_sql_{session_id}.log")
        
        # Create a detailed log file for this prompt if detailed logging is enabled
        if self.enable_detailed_logging:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
                f.write(f"QUERY: {query}\n")
                f.write(f"CATEGORY: {query_type}\n")
                f.write("\n----- FULL PROMPT TO GEMINI -----\n\n")
                f.write(prompt)
                f.write("\n\n")
            
            # Log prompt location
            logger.info(f"Full prompt logged to: {log_file}")
        
        # Track generation attempts
        attempts = 0
        sql = ""
        raw_response = ""
        
        # Set up retry logic in case of failures
        max_attempts = 3
        
        while attempts < max_attempts:
            attempts += 1
            
            try:
                logger.info(f"Generating SQL with model: {self.model}, attempt: {attempts}/{max_attempts}")
                
                # Call Gemini API
                model = self.model_instance
                if not model:
                    model = genai.GenerativeModel(self.model)
                    
                generation_config = {
                    "max_output_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
                
                # Track API call
                api_call_start = time.time()
                
                response = model.generate_content(
                    prompt, 
                    generation_config=generation_config
                )
                
                # Update metrics
                self.api_call_count += 1
                api_call_duration = time.time() - api_call_start
                self.total_latency += api_call_duration
                # Estimate tokens used (could be replaced with actual token count if available)
                estimated_tokens = len(prompt) // 4 + len(response.text) // 4
                self.total_tokens += estimated_tokens
                
                raw_response = response.text
                
                # Log the raw response if detailed logging is enabled
                if self.enable_detailed_logging:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("----- RAW GEMINI RESPONSE -----\n\n")
                        f.write(raw_response)
                        f.write("\n\n")
                
                # Extract SQL from the response
                sql = self._extract_sql(raw_response)
                
                if sql:
                    # Log the extracted SQL if detailed logging is enabled
                    if self.enable_detailed_logging:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write("----- EXTRACTED SQL -----\n\n")
                            f.write(sql)
                            f.write("\n\n")
                    
                    logger.info(f"Extracted SQL (length: {len(sql)}): {sql[:100]}...")
                    break
                else:
                    logger.warning(f"Failed to extract SQL from response in attempt {attempts}")
                    # Log extraction failure if detailed logging is enabled
                    if self.enable_detailed_logging:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write("----- SQL EXTRACTION FAILED -----\n\n")
                            f.write("Could not extract SQL from the response text.")
                            f.write("\n\n")
                    
                    # Update retry counter
                    self.retry_count += 1
            except Exception as e:
                error_msg = f"Error generating SQL in attempt {attempts}: {str(e)}"
                logger.error(error_msg)
                # Log the error if detailed logging is enabled
                if self.enable_detailed_logging:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("----- ERROR -----\n\n")
                        f.write(error_msg)
                        f.write("\n\n")
                
                # Wait before retrying
                time.sleep(1)
        
        # If we couldn't generate SQL after all attempts
        if not sql:
            logger.error("Failed to generate valid SQL after all attempts")
            return {
                "success": False,
                "error": "Failed to generate valid SQL",
                "query": None
            }
        
        # Final result construction - ensure we always return a valid dict
        result = {
            "success": bool(sql),  # Success is True if SQL is not empty
            "query_time": time.time() - start_time,
            "model": self.model,
            "attempts": attempts + 1
        }
        
        if sql:
            result["query"] = sql
            result["query_type"] = "SELECT"  # Default to SELECT, can be refined further
        else:
            result["error"] = f"Failed to generate SQL after {attempts+1} attempts"
            result["raw_response"] = raw_response[:500] if len(raw_response) > 500 else raw_response
            
        return result
    
    def _extract_sql(self, text: str) -> str:
        """
        Extract SQL from model response and validate basic requirements.
        
        Args:
            text: Raw model response
            
        Returns:
            Extracted SQL query
        """
        # Extract SQL from response using regex pattern
        sql_pattern = r"```sql\s+(.*?)\s+```"
        match = re.search(sql_pattern, text, re.DOTALL)
        
        if match:
            sql = match.group(1).strip()
        else:
            # Try alternative pattern without language specification
            alt_pattern = r"```\s+(.*?)\s+```"
            alt_match = re.search(alt_pattern, text, re.DOTALL)
            if alt_match:
                sql = alt_match.group(1).strip()
            else:
                # If no code block found, try to use the entire text
                sql = text.strip()
        
        # Basic preprocessing - remove any explanation text outside the SQL
        sql_lines = []
        for line in sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--') and not line.lower().startswith('explain') and not line.lower().startswith('note:'):
                sql_lines.append(line)
        
        processed_sql = '\n'.join(sql_lines)
        
        # Logging for debug
        logger.debug(f"Extracted SQL: {processed_sql[:100]}...")
        
        # Check for the presence of location_id filtering if this is an order query
        # This is a critical security measure that must be enforced
        from services.rules.business_rules import DEFAULT_LOCATION_ID
        
        # Check if this is a query on the orders table
        if " orders " in processed_sql.lower() or " orders\n" in processed_sql.lower() or "from orders" in processed_sql.lower():
            # Get table alias if used
            alias_pattern = r"from\s+orders\s+(?:as\s+)?([a-zA-Z0-9_]+)"
            alias_match = re.search(alias_pattern, processed_sql.lower(), re.IGNORECASE)
            
            table_prefix = ""
            if alias_match:
                table_prefix = f"{alias_match.group(1)}."
            else:
                table_prefix = "orders."
            
            # Check if location_id filtering is present
            location_filter_pattern = rf"{table_prefix}location_id\s*=\s*\d+"
            if not re.search(location_filter_pattern, processed_sql, re.IGNORECASE):
                logger.warning(f"Location ID filtering missing in SQL query: {processed_sql}")
                
                # Add the location filter to ensure data isolation
                # Find the WHERE clause if it exists
                if "where" in processed_sql.lower():
                    processed_sql = processed_sql.replace("WHERE", f"WHERE {table_prefix}location_id = {DEFAULT_LOCATION_ID} AND ", 1)
                    processed_sql = processed_sql.replace("where", f"where {table_prefix}location_id = {DEFAULT_LOCATION_ID} AND ", 1)
                else:
                    # Add a WHERE clause before GROUP BY, ORDER BY, LIMIT, etc. if they exist
                    for clause in ["group by", "order by", "limit", "having"]:
                        if clause in processed_sql.lower():
                            pattern = re.compile(f"({clause})", re.IGNORECASE)
                            processed_sql = pattern.sub(f"WHERE {table_prefix}location_id = {DEFAULT_LOCATION_ID} \n\\1", processed_sql, 1)
                            break
                    else:
                        # If no clauses found, add WHERE at the end
                        processed_sql += f"\nWHERE {table_prefix}location_id = {DEFAULT_LOCATION_ID}"
                
                logger.info(f"Location filter added to query: {processed_sql}")
        
        return processed_sql
    
    def health_check(self) -> bool:
        """
        Check if the Gemini API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple test query to Gemini
            model = genai.GenerativeModel(self.model)
            response = model.generate_content("Generate a simple SELECT statement")
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
        examples = rules_and_examples.get("examples", [])
        
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
        return {
            'api_call_count': self.api_call_count,
            'total_tokens_used': self.total_tokens,
            'average_latency': self.total_latency / max(1, self.api_call_count),
            'retry_count': self.retry_count
        } 