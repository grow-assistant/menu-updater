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
        assert rules.yaml_loader is not None
        assert isinstance(rules.yaml_loader, YamlLoader)
        assert rules.query_rules_modules is not None
        
    def test_load_rules(self, rules_service):
        """Test that rules are loaded correctly."""
        # Force a reload
        rules.load_rules()
        
        # Check that some rules were loaded
        assert hasattr(rules_service, 'base_rules')
        assert hasattr(rules_service, 'system_rules')
        assert hasattr(rules_service, 'business_rules')
    
    def test_load_query_rules_modules(self, rules_service):
        """Test that query rules modules are loaded correctly."""
        # The service should have loaded some modules
        assert len(rules.query_rules_modules) > 0
        
        # Check for specific expected modules
        assert "menu_rules" in rules.query_rules_modules
        
        # Verify the module has the expected interface
        module = rules.query_rules_modules["menu_rules"]
        assert hasattr(module, "get_rules")
        assert callable(module.get_rules)
    
    def test_get_rules_and_examples(self, rules_service):
        """Test retrieving rules and examples for a specific category."""
        # Get rules for the menu category
        menu_rules = rules.get_rules_and_examples("menu")
        
        # Verify the structure
        assert isinstance(menu_rules, dict)
        
        # The rules should contain some of these keys
        possible_keys = ["sql_examples", "response_rules", "query_rules", "schema", "query_patterns"]
        assert any(key in menu_rules for key in possible_keys)
        
        # If query_rules exist, check their structure
        if "query_rules" in menu_rules:
            assert isinstance(menu_rules["query_rules"], dict)
            
        # If schema exists, check its structure
        if "schema" in menu_rules:
            assert isinstance(menu_rules["schema"], dict)
            
        # If query_patterns exist, check their structure
        if "query_patterns" in menu_rules:
            assert isinstance(menu_rules["query_patterns"], dict)
    
    def test_caching(self, rules_service):
        """Test that rules are cached correctly."""
        # Get rules for the first time
        menu_rules_1 = rules.get_rules_and_examples("menu")
        
        # Verify it's in the cache
        assert "menu" in rules.cached_rules
        assert "menu" in rules.cache_timestamps
        
        # Get the same rules again
        menu_rules_2 = rules.get_rules_and_examples("menu")
        
        # Verify it's the same object (cached)
        assert menu_rules_1 is menu_rules_2
        
        # Invalidate the cache
        rules.invalidate_cache("menu")
        
        # Verify it's no longer in the cache
        assert "menu" not in rules.cached_rules
        
        # Get the rules again
        menu_rules_3 = rules.get_rules_and_examples("menu")
        
        # Verify it's a different object
        assert menu_rules_1 is not menu_rules_3
    
    def test_get_sql_patterns(self, rules_service):
        """Test retrieving SQL patterns."""
        # Try to get patterns for the menu category
        menu_patterns = rules.get_sql_patterns("menu")
        
        # Verify the structure
        assert isinstance(menu_patterns, dict)
        assert "rules" in menu_patterns
        assert "schema" in menu_patterns
        assert "patterns" in menu_patterns
    
    @pytest.mark.parametrize("pattern_type", ["menu", "order_history"])
    def test_get_schema_for_type(self, rules_service, pattern_type):
        """Test retrieving schema for a specific type."""
        # Get schema for the specified type
        schema = rules.get_schema_for_type(pattern_type)
        
        # Verify the structure
        assert isinstance(schema, dict)
    
    def test_sql_pattern_loading_from_directory(self):
        """Test loading SQL patterns from a directory."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup resources structure
            resources_dir = Path(temp_dir) / "resources"
            sql_patterns_dir = resources_dir / "sql_patterns" / "test_patterns"
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
                    },
                    "sql_generator": {
                        "examples_path": str(resources_dir / "sql_examples")
                    }
                }
            }
            
            # Create the rules service
            rules_service = RulesService(config)
            
            # Test loading the patterns
            patterns = rules.load_sql_patterns_from_directory(
                "test_patterns",
                {"test_pattern.sql": "test_pattern"},
                {"default_pattern": "SELECT 1;"}
            )
            
            # Verify the loaded patterns
            assert "test_pattern" in patterns
            assert patterns["test_pattern"].strip() == "SELECT * FROM test_table WHERE id = {test_id};"
            assert "default_pattern" in patterns
            assert patterns["default_pattern"] == "SELECT 1;"
    
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
        result = rules.replace_placeholders(patterns, replacements)
        
        # Verify the replacements
        assert result["test1"] == "SELECT * FROM users WHERE id = 123;"
        assert result["test2"] == "SELECT * FROM orders WHERE status = completed AND location_id = 62;"
    
    def test_health_check(self, rules_service):
        """Test the health check functionality."""
        # The health check should pass
        assert rules.health_check() is True
