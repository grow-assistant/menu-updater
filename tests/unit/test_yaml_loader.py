import os
import sys
import unittest
from pathlib import Path
import tempfile
import yaml

# Add the parent directory to sys.path to import the modules
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from services.rules.yaml_loader import YamlLoader, get_yaml_loader


class TestYamlLoader(unittest.TestCase):
    """Test cases for the YamlLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create a test YAML file
        self.test_yaml_path = self.temp_path / "test_config.yml"
        self.test_data = {
            "rules": {
                "rule1": "Value 1",
                "rule2": "Value 2"
            },
            "pattern_files": {
                "pattern1": "file1.sql",
                "pattern2": "file2.sql"
            }
        }
        
        with open(self.test_yaml_path, "w") as f:
            yaml.dump(self.test_data, f)
        
        # Create a test subdirectory with YAML files
        self.test_subdir = self.temp_path / "rules"
        self.test_subdir.mkdir()
        
        self.test_rule1_path = self.test_subdir / "rule1.yml"
        self.test_rule1_data = {"key1": "value1"}
        with open(self.test_rule1_path, "w") as f:
            yaml.dump(self.test_rule1_data, f)
        
        self.test_rule2_path = self.test_subdir / "rule2.yml"
        self.test_rule2_data = {"key2": "value2"}
        with open(self.test_rule2_path, "w") as f:
            yaml.dump(self.test_rule2_data, f)
        
        # Create a loader with the temp directory as base
        self.loader = YamlLoader(base_dir=str(self.temp_path))

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_load_yaml(self):
        """Test loading a YAML file."""
        # Test loading by relative path
        result = self.loader.load_yaml("test_config.yml")
        self.assertEqual(result, self.test_data)
        
        # Test loading by absolute path
        result = self.loader.load_yaml(str(self.test_yaml_path))
        self.assertEqual(result, self.test_data)
        
        # Test loading with Path object
        result = self.loader.load_yaml(self.test_yaml_path)
        self.assertEqual(result, self.test_data)

    def test_load_yaml_caching(self):
        """Test that YAML files are properly cached."""
        # Load file twice, should use cache the second time
        result1 = self.loader.load_yaml("test_config.yml")
        result2 = self.loader.load_yaml("test_config.yml")
        
        # Both results should be the same object (identity check)
        self.assertIs(result1, result2)
        
        # Force reload, should be a different object
        result3 = self.loader.load_yaml("test_config.yml", force_reload=True)
        self.assertEqual(result1, result3)  # Equal but not identical
        self.assertIsNot(result1, result3)

    def test_load_rules_dir(self):
        """Test loading all YAML files from a directory."""
        result = self.loader.load_rules_dir("rules")
        
        self.assertEqual(len(result), 2)
        self.assertIn("rule1", result)
        self.assertIn("rule2", result)
        self.assertEqual(result["rule1"], self.test_rule1_data)
        self.assertEqual(result["rule2"], self.test_rule2_data)

    def test_file_not_found(self):
        """Test handling of non-existent files."""
        with self.assertRaises(FileNotFoundError):
            self.loader.load_yaml("nonexistent_file.yml")

    def test_singleton_instance(self):
        """Test the singleton instance functionality."""
        loader1 = get_yaml_loader()
        loader2 = get_yaml_loader()
        
        # Both should be the same instance
        self.assertIs(loader1, loader2)
        
        # Should update the base_dir
        loader3 = get_yaml_loader("new_base_dir")
        # Account for the base_dir being a Path object
        self.assertEqual(str(loader3.base_dir), str(Path("new_base_dir")))


if __name__ == "__main__":
    unittest.main() 