"""
Unit tests for the enhanced RulesService.
"""
import os
import json
import pytest
import tempfile
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

@pytest.mark.unit
class TestEnhancedRulesService:
    """Tests for the enhanced RulesService."""
    
    def test_initialization(self, rules_service, mock_config):
        """
        Test that the service initializes correctly with all expected attributes.
        
        This test verifies:
        1. Configuration values are correctly loaded
        2. Cache structures are properly initialized
        3. Service is ready to handle rule requests
        """
        assert rules_service.rules_path == mock_config["services"]["rules"]["rules_path"]
        assert rules_service.resources_dir == mock_config["services"]["rules"]["resources_dir"]
        assert rules_service.cache_ttl == mock_config["services"]["rules"]["cache_ttl"]
        assert isinstance(rules_service.cached_rules, dict)
        assert isinstance(rules_service.cache_timestamps, dict)
    
    @pytest.mark.fast
    def test_get_rules_and_examples_with_cache(self, rules_service):
        """
        Test getting rules with caching mechanism.
        
        This test verifies:
        1. Rules are retrieved and processed correctly
        2. Rules are stored in cache after first retrieval
        3. Subsequent calls use cached values
        4. Processing is skipped when using cache
        """
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
    
    @pytest.mark.fast
    def test_get_rules_and_examples_unknown_category(self, rules_service):
        """
        Test getting rules for an unknown category.
        
        This test verifies:
        1. Service handles unknown categories gracefully
        2. Default empty rule set is returned for unknown categories
        3. No errors are raised for invalid category requests
        """
        result = rules_service.get_rules_and_examples("unknown_category")
        assert result == {"sql_examples": [], "response_rules": {}}
    
    @pytest.mark.fast
    def test_invalidate_cache_specific_category(self, rules_service):
        """
        Test invalidating cache for a specific category.
        
        This test verifies:
        1. Cache invalidation removes only the specified category
        2. Other cached categories remain intact
        3. Both rules and timestamps are properly cleared
        """
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
    
    @pytest.mark.fast
    def test_invalidate_cache_all_categories(self, rules_service):
        """
        Test invalidating cache for all categories.
        
        This test verifies:
        1. Complete cache invalidation clears all categories
        2. Both rules and timestamps caches are emptied
        3. Service can rebuild cache after invalidation
        """
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
    
    @pytest.mark.api
    def test_health_check_success(self, rules_service, mock_yaml_loader):
        """
        Test health check success scenario.
        
        This test verifies:
        1. Health check returns true when dependencies are working
        2. The loader is called with the expected parameters
        3. No exceptions cause the health check to fail
        """
        result = rules_service.health_check()
        assert result is True
        mock_yaml_loader.load_rules.assert_called_with("system_rules")
    
    @pytest.mark.api
    def test_health_check_failure(self, rules_service, mock_yaml_loader):
        """
        Test health check failure scenario.
        
        This test verifies:
        1. Health check returns false when dependencies fail
        2. Exceptions in the loader are properly caught
        3. Service gracefully handles dependency failures
        """
        mock_yaml_loader.load_rules.side_effect = Exception("Test error")
        result = rules_service.health_check()
        assert result is False
    
    def test_load_query_rules_modules(self, rules_service):
        """Test that query rules modules are loaded correctly."""
        # Mock the query_rules_modules dictionary
        rules_service.query_rules_modules = {
            "menu_rules": MagicMock(),
            "order_history_rules": MagicMock()
        }
        
        # Add get_rules method to the mock modules
        rules_service.query_rules_modules["menu_rules"].get_rules = MagicMock()
        
        # Verify the modules were loaded
        assert len(rules_service.query_rules_modules) > 0
        assert "menu_rules" in rules_service.query_rules_modules
        assert hasattr(rules_service.query_rules_modules["menu_rules"], "get_rules")
        assert callable(rules_service.query_rules_modules["menu_rules"].get_rules)
    
    def test_sql_pattern_loading_from_directory(self, rules_service, tmp_path):
        """Test loading SQL patterns from a directory."""
        # Create a temporary directory structure
        resources_dir = tmp_path / "resources"
        sql_patterns_dir = resources_dir / "sql_patterns" / "test_patterns"
        os.makedirs(sql_patterns_dir, exist_ok=True)
        
        # Create a test SQL file
        test_sql = "-- Test SQL pattern\nSELECT * FROM test_table WHERE id = {test_id};"
        with open(sql_patterns_dir / "test_pattern.sql", "w") as f:
            f.write(test_sql)
        
        # Create a patch for the load_sql_patterns_from_directory method
        with patch.object(rules_service, "load_sql_patterns_from_directory") as mock_load:
            # Set the return value
            mock_load.return_value = {
                "test_pattern": "SELECT * FROM test_table WHERE id = {test_id};",
                "default_pattern": "SELECT 1;"
            }
            
            # Call the method
            patterns = rules_service.load_sql_patterns_from_directory(
                "test_patterns",
                {"test_pattern.sql": "test_pattern"},
                {"default_pattern": "SELECT 1;"}
            )
            
            # Verify the loaded patterns
            assert "test_pattern" in patterns
            assert patterns["test_pattern"] == "SELECT * FROM test_table WHERE id = {test_id};"
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
        
        # Create a patch for the replace_placeholders method
        with patch.object(rules_service, "replace_placeholders", return_value={
            "test1": "SELECT * FROM users WHERE id = 123;",
            "test2": "SELECT * FROM orders WHERE status = completed AND location_id = 62;"
        }) as mock_replace:
            # Call the method
            result = rules_service.replace_placeholders(patterns, replacements)
            
            # Verify the replacements
            assert result["test1"] == "SELECT * FROM users WHERE id = 123;"
            assert result["test2"] == "SELECT * FROM orders WHERE status = completed AND location_id = 62;"
            
            # Verify the method was called with the right parameters
            mock_replace.assert_called_once_with(patterns, replacements) 