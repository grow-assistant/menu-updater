"""
Unit tests for the ScenarioLibrary class.
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
from ai_testing_agent.scenario_library import ScenarioLibrary, DEFAULT_SCENARIO_TEMPLATE


class TestScenarioLibrary:
    """Tests for the ScenarioLibrary class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test scenarios."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def library(self, temp_dir):
        """Create a ScenarioLibrary with a temporary directory."""
        return ScenarioLibrary(scenarios_dir=temp_dir)
    
    @pytest.fixture
    def sample_scenario(self):
        """Create a sample test scenario."""
        return {
            "name": "test_scenario",
            "category": "menu_query",
            "description": "A test scenario",
            "priority": "high",
            "tags": ["test", "menu"],
            "context": {
                "user_persona": "casual_diner",
                "restaurant_context": "Test context"
            },
            "initial_query_hints": ["What's on the menu?"],
            "expected_entities": ["menu_items"],
            "success_conditions": [
                {"type": "response_contains", "phrase": "our menu"}
            ],
            "max_turns": 3
        }
    
    def test_initialization(self, library, temp_dir):
        """Test that the library initializes correctly."""
        assert library.scenarios_dir == temp_dir
        assert isinstance(library.scenarios, dict)
        assert len(library.categories) > 0
        assert os.path.exists(temp_dir)
    
    def test_add_scenario(self, library, sample_scenario):
        """Test adding a scenario to the library."""
        result = library.add_scenario(sample_scenario)
        
        assert result is True
        assert "test_scenario" in library.scenarios
        assert library.scenarios["test_scenario"]["name"] == "test_scenario"
        assert "created_at" in library.scenarios["test_scenario"]
        
        # Verify file was created
        file_path = os.path.join(library.scenarios_dir, "test_scenario.json")
        assert os.path.exists(file_path)
        
        # Verify content
        with open(file_path, 'r') as f:
            saved_scenario = json.load(f)
            assert saved_scenario["name"] == "test_scenario"
            assert saved_scenario["category"] == "menu_query"
    
    def test_add_duplicate_scenario(self, library, sample_scenario):
        """Test that adding a duplicate scenario fails."""
        library.add_scenario(sample_scenario)
        result = library.add_scenario(sample_scenario)
        
        assert result is False
    
    def test_get_scenario(self, library, sample_scenario):
        """Test retrieving a scenario by name."""
        library.add_scenario(sample_scenario)
        
        scenario = library.get_scenario("test_scenario")
        assert scenario is not None
        assert scenario["name"] == "test_scenario"
        
        # Test getting a non-existent scenario
        scenario = library.get_scenario("nonexistent")
        assert scenario is None
    
    def test_update_scenario(self, library, sample_scenario):
        """Test updating an existing scenario."""
        library.add_scenario(sample_scenario)
        
        updates = {
            "description": "Updated description",
            "priority": "low"
        }
        
        result = library.update_scenario("test_scenario", updates)
        assert result is True
        
        # Verify updates were applied
        scenario = library.get_scenario("test_scenario")
        assert scenario["description"] == "Updated description"
        assert scenario["priority"] == "low"
        
        # Verify file was updated
        file_path = os.path.join(library.scenarios_dir, "test_scenario.json")
        with open(file_path, 'r') as f:
            saved_scenario = json.load(f)
            assert saved_scenario["description"] == "Updated description"
    
    def test_delete_scenario(self, library, sample_scenario):
        """Test deleting a scenario."""
        library.add_scenario(sample_scenario)
        file_path = os.path.join(library.scenarios_dir, "test_scenario.json")
        
        result = library.delete_scenario("test_scenario")
        assert result is True
        assert "test_scenario" not in library.scenarios
        assert not os.path.exists(file_path)
        
        # Test deleting a non-existent scenario
        result = library.delete_scenario("nonexistent")
        assert result is False
    
    def test_get_scenarios_by_category(self, library):
        """Test filtering scenarios by category."""
        # Add scenarios in different categories
        library.add_scenario({
            "name": "menu_scenario",
            "category": "menu_query",
            "description": "Menu scenario",
            "context": {},
            "max_turns": 3
        })
        
        library.add_scenario({
            "name": "order_scenario",
            "category": "order_history",
            "description": "Order scenario",
            "context": {},
            "max_turns": 3
        })
        
        # Test filtering
        menu_scenarios = library.get_scenarios_by_category("menu_query")
        assert len(menu_scenarios) == 1
        assert menu_scenarios[0]["name"] == "menu_scenario"
        
        order_scenarios = library.get_scenarios_by_category("order_history")
        assert len(order_scenarios) == 1
        assert order_scenarios[0]["name"] == "order_scenario"
        
        empty_scenarios = library.get_scenarios_by_category("nonexistent")
        assert len(empty_scenarios) == 0
    
    def test_get_scenarios_by_tag(self, library):
        """Test filtering scenarios by tag."""
        # Add scenarios with different tags
        library.add_scenario({
            "name": "menu_scenario",
            "category": "menu_query",
            "description": "Menu scenario",
            "tags": ["menu", "food"],
            "context": {},
            "max_turns": 3
        })
        
        library.add_scenario({
            "name": "price_scenario",
            "category": "menu_query",
            "description": "Price scenario",
            "tags": ["menu", "price"],
            "context": {},
            "max_turns": 3
        })
        
        # Test filtering
        food_scenarios = library.get_scenarios_by_tag("food")
        assert len(food_scenarios) == 1
        assert food_scenarios[0]["name"] == "menu_scenario"
        
        menu_scenarios = library.get_scenarios_by_tag("menu")
        assert len(menu_scenarios) == 2
        
        empty_scenarios = library.get_scenarios_by_tag("nonexistent")
        assert len(empty_scenarios) == 0
    
    def test_get_scenarios_by_priority(self, library):
        """Test filtering scenarios by priority."""
        # Add scenarios with different priorities
        library.add_scenario({
            "name": "high_scenario",
            "category": "menu_query",
            "description": "High priority scenario",
            "priority": "high",
            "context": {},
            "max_turns": 3
        })
        
        library.add_scenario({
            "name": "low_scenario",
            "category": "menu_query",
            "description": "Low priority scenario",
            "priority": "low",
            "context": {},
            "max_turns": 3
        })
        
        # Test filtering
        high_scenarios = library.get_scenarios_by_priority("high")
        assert len(high_scenarios) == 1
        assert high_scenarios[0]["name"] == "high_scenario"
        
        low_scenarios = library.get_scenarios_by_priority("low")
        assert len(low_scenarios) == 1
        assert low_scenarios[0]["name"] == "low_scenario"
        
        medium_scenarios = library.get_scenarios_by_priority("medium")
        assert len(medium_scenarios) == 0
    
    def test_add_test_result(self, library, sample_scenario):
        """Test adding a test result to a scenario."""
        library.add_scenario(sample_scenario)
        
        test_result = {
            "status": "success",
            "execution_time": 1.5,
            "turn_count": 3
        }
        
        result = library.add_test_result("test_scenario", test_result)
        assert result is True
        
        # Verify test result was added
        scenario = library.get_scenario("test_scenario")
        assert "test_history" in scenario
        assert len(scenario["test_history"]) == 1
        assert scenario["test_history"][0]["status"] == "success"
        assert "timestamp" in scenario["test_history"][0]
        
        # Test adding to a non-existent scenario
        result = library.add_test_result("nonexistent", test_result)
        assert result is False
    
    def test_generate_default_scenarios(self, library):
        """Test generating default scenarios."""
        # First test with an empty library
        count = library.generate_default_scenarios()
        assert count > 0
        assert len(library.scenarios) == count
        
        # Generate again - should skip since scenarios exist
        new_count = library.generate_default_scenarios()
        assert new_count == 0
        assert len(library.scenarios) == count
    
    def test_add_category(self, library):
        """Test adding a new category."""
        result = library.add_category(
            "test_category", 
            "A test category", 
            "high", 
            ["test", "new"]
        )
        
        assert result is True
        assert "test_category" in library.categories
        assert library.categories["test_category"]["description"] == "A test category"
        assert library.categories["test_category"]["priority"] == "high"
        assert "test" in library.categories["test_category"]["tags"]
        
        # Test adding a duplicate category
        result = library.add_category("test_category", "Duplicate")
        assert result is False
    
    def test_get_random_scenario(self, library):
        """Test retrieving a random scenario with filters."""
        # Add multiple scenarios
        library.add_scenario({
            "name": "menu_high",
            "category": "menu_query",
            "description": "High priority menu scenario",
            "priority": "high",
            "tags": ["menu", "test"],
            "context": {},
            "max_turns": 3
        })
        
        library.add_scenario({
            "name": "menu_low",
            "category": "menu_query",
            "description": "Low priority menu scenario",
            "priority": "low",
            "tags": ["menu", "test"],
            "context": {},
            "max_turns": 3
        })
        
        library.add_scenario({
            "name": "order_high",
            "category": "order_history",
            "description": "High priority order scenario",
            "priority": "high",
            "tags": ["order", "test"],
            "context": {},
            "max_turns": 3
        })
        
        # Test getting random scenario without filters
        scenario = library.get_random_scenario()
        assert scenario is not None
        assert scenario["name"] in ["menu_high", "menu_low", "order_high"]
        
        # Test with category filter
        for _ in range(5):  # Try multiple times to avoid random chance
            scenario = library.get_random_scenario(category="menu_query")
            assert scenario is not None
            assert scenario["category"] == "menu_query"
            assert scenario["name"] in ["menu_high", "menu_low"]
        
        # Test with tag filter
        for _ in range(5):
            scenario = library.get_random_scenario(tag="order")
            assert scenario is not None
            assert "order" in scenario["tags"]
            assert scenario["name"] == "order_high"
        
        # Test with priority filter
        for _ in range(5):
            scenario = library.get_random_scenario(priority="high")
            assert scenario is not None
            assert scenario["priority"] == "high"
            assert scenario["name"] in ["menu_high", "order_high"]
        
        # Test with combined filters
        for _ in range(5):
            scenario = library.get_random_scenario(
                category="menu_query", 
                priority="high"
            )
            assert scenario is not None
            assert scenario["category"] == "menu_query"
            assert scenario["priority"] == "high"
            assert scenario["name"] == "menu_high"
        
        # Test with no matching scenarios
        scenario = library.get_random_scenario(category="nonexistent")
        assert scenario is None
    
    def test_export_import_scenarios(self, library, temp_dir, sample_scenario):
        """Test exporting and importing scenarios."""
        library.add_scenario(sample_scenario)
        
        # Create additional scenarios to export
        library.add_scenario({
            "name": "additional_scenario",
            "category": "order_history",
            "description": "Another test scenario",
            "context": {},
            "max_turns": 3
        })
        
        # Export scenarios
        export_file = os.path.join(temp_dir, "export.json")
        result = library.export_scenarios(export_file)
        assert result is True
        assert os.path.exists(export_file)
        
        # Create a new library and import scenarios
        new_library = ScenarioLibrary(scenarios_dir=os.path.join(temp_dir, "imported"))
        assert len(new_library.scenarios) == 0
        
        import_count = new_library.import_scenarios(export_file)
        assert import_count == 2
        assert "test_scenario" in new_library.scenarios
        assert "additional_scenario" in new_library.scenarios
        
        # Test importing with an invalid file
        invalid_file = os.path.join(temp_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("{}")
            
        import_count = new_library.import_scenarios(invalid_file)
        assert import_count == 0 