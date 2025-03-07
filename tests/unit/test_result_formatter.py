"""
Unit tests for the Result Formatter module.

Tests the functionality of the result_formatter module which formats database query results.
"""

import pytest
import pandas as pd
import json
from decimal import Decimal
from datetime import datetime, date, time

from services.execution.result_formatter import (
    _json_serializer,
    format_to_json,
    format_to_csv,
    format_to_dataframe,
    format_to_text_table,
    format_result,
    get_summary_stats
)

@pytest.mark.unit
class TestResultFormatter:
    """Tests for the ResultFormatter module."""
    
    @pytest.fixture
    def sample_data(self):
        """Fixture providing sample data for testing."""
        return [
            {"id": 1, "name": "Burger", "price": Decimal("9.99"), "available": True, 
             "created_at": datetime(2023, 1, 1, 12, 0, 0)},
            {"id": 2, "name": "Pizza", "price": Decimal("12.99"), "available": False,
             "created_at": datetime(2023, 1, 2, 14, 30, 0)},
            {"id": 3, "name": "Salad", "price": Decimal("7.50"), "available": True,
             "created_at": datetime(2023, 1, 3, 10, 15, 0)}
        ]
    
    @pytest.mark.fast
    def test_json_serializer(self, sample_data):
        """Test the custom JSON serializer for special types."""
        # Test datetime serialization
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert _json_serializer(dt) == "2023-01-01T12:00:00"
        
        # Test date serialization
        d = date(2023, 1, 1)
        assert _json_serializer(d) == "2023-01-01"
        
        # Test time serialization
        t = time(12, 0, 0)
        assert _json_serializer(t) == "12:00:00"
        
        # Test Decimal serialization
        dec = Decimal("9.99")
        assert _json_serializer(dec) == float(dec)
        
        # Test string-convertible object
        class TestObj:
            def __str__(self):
                return "test_object"
        
        obj = TestObj()
        assert _json_serializer(obj) == "test_object"
        
        # Test non-serializable object - this would raise TypeError in real usage
        # but the implementation catches all objects with __str__ method
        # so we can't easily test the TypeError case
    
    @pytest.mark.fast
    def test_format_to_json(self, sample_data):
        """Test formatting data to JSON."""
        # Test with default options (not pretty)
        json_str = format_to_json(sample_data)
        assert isinstance(json_str, str)
        
        # Verify we can parse it back
        parsed = json.loads(json_str)
        assert len(parsed) == 3
        assert parsed[0]["name"] == "Burger"
        assert parsed[1]["price"] == 12.99
        assert parsed[2]["available"] is True
        
        # Test with pretty-printing
        pretty_json = format_to_json(sample_data, pretty=True)
        assert isinstance(pretty_json, str)
        assert pretty_json.count("\n") > 0  # Pretty JSON should have line breaks
        
        # Verify empty data handling
        empty_json = format_to_json([])
        assert empty_json == "[]"
    
    @pytest.mark.fast
    def test_format_to_csv(self, sample_data):
        """Test formatting data to CSV."""
        # Test with default options (with header)
        csv_str = format_to_csv(sample_data)
        assert isinstance(csv_str, str)
        
        # CSV should have 4 lines (header + 3 data rows)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 4
        
        # Header should contain all column names
        header = lines[0].split(",")
        assert "id" in header
        assert "name" in header
        assert "price" in header
        assert "available" in header
        # Handle the carriage return that might be present in the CSV output
        assert any("created_at" in h for h in header)
        
        # Test without header
        csv_no_header = format_to_csv(sample_data, include_header=False)
        lines_no_header = csv_no_header.strip().split("\n")
        assert len(lines_no_header) == 3  # Just data rows
        
        # Verify empty data handling
        empty_csv = format_to_csv([])
        assert empty_csv == ""
    
    @pytest.mark.fast
    def test_format_to_dataframe(self, sample_data):
        """Test formatting data to pandas DataFrame."""
        df = format_to_dataframe(sample_data)
        
        # Verify it's a DataFrame
        assert isinstance(df, pd.DataFrame)
        
        # Verify dimensions
        assert df.shape == (3, 5)  # 3 rows, 5 columns
        
        # Verify column names
        assert set(df.columns) == {"id", "name", "price", "available", "created_at"}
        
        # Verify data
        assert df.iloc[0]["name"] == "Burger"
        assert df.iloc[1]["price"] == Decimal("12.99")
        assert df.iloc[2]["available"] == True  # Use == instead of 'is' for pandas
        
        # Verify empty data handling
        empty_df = format_to_dataframe([])
        assert isinstance(empty_df, pd.DataFrame)
        assert empty_df.empty
    
    @pytest.mark.fast
    def test_format_to_text_table(self, sample_data):
        """Test formatting data to text table."""
        table = format_to_text_table(sample_data)
        
        # Verify it's a string
        assert isinstance(table, str)
        
        # Table should have borders and separators
        assert "+" in table or "-+-" in table  # Border character
        assert "|" in table  # Column separator
        
        # Table should have all data
        assert "Burger" in table
        assert "Pizza" in table
        assert "Salad" in table
        assert "9.99" in table
        assert "12.99" in table
        # The decimal 7.50 might be formatted as 7.5
        assert "7.5" in table
        
        # Test with custom column width
        narrow_table = format_to_text_table(sample_data, max_col_width=10)
        assert isinstance(narrow_table, str)
        
        # Verify empty data handling
        empty_table = format_to_text_table([])
        assert empty_table == "No data"
    
    @pytest.mark.fast
    def test_format_result(self, sample_data):
        """Test the main format_result function with different formats."""
        # Test JSON format
        json_result = format_result(sample_data, format_type="json")
        assert isinstance(json_result, str)
        assert json.loads(json_result)[0]["name"] == "Burger"
        
        # Test CSV format
        csv_result = format_result(sample_data, format_type="csv")
        assert isinstance(csv_result, str)
        assert "id" in csv_result
        assert "name" in csv_result
        
        # Test DataFrame format
        df_result = format_result(sample_data, format_type="dataframe")
        assert isinstance(df_result, pd.DataFrame)
        
        # Test text table format
        table_result = format_result(sample_data, format_type="text")
        assert isinstance(table_result, str)
        assert "Burger" in table_result
        
        # Test with format options
        json_pretty = format_result(sample_data, format_type="json", 
                                   format_options={"pretty": True})
        assert isinstance(json_pretty, str)
        assert json_pretty.count("\n") > 0
        
        # Test with invalid format type
        default_result = format_result(sample_data, format_type="invalid_format")
        assert isinstance(default_result, str)  # Should default to JSON
        
        # Verify empty data handling
        empty_result = format_result([], format_type="json")
        assert empty_result == ""  # Empty string for empty data
        
        empty_df_result = format_result([], format_type="dataframe")
        assert isinstance(empty_df_result, pd.DataFrame)
        assert empty_df_result.empty
        
        empty_text_result = format_result([], format_type="text")
        assert empty_text_result == "No data"
    
    @pytest.mark.fast
    def test_get_summary_stats(self, sample_data):
        """Test getting summary statistics from data."""
        stats = get_summary_stats(sample_data)
        
        # Verify it's a dictionary
        assert isinstance(stats, dict)
        
        # Verify basic stats
        assert stats["row_count"] == 3
        assert stats["column_count"] == 5
        
        # Verify columns list
        assert "columns" in stats
        assert isinstance(stats["columns"], list)
        assert len(stats["columns"]) == 5
        assert "id" in stats["columns"]
        assert "name" in stats["columns"]
        
        # Verify column stats
        assert "column_stats" in stats
        assert "price" in stats["column_stats"]
        
        # Verify numeric column stats
        price_stats = stats["column_stats"]["price"]
        assert price_stats["type"] == "numeric"
        assert price_stats["min"] == 7.5
        assert price_stats["max"] == 12.99
        assert price_stats["avg"] == pytest.approx(10.16, 0.01)
        
        # Verify text column stats
        name_stats = stats["column_stats"]["name"]
        assert name_stats["type"] == "text"
        assert name_stats["min_length"] == 5  # "Pizza" and "Salad" are 5 chars
        assert name_stats["max_length"] == 6  # "Burger" is 6 chars
        
        # Verify empty data handling
        empty_stats = get_summary_stats([])
        assert empty_stats["row_count"] == 0
        assert empty_stats["column_count"] == 0 