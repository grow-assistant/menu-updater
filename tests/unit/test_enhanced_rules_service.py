"""
Unit tests for the enhanced RulesService.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.rules.rules_service import RulesService
from services.rules.yaml_loader import YamlLoader

@pytest.fixture
def mock_config():
    """Fixture for mock configuration."""
    return {
        "services": {
            "rules": {
                "rules_path": "test_rules",
                "resources_dir": "test_resources",
                "cache_ttl": 300  # 5 minutes
            }
        }
    }

@pytest.fixture
def mock_yaml_loader():
    """Fixture for mock YamlLoader."""
    loader = MagicMock(spec=YamlLoader)
    
    # Mock system rules
    loader.load_rules.return_value = {
        "rules": {
            "formatting": ["Use proper SQL formatting", "Capitalize SQL keywords"],
            "security": ["Avoid SQL injection", "Use parameterized queries"]
        }
    }
    
    # Mock SQL patterns
    loader.load_sql_patterns.return_value = {
        "rules": {"max_rows": 100},
        "schema": {
            "menu_items": {
                "columns": ["id", "name", "price", "category"]
            }
        },
        "patterns": {
            "get_menu_items": "SELECT * FROM menu_items",
            "get_item_by_id": "SELECT * FROM menu_items WHERE id = {id}"
        }
    }
    
    return loader

@pytest.fixture
def rules_service(mock_config, mock_yaml_loader):
    """Fixture for RulesService with mocked dependencies."""
    with patch("services.rules.rules_service.get_yaml_loader") as mock_get_loader:
        mock_get_loader.return_value = mock_yaml_loader
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("os.path.isdir") as mock_isdir:
                mock_isdir.return_value = True
                with patch("os.listdir") as mock_listdir:
                    mock_listdir.return_value = []
                    service = RulesService(mock_config)
                    return service

class TestEnhancedRulesService:
    """Tests for the enhanced RulesService."""
    
    def test_initialization(self, rules_service, mock_config):
        """Test service initialization."""
        assert rules_service.rules_path == mock_config["services"]["rules"]["rules_path"]
        assert rules_service.resources_dir == mock_config["services"]["rules"]["resources_dir"]
        assert rules_service.cache_ttl == mock_config["services"]["rules"]["cache_ttl"]
        assert isinstance(rules_service.cached_rules, dict)
        assert isinstance(rules_service.cache_timestamps, dict)
    
    def test_get_rules_and_examples_with_cache(self, rules_service):
        """Test getting rules with caching."""
        # Set up a cached rule
        category = "test_category"
        test_rules = {"sql_examples": ["SELECT * FROM test"], "response_rules": {"format": "table"}}
        rules_service.base_rules = {category: test_rules}
        
        # First call should process and cache
        result = rules_service.get_rules_and_examples(category)
        assert result == test_rules
        assert category in rules_service.cached_rules
        
        # Second call should use cache
        with patch.object(rules_service, "_process_rules_for_category") as mock_process:
            result2 = rules_service.get_rules_and_examples(category)
            assert result2 == test_rules
            mock_process.assert_not_called()
    
    def test_get_rules_and_examples_unknown_category(self, rules_service):
        """Test getting rules for unknown category."""
        result = rules_service.get_rules_and_examples("unknown_category")
        assert result == {"sql_examples": [], "response_rules": {}}
    
    def test_invalidate_cache_specific_category(self, rules_service):
        """Test invalidating cache for a specific category."""
        # Set up cached rules
        rules_service.cached_rules = {
            "category1": {"data": "test1"},
            "category2": {"data": "test2"}
        }
        rules_service.cache_timestamps = {
            "category1": 12345,
            "category2": 67890
        }
        
        # Invalidate one category
        rules_service.invalidate_cache("category1")
        
        # Check that only the specified category was removed
        assert "category1" not in rules_service.cached_rules
        assert "category1" not in rules_service.cache_timestamps
        assert "category2" in rules_service.cached_rules
        assert "category2" in rules_service.cache_timestamps
    
    def test_invalidate_cache_all_categories(self, rules_service):
        """Test invalidating cache for all categories."""
        # Set up cached rules
        rules_service.cached_rules = {
            "category1": {"data": "test1"},
            "category2": {"data": "test2"}
        }
        rules_service.cache_timestamps = {
            "category1": 12345,
            "category2": 67890
        }
        
        # Invalidate all categories
        rules_service.invalidate_cache()
        
        # Check that all categories were removed
        assert len(rules_service.cached_rules) == 0
        assert len(rules_service.cache_timestamps) == 0
    
    def test_get_sql_patterns(self, rules_service, mock_yaml_loader):
        """Test getting SQL patterns."""
        pattern_type = "menu"
        result = rules_service.get_sql_patterns(pattern_type)
        
        # Verify the loader was called with the correct pattern type
        mock_yaml_loader.load_sql_patterns.assert_called_once_with(pattern_type)
        
        # Verify the result matches the mock data
        assert result == mock_yaml_loader.load_sql_patterns.return_value
    
    def test_get_schema_for_type(self, rules_service):
        """Test getting schema for a specific type."""
        with patch.object(rules_service, "get_sql_patterns") as mock_get_patterns:
            mock_get_patterns.return_value = {
                "schema": {"test_table": {"columns": ["id", "name"]}}
            }
            
            result = rules_service.get_schema_for_type("test_type")
            assert result == {"test_table": {"columns": ["id", "name"]}}
    
    def test_get_sql_pattern(self, rules_service):
        """Test getting a specific SQL pattern."""
        with patch.object(rules_service, "get_sql_patterns") as mock_get_patterns:
            mock_get_patterns.return_value = {
                "patterns": {"test_pattern": "SELECT * FROM test"}
            }
            
            result = rules_service.get_sql_pattern("test_type", "test_pattern")
            assert result == "SELECT * FROM test"
    
    def test_format_rules_for_prompt(self, rules_service):
        """Test formatting rules for a prompt."""
        rules = {
            "formatting": ["Rule 1", "Rule 2"],
            "security": {"sql_injection": "Avoid it", "permissions": "Check them"}
        }
        
        result = rules_service.format_rules_for_prompt(rules)
        
        # Check that the result contains all the rules
        assert "FORMATTING:" in result
        assert "1. Rule 1" in result
        assert "2. Rule 2" in result
        assert "SECURITY:" in result
        assert "- sql_injection: Avoid it" in result
        assert "- permissions: Check them" in result
    
    def test_health_check_success(self, rules_service, mock_yaml_loader):
        """Test health check success."""
        result = rules_service.health_check()
        assert result is True
        mock_yaml_loader.load_rules.assert_called_with("system_rules")
    
    def test_health_check_failure(self, rules_service, mock_yaml_loader):
        """Test health check failure."""
        mock_yaml_loader.load_rules.side_effect = Exception("Test error")
        result = rules_service.health_check()
        assert result is False 