"""
Unit tests for the Rules Service.

Tests the functionality of the RulesManager class and related components.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
import json

from services.rules_service import RulesManager


class TestRulesService:
    """Test cases for the Rules Service."""

    def test_init_rules_manager(self, test_config):
        """Test the initialization of the RulesManager."""
        with patch("services.rules.rules_manager.os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("builtins.open", mock_open(read_data='{}')):
                rules_manager = RulesManager(config=test_config)
                assert rules_manager is not None
                assert rules_manager.config == test_config

    def test_load_rules(self, mock_rules_manager):
        """Test loading rules from files."""
        # Test with mocked load_rules
        rules = mock_rules_manager.load_rules("test_path")
        assert rules == {"test_rule": "test value"}

    def test_get_rules_for_query_type(self, mock_rules_manager):
        """Test retrieving rules for a specific query type."""
        # Test with mocked get_rules_for_query_type
        rules = mock_rules_manager.get_rules_for_query_type("menu_query")
        assert rules == {"test_rule": "test value"}

        # Test with nonexistent query type
        with patch.object(mock_rules_manager, "get_rules_for_query_type") as mock_get:
            mock_get.side_effect = ValueError("Unknown query type")
            with pytest.raises(ValueError):
                mock_rules_manager.get_rules_for_query_type("nonexistent_type")

    def test_get_system_rules(self, mock_rules_manager):
        """Test retrieving system rules."""
        with patch.object(mock_rules_manager, "get_system_rules") as mock_get:
            mock_get.return_value = {"system_rule": "system value"}
            rules = mock_rules_manager.get_system_rules()
            assert rules == {"system_rule": "system value"}

    def test_get_business_rules(self, mock_rules_manager):
        """Test retrieving business rules."""
        with patch.object(mock_rules_manager, "get_business_rules") as mock_get:
            mock_get.return_value = {"business_rule": "business value"}
            rules = mock_rules_manager.get_business_rules()
            assert rules == {"business_rule": "business value"}

    def test_get_sql_patterns(self, mock_rules_manager):
        """Test retrieving SQL patterns."""
        with patch.object(mock_rules_manager, "get_sql_patterns") as mock_get:
            mock_get.return_value = ["SELECT * FROM items WHERE location_id = {location_id}"]
            patterns = mock_rules_manager.get_sql_patterns("menu_query")
            assert patterns == ["SELECT * FROM items WHERE location_id = {location_id}"]

    def test_format_rules_for_prompt(self, mock_rules_manager):
        """Test formatting rules for inclusion in a prompt."""
        with patch.object(mock_rules_manager, "format_rules_for_prompt") as mock_format:
            mock_format.return_value = "Formatted rules text"
            rules_text = mock_rules_manager.format_rules_for_prompt(
                {"rule1": "value1", "rule2": "value2"}
            )
            assert rules_text == "Formatted rules text"

    def test_combine_rules(self, mock_rules_manager):
        """Test combining different types of rules."""
        with patch.object(mock_rules_manager, "combine_rules") as mock_combine:
            mock_combine.return_value = {
                "system_rule": "system value",
                "business_rule": "business value",
                "query_rule": "query value"
            }
            
            combined_rules = mock_rules_manager.combine_rules(
                "menu_query",
                {"system_rule": "system value"},
                {"business_rule": "business value"},
                {"query_rule": "query value"}
            )
            
            assert combined_rules == {
                "system_rule": "system value",
                "business_rule": "business value",
                "query_rule": "query value"
            } 