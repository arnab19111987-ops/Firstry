"""Tests for main module."""

import unittest
from src.main import process_data, validate_config, DataProcessor


class TestProcessData(unittest.TestCase):
    """Test process_data function."""
    
    def test_process_empty_list(self):
        """Test processing empty list."""
        result = process_data([])
        self.assertEqual(result, [])
    
    def test_process_strings(self):
        """Test processing strings."""
        data = ["  hello  ", "world", "", "python"]
        expected = ["HELLO", "WORLD", "PYTHON"]
        result = process_data(data)
        self.assertEqual(result, expected)


class TestValidateConfig(unittest.TestCase):
    """Test validate_config function."""
    
    def test_valid_config(self):
        """Test valid configuration."""
        config = {"name": "test", "version": "1.0", "author": "tester"}
        self.assertTrue(validate_config(config))
    
    def test_invalid_config(self):
        """Test invalid configuration."""
        config = {"name": "test"}
        self.assertFalse(validate_config(config))


class TestDataProcessor(unittest.TestCase):
    """Test DataProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {"name": "test", "version": "1.0", "author": "tester"}
        self.processor = DataProcessor(self.config)
    
    def test_process_items(self):
        """Test processing items."""
        items = ["hello", "world"]
        result = self.processor.process(items)
        self.assertEqual(result, ["HELLO", "WORLD"])
        self.assertEqual(self.processor.get_stats()["processed_count"], 2)
    
    def test_invalid_config_raises_error(self):
        """Test that invalid config raises error."""
        with self.assertRaises(ValueError):
            DataProcessor({"invalid": "config"})


if __name__ == "__main__":
    unittest.main()