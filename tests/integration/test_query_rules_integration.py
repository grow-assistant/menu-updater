"""
Tests for the integration between RulesService and SQL Generator.

This module tests the functionality of the RulesService working with
SQL files from the SQL Generator module.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from services.rules.rules_service import RulesService
from services.sql_generator.sql_example_loader import SQLExampleLoader


class TestQueryRulesIntegration:
    """Test suite for the integration between RulesService and SQL Generator."""
    
    @pytest.fixture
    def test_config(self) -> Dict[str, Any]:
        """Fixture providing test configuration."""
        return {
            "services": {
                "rules": {
                    "rules_path": "resources/rules",
                    "resources_dir": "resources",
                    "cache_ttl": 60,  # Short TTL for testing
                    "sql_files_path": "services/sql_generator/sql_files",  # Updated path
                    "query_rules_mapping": {
                        "menu": "menu_rules",
                        "order_history": "order_history_rules",
                        "ratings": "query_ratings_rules",
                        "performance": "query_performance_rules",
                    }
                },
                "sql_generator": {
                    "examples_path": "resources/sql_examples"
                }
            }
        }
    
    @pytest.fixture
    def rules_service(self, test_config) -> RulesService:
        """Fixture providing a RulesService instance."""
        return RulesService(test_config)
    
    @pytest.fixture
    def sql_example_loader(self) -> SQLExampleLoader:
        """Fixture providing a SQLExampleLoader instance."""
        return SQLExampleLoader()
    
    def test_load_sql_patterns_from_sql_generator(self, rules_service):
        """Test loading SQL patterns from the SQL Generator directory."""
        # Test loading patterns for menu queries
        patterns = rules.get_sql_patterns("menu")
        
        # Verify the structure
        assert isinstance(patterns, dict)
        assert "rules" in patterns
        assert "schema" in patterns
        assert "patterns" in patterns
        
        # There should be some patterns loaded
        assert len(patterns["patterns"]) > 0
    
    def test_query_rules_with_sql_files(self, rules_service):
        """Test that query rules can access SQL files from the SQL Generator."""
        # Get rules for the menu category
        menu_rules = rules.get_rules_and_examples("menu")
        
        # Verify query patterns are loaded
        assert "query_patterns" in menu_rules
        assert isinstance(menu_rules["query_patterns"], dict)
        assert len(menu_rules["query_patterns"]) > 0
        
        # Check that at least one pattern contains SQL
        assert any(isinstance(pattern, str) and "SELECT" in pattern 
                  for pattern in menu_rules["query_patterns"].values())
    
    def test_sql_pattern_integration(self, rules_service):
        """Test the integration between query rules and SQL patterns."""
        # Get a specific SQL pattern
        pattern = rules.get_sql_pattern("menu", "select_all_menu_items")
        
        # The pattern should be a non-empty string containing SQL
        assert isinstance(pattern, str)
        assert len(pattern) > 0
        assert "SELECT" in pattern
    
    def test_rules_service_with_sql_example_loader(self, rules_service, sql_example_loader):
        """Test the integration between RulesService and SQLExampleLoader."""
        # Get examples from the SQL example loader
        menu_examples = sql_example_loader.load_examples_for_query_type("menu")
        
        # Get rules from the rules service
        menu_rules = rules.get_rules_and_examples("menu")
        
        # Both should provide valid data structures
        assert isinstance(menu_examples, list)
        assert isinstance(menu_rules, dict)
        
        # If there are examples, verify their structure
        if menu_examples:
            assert "query" in menu_examples[0]
            assert "sql" in menu_examples[0]
        
        # If there are query patterns, verify their structure
        if "query_patterns" in menu_rules:
            assert isinstance(menu_rules["query_patterns"], dict)
            assert len(menu_rules["query_patterns"]) > 0 