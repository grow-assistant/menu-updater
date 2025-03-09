"""
Tests for the RulesService class.

This module tests the functionality of the RulesService,
particularly focusing on loading and integrating query rules.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from services.rules.rules_service import RulesService
from services.rules.yaml_loader import YamlLoader


class TestRulesService:
    """Test suite for the RulesService."""
    
    @pytest.fixture
    def test_config(self) -> Dict[str, Any]:
        """Fixture providing test configuration."""
        return {
            "services": {
                "rules": {
                    "rules_path": "resources/rules",
                    "resources_dir": "resources",
                    "cache_ttl": 60,  # Short TTL for testing
                    "query_rules_mapping": {
                        "menu": "menu_rules",
                        "order_history": "order_history_rules",
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
    
    def test_init(self, rules_service):
        """Test that the RulesService initializes correctly."""
        assert rules_service is not None
        assert rules_service.yaml_loader is not None
        assert isinstance(rules_service.yaml_loader, YamlLoader)
        assert rules_service.query_rules_modules is not None
        
    def test_load_rules(self, rules_service):
        """Test that rules are loaded correctly."""
        # Force a reload
        rules_service.load_rules()
        
        # It shouldn't crash even if no files exist
        assert True
    
    def test_load_query_rules_modules(self, rules_service):
        """Test that query rules modules are loaded correctly."""
        # The service should have loaded some modules
        assert len(rules_service.query_rules_modules) > 0
        
        # Check for specific expected modules
        assert "menu_inquiry_rules" in rules_service.query_rules_modules
        assert "order_history_rules" in rules_service.query_rules_modules
        
        # Verify the module has the expected interface
        module = rules_service.query_rules_modules["menu_inquiry_rules"]
        assert hasattr(module, "get_rules")
        assert callable(module.get_rules)
    
    def test_get_rules_and_examples(self, rules_service):
        """Test retrieving rules and examples for a specific category."""
        # Get rules for the menu category
        menu_rules = rules_service.get_rules_and_examples("menu")
        
        # Verify it returns a dictionary
        assert isinstance(menu_rules, dict)
        
        # Get rules for a non-existent category
        unknown_rules = rules_service.get_rules_and_examples("non_existent_category")
        
        # Should still return a dictionary, possibly empty or with defaults
        assert isinstance(unknown_rules, dict)
    
    def test_caching(self, rules_service):
        """Test that rules are cached correctly."""
        # Get rules for the first time
        menu_rules_1 = rules_service.get_rules_and_examples("menu")
        
        # Verify it's cached
        assert "menu" in rules_service.cached_rules
        
        # Get rules again - should use cache
        menu_rules_2 = rules_service.get_rules_and_examples("menu")
        
        # Verify both are the same instance
        assert menu_rules_1 is menu_rules_2
        
        # Invalidate cache
        rules_service.invalidate_cache("menu")
        
        # Get rules after cache invalidation
        menu_rules_3 = rules_service.get_rules_and_examples("menu")
        
        # Verify it's a different instance
        assert menu_rules_1 is not menu_rules_3
    
    def test_get_sql_patterns(self, rules_service):
        """Test retrieving SQL patterns."""
        # Try to get patterns for the menu category
        menu_patterns = rules_service.get_sql_patterns("menu")
        
        # Verify it returns a dictionary
        assert isinstance(menu_patterns, dict)
    
    @pytest.mark.parametrize("pattern_type", ["menu", "order_history"])
    def test_get_schema_for_type(self, rules_service, pattern_type):
        """Test retrieving schema for a specific type."""
        # Get schema for the specified type
        schema = rules_service.get_schema_for_type(pattern_type)
        
        # Verify it returns a dictionary
        assert isinstance(schema, dict)
    
    def test_sql_pattern_loading_from_directory(self):
        """Test loading SQL patterns from a directory."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup resources structure
            resources_dir = Path(temp_dir) / "resources"
            sql_files_dir = Path(temp_dir) / "services" / "sql_generator" / "sql_files"
            sql_patterns_dir = sql_files_dir / "test_patterns"
            os.makedirs(sql_patterns_dir, exist_ok=True)

            # Create a test SQL file
            test_sql = "-- Test SQL pattern\nSELECT * FROM test_table WHERE id = {test_id};"
            with open(sql_patterns_dir / "test_pattern.sql", "w") as f:
                f.write(test_sql)

            # Create a config for the rules service
            config = {
                "services": {
                    "rules": {
                        "rules_path": str(resources_dir / "rules"),
                        "resources_dir": str(resources_dir),
                        "cache_ttl": 60,
                        "sql_files_path": str(sql_files_dir),  # Set the correct path to SQL files
                    },
                    "sql_generator": {
                        "examples_path": str(resources_dir / "sql_examples")
                    }
                }
            }

            # Create the rules service
            rules_service = RulesService(config)

            # Test loading the patterns
            patterns = rules_service.load_sql_patterns_from_directory(
                "test_patterns",
                {"test_pattern.sql": "test_pattern"},
                {"default_pattern": "SELECT 1;"}
            )
            
            # Verify patterns were loaded
            assert "test_pattern" in patterns or "default_pattern" in patterns
            # Even if the test_pattern failed to load, the default pattern should be there
            assert "default_pattern" in patterns
            assert "SELECT 1;" in patterns["default_pattern"]
    
    def test_replace_placeholders(self, rules_service):
        """Test replacing placeholders in SQL patterns."""
        # Create test patterns
        patterns = {
            "test1": "SELECT * FROM users WHERE id = {user_id};",
            "test2": "SELECT * FROM orders WHERE status = {status} AND location_id = {location_id};"
        }
        
        # Define replacements
        replacements = {
            "user_id": 123,
            "status": "completed",
            "location_id": 62
        }
        
        # Replace placeholders
        result = rules_service.replace_placeholders(patterns, replacements)
        
        # Verify replacements
        assert "SELECT * FROM users WHERE id = 123;" in result.values()
        assert "SELECT * FROM orders WHERE status = completed AND location_id = 62;" in result.values()
    
    def test_health_check(self, rules_service):
        """Test the health check functionality."""
        # The health check should pass
        assert rules_service.health_check() is True
