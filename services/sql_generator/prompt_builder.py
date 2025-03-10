"""
SQL Prompt Builder

This module provides functionality for building SQL generation prompts
using templates and SQL patterns.
"""

import os
from typing import Dict, Any, List, Optional
import yaml

from services.utils.prompt_loader import PromptLoader, get_prompt_loader
from services.rules.yaml_loader import YamlLoader
from services.utils.logging import get_logger

logger = get_logger(__name__)

class SQLPromptBuilder:
    """
    Builds prompts for SQL generation using templates and SQL patterns.
    """
    
    def __init__(self, config=None):
        """
        Initialize the SQL Prompt Builder.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.prompt_loader = PromptLoader()
        
        # Path configurations - pointing to existing directories
        self.patterns_path = self.config.get("patterns_path", "services/sql_generator/sql_files")
        self.examples_path = self.config.get("examples_path", "services/sql_generator/sql_files")
        
        # Load SQL patterns and examples
        self.patterns = self.load_sql_patterns()
        self.examples = self.load_sql_examples()
        
        logger.info("SQLPromptBuilder initialized")
    
    def load_sql_patterns(self):
        """
        Load SQL patterns from YAML files.
        
        Returns:
            Dictionary of patterns by domain
        """
        patterns = {}
        
        try:
            yaml_loader = YamlLoader()
            patterns_dir = os.path.join(os.getcwd(), self.patterns_path)
            
            # Load each YAML file in the patterns directory
            for filename in os.listdir(patterns_dir):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    file_path = os.path.join(patterns_dir, filename)
                    domain = os.path.splitext(filename)[0]
                    patterns[domain] = yaml_loader.load_yaml_file(file_path)
                    logger.info(f"Loaded SQL patterns for domain: {domain}")
            
            return patterns
        except Exception as e:
            logger.error(f"Error loading SQL patterns: {str(e)}")
            return {}
    
    def load_sql_examples(self) -> Dict[str, List[str]]:
        """
        Load SQL examples from text files.
        
        Returns:
            Dictionary of examples by query type
        """
        examples = {}
        
        try:
            examples_dir = os.path.join(os.getcwd(), self.examples_path)
            
            # Load each text file in the examples directory
            for filename in os.listdir(examples_dir):
                if filename.endswith('.txt') or filename.endswith('.sql'):
                    file_path = os.path.join(examples_dir, filename)
                    query_type = os.path.splitext(filename)[0]
                    
                    with open(file_path, 'r') as file:
                        examples[query_type] = [line.strip() for line in file.readlines() if line.strip()]
                    
                    logger.info(f"Loaded SQL examples for query type: {query_type}")
            
            return examples
        except Exception as e:
            logger.error(f"Error loading SQL examples: {str(e)}")
            return {}
    
    def build_sql_prompt(self, query_type: str, query_params: Dict[str, Any]) -> Dict[str, str]:
        """
        Build a prompt for SQL generation based on query type and parameters.
        
        Args:
            query_type: Type of query (e.g., 'menu_query', 'update_price', etc.)
            query_params: Parameters for the query
            
        Returns:
            Dictionary with system and user prompt components
        """
        logger.info(f"Building SQL prompt for query type: {query_type}")
        
        # Get the domain for this query type
        domain = self._get_domain_for_query_type(query_type)
        
        # Load the system prompt template
        system_prompt = self.prompt_loader.load_template("sql_system")
        
        # Add domain-specific patterns if available
        domain_patterns = self.patterns.get(domain, {})
        pattern_str = yaml.dump(domain_patterns, default_flow_style=False)
        
        # Add examples for this query type if available
        examples_str = "\n".join(self.examples.get(query_type, []))
        
        # Format the system prompt
        system_prompt = system_prompt.format(
            patterns=pattern_str,
            examples=examples_str
        )
        
        # Format the user prompt with the query parameters
        user_prompt = self._format_user_prompt(query_type, query_params)
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _get_domain_for_query_type(self, query_type: str) -> str:
        """
        Map a query type to its domain.
        
        Args:
            query_type: Type of query
            
        Returns:
            Domain name
        """
        # Mapping of query types to domains
        domain_mapping = {
            "menu_query": "restaurant",
            "order_history": "restaurant",
            "query_menu": "restaurant",
            "query_performance": "restaurant",
            "query_ratings": "restaurant",
            "update_price": "restaurant",
            "enable_item": "restaurant",
            "disable_item": "restaurant",
            "general_question": "general"
        }
        
        return domain_mapping.get(query_type, "general")
    
    def _format_user_prompt(self, query_type: str, query_params: Dict[str, Any]) -> str:
        """
        Format the user prompt with query parameters.
        
        Args:
            query_type: Type of query
            query_params: Parameters for the query
            
        Returns:
            Formatted user prompt string
        """
        # Standard parameters
        query = query_params.get('query', '')
        parsed_info = query_params.get('parsed_info', {})
        
        prompt = f"Query type: {query_type}\n"
        prompt += f"User query: {query}\n\n"
        
        # Add parsed information if available
        if parsed_info:
            prompt += "Parsed information:\n"
            prompt += self._format_params(parsed_info)
        
        # Add specific instructions based on query type
        if query_type in ["update_price", "disable_item", "enable_item"]:
            prompt += "\nThis is a mutation query. Generate SQL to update the database."
        elif query_type in ["menu_query", "order_history", "query_performance", "query_ratings"]:
            prompt += "\nThis is a read query. Generate SQL to retrieve information."
        
        # Add time-based defaults for order queries
        if 'order' in query_type.lower() or 'order' in query.lower():
            prompt += "\nIMPORTANT: For time-based queries, follow these rules:"
            prompt += "\n- Interpret time expressions precisely as follows:"
            prompt += "\n  * 'in the last week/month/quarter/year' means a ROLLING time period (e.g., 'in the last month' = the last 30 days from today)"
            prompt += "\n  * 'last week/month/quarter/year' means the PREVIOUS COMPLETE time period (e.g., 'last month' = the full previous calendar month)"
            prompt += "\n  * 'this week/month/quarter/year' means the CURRENT PARTIAL time period (e.g., 'this month' = month-to-date)"
            prompt += "\n- Use explicit date ranges with PostgreSQL date functions in your WHERE clause"
            prompt += "\n- For rolling periods, use: current_date - interval '30 days' for 'in the last month'"
            prompt += "\n- For previous complete periods, use: date_trunc('month', current_date - interval '1 month')"
            prompt += "\n- For current partial periods, use: date_trunc('month', current_date)"
            prompt += "\n- Always include both start AND end dates in your BETWEEN clauses"
            
            # Add location filtering instruction for order queries
            prompt += "\n\nCRITICAL: Location filtering requirement"
            prompt += "\n- Every query on the orders table MUST filter by location_id"
            prompt += "\n- Use: o.location_id = 62 (exact value, not a placeholder)"
            prompt += "\n- This is a security requirement for data isolation"
        
        return prompt
    
    def _format_params(self, params: Dict[str, Any]) -> str:
        """
        Format parameters as a string.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Formatted parameter string
        """
        result = ""
        for key, value in params.items():
            if isinstance(value, dict):
                result += f"{key}:\n"
                for inner_key, inner_value in value.items():
                    result += f"  {inner_key}: {inner_value}\n"
            else:
                result += f"{key}: {value}\n"
        
        return result


# Create a singleton instance
sql_prompt_builder = SQLPromptBuilder() 