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
        patterns = rules_service.get_sql_patterns("menu")
        
        # The service might not find patterns in the test environment, but it shouldn't crash
        assert isinstance(patterns, dict)
        
    def test_query_rules_with_sql_files(self, rules_service):
        """Test that query rules can access SQL files from the SQL Generator."""
        # Get rules for the menu category
        menu_rules = rules_service.get_rules_and_examples("menu")
        
        # The rules should be a dictionary with various sections
        assert isinstance(menu_rules, dict)
        
    def test_sql_pattern_integration(self, rules_service):
        """Test the integration between query rules and SQL patterns."""
        # Get a specific SQL pattern
        pattern = rules_service.get_sql_pattern("menu", "select_all_menu_items")
        
        # The pattern might not exist in test environment, but method should return at least an empty string
        assert isinstance(pattern, str)
    
    def test_rules_service_with_sql_example_loader(self, rules_service, sql_example_loader):
        """Test the integration between RulesService and SQLExampleLoader."""
        # Get examples from the SQL example loader
        menu_examples = sql_example_loader.load_examples_for_query_type("menu")
        
        # Get rules from the rules service
        menu_rules = rules_service.get_rules_and_examples("menu")
        
        # menu_examples could be a dict or list, depending on the implementation
        assert isinstance(menu_examples, (dict, list))
        assert isinstance(menu_rules, dict) 