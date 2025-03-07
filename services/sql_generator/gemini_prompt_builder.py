"""
Gemini Prompt Builder for the SQL Generator Service.

This module provides functionality for building prompts for the Gemini API
to generate SQL queries from natural language.
"""

import logging
from typing import Dict, List, Any, Optional

from services.rules.rules_manager import RulesManager
from services.sql_generator.sql_example_loader import sql_example_loader

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

# Disable automatic initialization to prevent errors during testing
# rules_manager = RulesManager(config={})

class GeminiPromptBuilder:
    """
    Builds prompts for the Gemini API to generate SQL queries.
    """
    
    def __init__(self):
        """Initialize the Gemini Prompt Builder."""
        self.rules_manager = None  # Will be initialized when needed
    
    def build_prompt(
        self, 
        query: str, 
        query_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build a prompt for the Gemini API to generate a SQL query.
        
        Args:
            query: The natural language query
            query_type: The type of query (e.g., 'menu', 'order_history')
            additional_context: Additional context for the prompt
            
        Returns:
            Dictionary containing the prompt and related metadata
        """
        # Get rules for this query type
        rules = self.rules_manager.get_rules_for_query_type(query_type)
        
        # Get SQL examples for this query type
        examples = sql_example_loader.get_formatted_examples(query_type)
        
        # Extract SQL schema information if available in the rules
        schema_info = ""
        if "schema" in rules:
            schema_info = "Database Schema:\n"
            for table_name, fields in rules["schema"].items():
                schema_info += f"Table: {table_name}\n"
                for field_name, field_type in fields.items():
                    schema_info += f"  - {field_name}: {field_type}\n"
        
        # Extract query rules if available
        query_rules = ""
        if "query_rules" in rules:
            query_rules = "Query Rules:\n"
            # Handle nested structure of query_rules
            for category, category_rules in rules["query_rules"].items():
                query_rules += f"Category: {category}\n"
                if isinstance(category_rules, dict):
                    for rule_name, rule_desc in category_rules.items():
                        query_rules += f"  - {rule_name}: {rule_desc}\n"
                else:
                    query_rules += f"  - {category_rules}\n"
        
        # Extract SQL patterns if available
        sql_patterns = ""
        if "sql_patterns" in rules:
            sql_patterns = "SQL Patterns:\n"
            for pattern_name, pattern in rules["sql_patterns"].items():
                # Truncate long patterns for the prompt
                if len(pattern) > 300:
                    pattern = pattern[:300] + "...[truncated]"
                sql_patterns += f"Pattern '{pattern_name}':\n{pattern}\n\n"
        
        # Build the system prompt
        system_prompt = f"""You are a PostgreSQL expert that translates natural language questions into SQL queries.
Follow these guidelines:
1. Only return valid PostgreSQL queries.
2. Use appropriate table and column names as defined in the schema.
3. Follow all query rules provided.
4. Include helpful comments in your SQL to explain your reasoning.
5. Format your SQL query properly with line breaks and indentation for readability.
6. Do not include any explanations outside of comments within the SQL.
7. Only return the SQL query, nothing else.

{schema_info}

{query_rules}

{sql_patterns}

Here are some examples of questions and their corresponding SQL queries:

{examples}
"""

        # Build the user prompt (the query)
        user_prompt = f"Generate a PostgreSQL query for the following question: {query}"
        
        # Return the prompt data
        prompt_data = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "query_type": query_type,
            "examples_count": examples.count("Example ") if examples else 0,
        }
        
        logger.info(f"Built prompt for query type '{query_type}', examples count: {prompt_data['examples_count']}")
        
        return prompt_data


# Singleton instance
gemini_prompt_builder = GeminiPromptBuilder()
