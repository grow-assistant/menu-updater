"""
Unit tests for the monitoring module.
"""

import pytest
import time
import os
import shutil
import json
from threading import Thread
from typing import Dict, Any, List

from ai_testing_agent.monitoring import TestMonitor, ConsoleMonitorCallback, create_test_monitor

class TestMonitoring:
    """Tests for the monitoring functionality."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test data."""
        data_dir = tmp_path / "monitoring_data"
        data_dir.mkdir()
        yield str(data_dir)
        # Clean up
        shutil.rmtree(str(data_dir), ignore_errors=True)
    
    @pytest.fixture
    def monitor(self, temp_dir):
        """Create a test monitor instance."""
        monitor = TestMonitor(notification_threshold="medium", data_dir=temp_dir)
        yield monitor
        # Clean up
        monitor.stop()
    
    def test_initialization(self, monitor, temp_dir):
        """Test monitor initialization."""
        assert monitor.notification_threshold == "medium"
        assert monitor.data_dir == temp_dir
        assert isinstance(monitor.notification_callbacks, list)
        assert isinstance(monitor.dashboard_callbacks, list)
        assert monitor.summary_data["total_tests"] == 0
        assert monitor.metrics_thread.is_alive()
    
    def test_add_callbacks(self, monitor):
        """Test adding callbacks."""
        # Mock callbacks
        def notification_callback(data): pass
        def dashboard_callback(data): pass
        
        monitor.add_notification_callback(notification_callback)
        monitor.add_dashboard_callback(dashboard_callback)
        
        assert len(monitor.notification_callbacks) == 1
        assert len(monitor.dashboard_callbacks) == 1
    
    def test_process_test_result(self, monitor):
        """Test processing a test result."""
        # Create a mock test result
        result = {
            "scenario": "test_scenario",
            "status": "success",
            "processing_time": 0.5,
            "critiques": [
                {"severity": "high", "type": "clarity_issue", "message": "Test critique"}
            ]
        }
        
        # Process the result
        monitor.process_test_result(result)
        
        # Check summary data
        assert monitor.summary_data["total_tests"] == 1
        assert monitor.summary_data["passed_tests"] == 1
        assert monitor.summary_data["failed_tests"] == 0
        assert "test_scenario" in monitor.summary_data["scenarios_run"]
        assert monitor.summary_data["total_critiques"] == 1
        assert monitor.summary_data["critiques_by_severity"]["high"] == 1
        assert monitor.summary_data["critiques_by_type"]["clarity_issue"] == 1
        assert len(monitor.summary_data["test_history"]) == 1
    
    def test_process_failed_test(self, monitor):
        """Test processing a failed test."""
        # Create a mock test result
        result = {
            "scenario": "failed_scenario",
            "status": "failed",
            "error": "Test error",
            "processing_time": 0.5,
            "critiques": []
        }
        
        # Add a mock notification callback
        notifications = []
        def notification_callback(data):
            notifications.append(data)
        
        monitor.add_notification_callback(notification_callback)
        
        # Process the result
        monitor.process_test_result(result)
        
        # Check summary data
        assert monitor.summary_data["failed_tests"] == 1
        assert "failed_scenario" in monitor.summary_data["scenarios_failed"]
        
        # Check notification
        assert len(notifications) == 1
        assert notifications[0]["type"] == "test_failure"
        assert notifications[0]["scenario"] == "failed_scenario"
    
    def test_get_current_metrics(self, monitor):
        """Test getting current metrics."""
        # Add some test data
        result1 = {"scenario": "scenario1", "status": "success", "processing_time": 0.5, "critiques": []}
        result2 = {"scenario": "scenario2", "status": "failed", "processing_time": 0.7, "critiques": []}
        
        monitor.process_test_result(result1)
        monitor.process_test_result(result2)
        
        # Get metrics
        metrics = monitor.get_current_metrics()
        
        # Check metrics
        assert metrics["total_tests"] == 2
        assert metrics["passed_tests"] == 1
        assert metrics["failed_tests"] == 1
        assert "elapsed_time" in metrics
        assert "scenario1" in metrics["scenarios_run"]
        assert "scenario2" in metrics["scenarios_failed"]
    
    def test_reset_metrics(self, monitor):
        """Test resetting metrics."""
        # Add some test data
        result = {"scenario": "scenario1", "status": "success", "processing_time": 0.5, "critiques": []}
        monitor.process_test_result(result)
        
        # Reset metrics
        monitor.reset_metrics()
        
        # Check metrics
        assert monitor.summary_data["total_tests"] == 0
        assert monitor.summary_data["passed_tests"] == 0
        assert monitor.summary_data["scenarios_run"] == set()
    
    def test_save_metrics(self, monitor, temp_dir):
        """Test saving metrics to disk."""
        # Add some test data
        result = {"scenario": "scenario1", "status": "success", "processing_time": 0.5, "critiques": []}
        monitor.process_test_result(result)
        
        # Force save metrics
        monitor._save_metrics()
        
        # Check that the latest_metrics.json file exists
        latest_file = os.path.join(temp_dir, "latest_metrics.json")
        assert os.path.exists(latest_file)
        
        # Check file contents
        with open(latest_file, 'r') as f:
            metrics = json.load(f)
            assert metrics["total_tests"] == 1
            assert "scenario1" in metrics["scenarios_run"]
    
    def test_console_callback(self, capsys):
        """Test console callback functionality."""
        callback = ConsoleMonitorCallback(show_notifications=True, show_dashboard=True, dashboard_interval=0)
        
        # Test notification callback
        notification = {
            "type": "critique",
            "scenario": "test_scenario",
            "critique": {
                "message": "Test critique message",
                "severity": "high"
            }
        }
        
        callback.notification_callback(notification)
        
        # Check output
        captured = capsys.readouterr()
        assert "HIGH CRITIQUE" in captured.out
        assert "Test critique message" in captured.out
        
        # Test dashboard callback
        dashboard_data = {
            "total_tests": 10,
            "passed_tests": 8,
            "failed_tests": 2,
            "in_progress_tests": 0,
            "avg_processing_time": 0.5,
            "total_critiques": 5,
            "critiques_by_severity": {"high": 2, "medium": 3},
            "elapsed_time": 120
        }
        
        callback.dashboard_callback(dashboard_data)
        
        # Check output
        captured = capsys.readouterr()
        assert "TESTING DASHBOARD" in captured.out
        assert "Total Tests: 10" in captured.out
        assert "Success Rate: 80.0%" in captured.out
        
    def test_create_test_monitor(self):
        """Test the create_test_monitor function."""
        monitor, callback = create_test_monitor()
        
        assert isinstance(monitor, TestMonitor)
        assert callable(callback)
        
        # Clean up
        monitor.stop() 