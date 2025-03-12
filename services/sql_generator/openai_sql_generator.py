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
from dotenv import load_dotenv

from services.rules.rules_service import RulesService
from services.utils.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class OpenAISQLGenerator:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAISQLGenerator with configuration.
        
        Args:
            config: Configuration dictionary
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Get API key from config or environment
        api_key = config.get("api", {}).get("openai", {}).get("api_key")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                logger.info("Using OpenAI API key from environment variable")
            else:
                logger.warning("No OpenAI API key found in config or environment variables")
                
        # Initialize OpenAI client with the API key
        self.client = OpenAI(api_key=api_key)
        
        # Load other configuration parameters
        self.model = config.get("services", {}).get("sql_generator", {}).get("model", "gpt-4o-mini")
        self.temperature = config.get("services", {}).get("sql_generator", {}).get("temperature", 0.7)
        self.max_tokens = config.get("services", {}).get("sql_generator", {}).get("max_tokens", 2000)
        self.enable_caching = config.get("services", {}).get("sql_generator", {}).get("enable_caching", True)
        
        # Performance tracking
        self.retry_count = 0
        self.total_tokens = 0
        self.api_calls = 0
        self.total_latency = 0
        
        # Caching for results
        self.prompt_cache = {}
        self.prompt_cache_timestamps = {}
        self.prompt_cache_ttl = 3600  # 1 hour
        
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
        
        # Add conversation history context for follow-up questions
        conversation_context = ""
        if context.get("is_followup", False):
            logger.info("Detected follow-up question, adding conversation context")
            
            # Add previous query
            last_query = ""
            if "session_history" in context and context["session_history"]:
                # Get the most recent query
                last_entry = context["session_history"][-1]
                last_query = last_entry.get("query", "")
                if last_query:
                    conversation_context += f"Previous question: {last_query}\n"
                
                # Add previous query results if available
                if "results" in last_entry and last_entry["results"]:
                    conversation_context += f"Results of previous query: {last_entry['results']}\n"
            
            # Add previous SQL
            previous_sql = context.get("previous_sql", "")
            if previous_sql:
                conversation_context += f"SQL for previous question: {previous_sql}\n"
                
                # Extract filters from previous SQL
                where_clause = ""
                where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|LIMIT|$)', previous_sql, re.IGNORECASE | re.DOTALL)
                if where_match:
                    where_clause = where_match.group(1).strip()
                    conversation_context += f"Previous filters: {where_clause}\n"
            
            # Add time period explicitly
            time_period_clause = context.get("time_period_clause", "")
            if time_period_clause:
                conversation_context += f"Time period from previous query: {time_period_clause}\n"
            
            # Add previous filters explicitly
            if "previous_filters" in context and context["previous_filters"]:
                conversation_context += "Filters from previous query:\n"
                for filter_name, filter_value in context["previous_filters"].items():
                    conversation_context += f"- {filter_name}: {filter_value}\n"
            
            # Special handling for references to "those orders"
            if any(term in query.lower() for term in ["those orders", "these orders", "the orders"]):
                conversation_context += "\nIMPORTANT: The current query refers to the same orders from the previous query. " \
                                      "You MUST maintain the same WHERE conditions when showing order information.\n"
                # Add more explicit instructions
                conversation_context += "DO NOT DROP any time period or status filters that were in the previous query.\n"
            
            # Enhanced handling for "who" queries
            if "who" in query.lower() and any(term in query.lower() for term in ["placed", "order", "those orders", "these orders"]):
                conversation_context += "\nIMPORTANT: This query is asking about who placed the orders from the previous query. " \
                                      "You MUST maintain all filters from the previous query and return customer/user information.\n"
                conversation_context += "CRITICAL INSTRUCTIONS FOR THIS QUERY:\n"
                conversation_context += "1. Join orders to users table: orders o JOIN users u ON o.customer_id = u.id\n"
                conversation_context += "2. Return customer names using: u.first_name || ' ' || u.last_name AS customer_name\n"
                conversation_context += "3. Include all WHERE conditions from the previous query\n"
                conversation_context += "4. DO NOT use user_id for joins, ALWAYS use customer_id\n"
                
                # Add sample SQL for who placed orders
                conversation_context += "\nSAMPLE SQL for 'who placed orders' query:\n"
                conversation_context += """
SELECT 
    u.first_name || ' ' || u.last_name AS customer_name,
    COUNT(o.id) AS order_count 
FROM 
    orders o
JOIN 
    users u ON o.customer_id = u.id
WHERE 
    o.location_id = 62
    -- Maintain other filters from previous query here
GROUP BY 
    u.first_name, u.last_name
ORDER BY 
    order_count DESC;
"""

        # Format any SQL patterns
        patterns_text = context.get("patterns", "")
        
        # Add schema hints
        schema_hints = context.get("schema_hints", "")
        if not schema_hints and "sql_schema_valid_tables" in context:
            valid_tables = context.get("sql_schema_valid_tables", [])
            schema_hints += "Valid tables in the database schema:\n"
            schema_hints += ", ".join(valid_tables) + "\n\n"
        
        # Add table replacements
        if "table_replacements" in context:
            replacements = context.get("table_replacements", {})
            schema_hints += "IMPORTANT TABLE MAPPING:\n"
            for non_existent, alternatives in replacements.items():
                schema_hints += f"- Table '{non_existent}' does not exist. Use {alternatives} instead.\n"
        
        # Substitute into the prompt template
        prompt = self.prompt_template.format(
            schema=schema_info,
            rules=rules_text,
            patterns=patterns_text,
            examples=examples_text,
            conversation_context=conversation_context,
            schema_hints=schema_hints,
            query=query
        )
        
        # Log detailed logging if enabled
        if self.enable_detailed_logging:
            logger.debug(f"Generated prompt (excerpt): {prompt[:500]}...")
        
        return prompt

    def generate_sql(self, query: str, examples: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SQL for a natural language query using OpenAI's API.
        
        Args:
            query: The natural language query text
            examples: Example queries and their SQL queries
            context: Additional context for the query
            
        Returns:
            A dictionary with the generated SQL and metadata
        """
        # Import schema information here to avoid circular imports
        from services.sql_generator.schema import get_database_schema, get_schema_hints
        
        # Special handling for "who placed those orders" type of follow-up queries
        is_who_query = False
        if context.get("is_followup", False) and "who" in query.lower() and any(term in query.lower() for term in ["placed", "those orders", "these orders", "the orders"]):
            is_who_query = True
            logger.info("Detected 'who placed those orders' follow-up query - applying special handling")
            
            # Get the time period from the previous query context
            time_period = context.get("time_period_clause", "")
            # Get status filter from previous query
            status_filter = None
            if "previous_filters" in context and "status" in context["previous_filters"]:
                status = context["previous_filters"]["status"]
                if status.lower() == "completed":
                    status_filter = "o.status = 7"
                elif status.lower() == "cancelled" or status.lower() == "canceled":
                    status_filter = "o.status = 6"
                elif status.lower() == "pending":
                    status_filter = "o.status IN (3, 4, 5)"
            
            # Check if we can directly build the SQL query rather than going through the AI
            if time_period:
                # If we have the time period, we can construct the SQL directly
                sql = f"""
SELECT 
    u.first_name || ' ' || u.last_name AS customer_name,
    COUNT(o.id) AS order_count
FROM 
    orders o
JOIN 
    users u ON o.customer_id = u.id
WHERE 
    o.location_id = 62
    {f"AND {status_filter}" if status_filter else ""}
    AND {time_period}
GROUP BY 
    u.first_name, u.last_name
ORDER BY 
    order_count DESC;
"""
                logger.info("Generated direct SQL for 'who placed orders' query using context information")
                return {
                    "sql": sql,
                    "error": None,
                    "generation_time": 0.01,
                    "model": "direct_template",
                    "tokens": 0
                }
        
        prompt = self._build_prompt(query, examples, context)
        
        # Add schema information to the prompt
        schema = get_database_schema()
        schema_hints = get_schema_hints()
        
        # Replace placeholders with actual schema
        prompt = prompt.replace("{schema}", schema)
        prompt = prompt.replace("{schema_hints}", schema_hints)
        
        # Fill in any remaining placeholders with empty strings
        prompt = prompt.replace("{patterns}", "")
        prompt = prompt.replace("{conversation_context}", context.get("conversation_context", ""))
        
        # If this is a followup query about who placed orders, add extra emphasis in the prompt
        if is_who_query:
            prompt += "\n\nIMPORTANT REMINDER: When retrieving customer information for orders:\n"
            prompt += "1. ALWAYS join orders to users using: orders o JOIN users u ON o.customer_id = u.id\n"
            prompt += "2. NEVER use 'user_id' for the join condition, ALWAYS use 'customer_id'\n"
            prompt += "3. ALWAYS maintain all time period and status filters from the previous query\n"
        
        # Debug log
        logger.debug(f"Generated SQL prompt:\n{prompt}")
        
        # Retry logic for OpenAI API calls
        max_attempts = 3
        delay = 2  # Starting delay in seconds
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Generating SQL with model: {self.model}, attempt: {attempt}/{max_attempts}")
                t1 = time.perf_counter()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a SQL expert that translates natural language into PostgreSQL queries."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                generation_time = time.perf_counter() - t1
                self.total_tokens += response.usage.total_tokens
                self.api_calls += 1
                self.total_latency += generation_time
                
                # Extract the SQL from the response
                sql_text = response.choices[0].message.content
                sql = self._extract_sql(sql_text)
                
                logger.info(f"Successfully generated SQL query in {generation_time:.2f} seconds")
                
                return {
                    "sql": sql,
                    "error": None,
                    "generation_time": generation_time,
                    "model": self.model,
                    "tokens": response.usage.total_tokens
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error generating SQL (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        # If we get here, all attempts failed
        logger.error(f"Failed to generate SQL after {max_attempts} attempts. Last error: {last_error}")
        return {
            "sql": None,
            "error": last_error,
            "generation_time": 0,
            "model": self.model,
            "tokens": 0
        }
    
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