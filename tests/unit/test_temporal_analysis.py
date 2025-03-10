"""Unit tests for the Temporal Analysis Service."""
import unittest
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from services.temporal_analysis import TemporalAnalysisService


class TestTemporalAnalysisService(unittest.TestCase):
    """Test cases for TemporalAnalysisService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = TemporalAnalysisService()
    
    def test_initialization(self):
        """Test that the service initializes properly."""
        self.assertIsNotNone(self.service)
        self.assertIn('last month', self.service.RELATIVE_PATTERNS)
        self.assertIn('year over year', self.service.COMPARATIVE_PATTERNS)
    
    def test_extract_explicit_dates(self):
        """Test extracting explicit dates from text."""
        # Test MM/DD/YYYY format
        dates = self.service._extract_explicit_dates("Order from 10/15/2023")
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0].month, 10)
        self.assertEqual(dates[0].day, 15)
        self.assertEqual(dates[0].year, 2023)
        
        # Test written date format
        dates = self.service._extract_explicit_dates("Orders placed on January 5, 2023")
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0].month, 1)
        self.assertEqual(dates[0].day, 5)
        self.assertEqual(dates[0].year, 2023)
        
        # Test month-year format
        dates = self.service._extract_explicit_dates("Show sales for March 2023")
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0].month, 3)
        self.assertEqual(dates[0].day, 1)  # First day of month
        self.assertEqual(dates[0].year, 2023)
        
        # Test quarter format
        dates = self.service._extract_explicit_dates("Revenue for Q2 2023")
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0].month, 4)  # First month of Q2
        self.assertEqual(dates[0].day, 1)  # First day of month
        self.assertEqual(dates[0].year, 2023)
    
    def test_extract_relative_references(self):
        """Test extracting relative time references from text."""
        # Test single reference
        refs = self.service._extract_relative_references("Show orders from last month")
        self.assertIn("last month", refs)
        
        # Test multiple references
        refs = self.service._extract_relative_references("Compare last week to this week")
        self.assertIn("last week", refs)
        self.assertIn("this week", refs)
        
        # Test newer references
        refs = self.service._extract_relative_references("Show sales year to date")
        self.assertIn("year to date", refs)
    
    def test_extract_date_range(self):
        """Test extracting date ranges from text."""
        # Test explicit date range
        date_range = self.service._extract_date_range("Orders from 01/01/2023 to 01/31/2023")
        self.assertIsNotNone(date_range)
        self.assertEqual(date_range['start_date'].month, 1)
        self.assertEqual(date_range['start_date'].day, 1)
        self.assertEqual(date_range['end_date'].month, 1)
        self.assertEqual(date_range['end_date'].day, 31)
        
        # Test mixed range (relative and explicit)
        date_range = self.service._extract_date_range("Revenue from last month to January 15, 2023")
        self.assertIsNotNone(date_range)
    
    def test_extract_comparative_analysis(self):
        """Test extracting comparative analysis requests."""
        # Test YoY comparison
        comp = self.service._extract_comparative_analysis("Show sales compared to last year")
        self.assertIsNotNone(comp)
        self.assertEqual(comp['type'], 'compare')
        
        # Test specific comparison type
        comp = self.service._extract_comparative_analysis("Revenue year over year")
        self.assertIsNotNone(comp)
        self.assertEqual(comp['type'], 'yoy')
        
        # Test no comparison
        comp = self.service._extract_comparative_analysis("Show me last month's sales")
        self.assertIsNone(comp)
    
    def test_resolve_relative_reference(self):
        """Test resolving relative references to absolute time periods."""
        # Fix the base date for consistent testing
        base_date = datetime(2023, 3, 15)
        
        # Test "last month"
        period = self.service.resolve_relative_reference("last month", base_date)
        self.assertEqual(period['start_date'].year, 2023)
        self.assertEqual(period['start_date'].month, 2)
        self.assertEqual(period['start_date'].day, 1)
        self.assertEqual(period['end_date'].year, 2023)
        self.assertEqual(period['end_date'].month, 2)
        self.assertEqual(period['end_date'].day, 28)  # February 2023 has 28 days
        
        # Test "this year"
        period = self.service.resolve_relative_reference("this year", base_date)
        self.assertEqual(period['start_date'].year, 2023)
        self.assertEqual(period['start_date'].month, 1)
        self.assertEqual(period['start_date'].day, 1)
        self.assertEqual(period['end_date'].year, 2023)
        self.assertEqual(period['end_date'].month, 12)
        self.assertEqual(period['end_date'].day, 31)
        
        # Test "year to date"
        period = self.service.resolve_relative_reference("year to date", base_date)
        self.assertEqual(period['start_date'].year, 2023)
        self.assertEqual(period['start_date'].month, 1)
        self.assertEqual(period['start_date'].day, 1)
        self.assertEqual(period['end_date'], base_date)
    
    def test_calculate_comparison_period(self):
        """Test calculating comparison periods."""
        # Create a test time period
        time_period = {
            'start_date': datetime(2023, 3, 1),
            'end_date': datetime(2023, 3, 31)
        }
        
        # Test YoY comparison
        comp_period = self.service._calculate_comparison_period(time_period, 'yoy')
        self.assertEqual(comp_period['start_date'].year, 2022)
        self.assertEqual(comp_period['start_date'].month, 3)
        self.assertEqual(comp_period['end_date'].year, 2022)
        self.assertEqual(comp_period['end_date'].month, 3)
        
        # Test MoM comparison
        comp_period = self.service._calculate_comparison_period(time_period, 'mom')
        self.assertEqual(comp_period['start_date'].year, 2023)
        self.assertEqual(comp_period['start_date'].month, 2)
        self.assertEqual(comp_period['end_date'].year, 2023)
        self.assertEqual(comp_period['end_date'].month, 3)  # Spanning into March due to day count
    
    def test_format_time_period(self):
        """Test formatting time periods for display."""
        # Test single day
        period = {
            'start_date': datetime(2023, 3, 15),
            'end_date': datetime(2023, 3, 15)
        }
        formatted = self.service.format_time_period(period)
        self.assertEqual(formatted, "March 15, 2023")
        
        # Test full month
        period = {
            'start_date': datetime(2023, 3, 1),
            'end_date': datetime(2023, 3, 31)
        }
        formatted = self.service.format_time_period(period)
        self.assertEqual(formatted, "March 2023")
        
        # Test full year
        period = {
            'start_date': datetime(2023, 1, 1),
            'end_date': datetime(2023, 12, 31)
        }
        formatted = self.service.format_time_period(period)
        self.assertEqual(formatted, "2023")
        
        # Test custom range
        period = {
            'start_date': datetime(2023, 3, 15),
            'end_date': datetime(2023, 4, 15)
        }
        formatted = self.service.format_time_period(period)
        self.assertEqual(formatted, "March 15, 2023 to April 15, 2023")
    
    def test_analyze_integration(self):
        """Test the full analysis flow with various queries."""
        # Test with explicit date
        result = self.service.analyze("Show orders from January 15, 2023")
        self.assertTrue(len(result['explicit_dates']) > 0)
        self.assertIsNotNone(result['resolved_time_period'])
        
        # Test with relative reference
        result = self.service.analyze("Show sales from last month")
        self.assertTrue(len(result['relative_references']) > 0)
        self.assertIsNotNone(result['resolved_time_period'])
        
        # Test with comparison
        result = self.service.analyze("Show revenue from this year compared to last year")
        self.assertTrue(len(result['relative_references']) > 0)
        self.assertIsNotNone(result['comparative_analysis'])
        
        # Test with no time reference
        result = self.service.analyze("Show me the sales")
        self.assertTrue(result['is_ambiguous'])
        self.assertTrue(result['needs_clarification'])
        self.assertIsNotNone(result['clarification_question'])
    
    def test_health_check(self):
        """Test the health check function."""
        health = self.service.health_check()
        self.assertEqual(health['service'], 'temporal_analysis')
        self.assertEqual(health['status'], 'ok')
        self.assertIn('capabilities', health)


if __name__ == '__main__':
    unittest.main() 