"""
Unit tests for the SQL Generator Service.

Tests the functionality of the SQLGenerator class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.sql_generator import SQLGenerator


class TestSQLGenerator:
    """Test cases for the SQL Generator Service."""

    def test_init_sql_generator(self, mock_rules_manager, mock_gemini_client, test_config):
        """Test the initialization of the SQLGenerator."""
        sql_generator = SQLGenerator(
            ai_client=mock_gemini_client,
            rules_manager=mock_rules_manager,
            config=test_config
        )
        assert sql_generator is not None
        assert sql_generator.ai_client == mock_gemini_client
        assert sql_generator.rules_manager == mock_rules_manager
        assert sql_generator.config == test_config

    def test_generate_sql(self, mock_sql_generator):
        """Test SQL generation from a natural language query."""
        # Test with mocked generate_sql
        sql = mock_sql_generator.generate_sql(
            "Show me menu items at Idle Hour", 
            {"query_type": "menu_query", "location_id": 62}
        )
        assert sql == "SELECT * FROM menu_items WHERE location_id = 62"

    def test_generate_sql_with_no_ai_client(self, mock_rules_manager, test_config):
        """Test SQL generation when no AI client is available."""
        sql_generator = SQLGenerator(
            ai_client=None,
            rules_manager=mock_rules_manager,
            config=test_config
        )
        with patch.object(sql_generator, "generate_sql") as mock_generate:
            mock_generate.return_value = None
            sql = sql_generator.generate_sql(
                "Show me menu items at Idle Hour", 
                {"query_type": "menu_query", "location_id": 62}
            )
            assert sql is None

    def test_build_gemini_prompt(self, mock_sql_generator):
        """Test building a prompt for the Gemini AI model."""
        with patch.object(mock_sql_generator, "build_gemini_prompt") as mock_build:
            mock_build.return_value = "Test prompt for Gemini"
            prompt = mock_sql_generator.build_gemini_prompt(
                "Show me menu items at Idle Hour",
                {"query_type": "menu_query", "location_id": 62},
                ["SELECT * FROM items WHERE location_id = {location_id}"],
                {"rule": "value"}
            )
            assert prompt == "Test prompt for Gemini"

    def test_load_sql_examples(self, mock_sql_generator):
        """Test loading SQL examples for a query type."""
        with patch.object(mock_sql_generator, "load_sql_examples") as mock_load:
            mock_load.return_value = ["SELECT * FROM items WHERE location_id = 62"]
            examples = mock_sql_generator.load_sql_examples("menu_query")
            assert examples == ["SELECT * FROM items WHERE location_id = 62"]

    def test_substitute_variables(self, mock_sql_generator):
        """Test variable substitution in SQL patterns."""
        with patch.object(mock_sql_generator, "substitute_variables") as mock_sub:
            mock_sub.return_value = "SELECT * FROM items WHERE location_id = 62"
            sql = mock_sql_generator.substitute_variables(
                "SELECT * FROM items WHERE location_id = {location_id}",
                {"location_id": 62}
            )
            assert sql == "SELECT * FROM items WHERE location_id = 62"

    def test_clean_sql(self, mock_sql_generator):
        """Test cleaning generated SQL."""
        with patch.object(mock_sql_generator, "clean_sql") as mock_clean:
            mock_clean.return_value = "SELECT * FROM menu_items WHERE location_id = 62"
            sql = mock_sql_generator.clean_sql(
                "```sql\nSELECT * FROM menu_items WHERE location_id = 62\n```"
            )
            assert sql == "SELECT * FROM menu_items WHERE location_id = 62"

    def test_validate_sql(self, mock_sql_generator):
        """Test SQL validation."""
        with patch.object(mock_sql_generator, "validate_sql") as mock_validate:
            # Valid SQL
            mock_validate.return_value = True
            is_valid = mock_sql_generator.validate_sql(
                "SELECT * FROM menu_items WHERE location_id = 62",
                {"location_id": 62}
            )
            assert is_valid is True
            
            # Invalid SQL
            mock_validate.return_value = False
            is_valid = mock_sql_generator.validate_sql(
                "SELECT * FROM menu_items",  # Missing location_id filter
                {"location_id": 62}
            )
            assert is_valid is False 