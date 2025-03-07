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
            rules_str = "Rules:\n"
            for rule_name, rule_description in rules.items():
                rules_str += f"- {rule_name}: {rule_description}\n"
        
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
        Build a prompt for generating SQL from a natural language query.
        
        Args:
            query: The natural language query
            examples: List of example queries and SQL
            context: Additional context like schema, rules, etc.
            
        Returns:
            Formatted prompt string
        """
        # Start with the template
        prompt = self.prompt_template
        
        # Get rules service for schema information
        rules_service = ServiceRegistry.get_service("rules")
        
        # Get schema information if available
        schema_str = ""
        if "query_type" in context:
            query_type = context["query_type"]
            schema = rules_service.get_schema_for_type(query_type)
            
            if schema:
                schema_str = self._format_schema(schema)
        
        # Get rules if available
        rules_str = ""
        if "rules" in context:
            rules_str = self._format_rules(context["rules"])
        
        # Get patterns if available
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
        Generate SQL from the user query using OpenAI.
        
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
        log_file = os.path.join(log_dir, f"openai_sql_{session_id}.log")
        
        # Create a detailed log file for this prompt if detailed logging is enabled
        if self.enable_detailed_logging:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
                f.write(f"QUERY: {query}\n")
                f.write(f"CATEGORY: {query_type}\n")
                f.write("\n----- FULL PROMPT TO OPENAI -----\n\n")
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
                
                # Call OpenAI API
                api_call_start = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a PostgreSQL expert that translates natural language questions into SQL queries."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                # Update metrics
                self.api_call_count += 1
                api_call_duration = time.time() - api_call_start
                self.total_latency += api_call_duration
                # Get token usage from the response
                self.total_tokens += response.usage.total_tokens
                
                raw_response = response.choices[0].message.content
                
                # Log the raw response if detailed logging is enabled
                if self.enable_detailed_logging:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("----- RAW OPENAI RESPONSE -----\n\n")
                        f.write(raw_response)
                        f.write("\n\n")
                
                # Extract SQL from the response
                sql = self._extract_sql(raw_response)
                
                # If SQL was successfully extracted, break the retry loop
                if sql:
                    break
                    
                # If no SQL was extracted, log and retry
                logger.warning(f"Failed to extract SQL from response. Attempt {attempts}/{max_attempts}")
                self.retry_count += 1
                
            except Exception as e:
                error_msg = f"Error generating SQL: {str(e)}"
                logger.error(error_msg)
                
                # Log the error if detailed logging is enabled
                if self.enable_detailed_logging:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("----- ERROR -----\n\n")
                        f.write(error_msg)
                        f.write("\n\n")
                
                # Sleep briefly before retry
                time.sleep(0.5)
                self.retry_count += 1
        
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