"""
SQL Generator Service for the Swoop AI application.

This package provides functionality for generating SQL queries from natural language
using either OpenAI or Gemini APIs with example-based prompting techniques.
"""

from services.sql_generator.sql_generator import SQLGenerator, sql_generator
from services.sql_generator.gemini_prompt_builder import GeminiPromptBuilder
from services.sql_generator.sql_example_loader import SQLExampleLoader
from services.sql_generator.prompt_builder import SQLPromptBuilder, sql_prompt_builder
from services.sql_generator.openai_sql_generator import OpenAISQLGenerator
from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
from services.sql_generator.sql_generator_factory import SQLGeneratorFactory

__all__ = [
    "SQLGenerator", 
    "sql_generator", 
    "GeminiPromptBuilder", 
    "SQLExampleLoader", 
    "SQLPromptBuilder", 
    "sql_prompt_builder",
    "OpenAISQLGenerator",
    "GeminiSQLGenerator",
    "SQLGeneratorFactory"
]
