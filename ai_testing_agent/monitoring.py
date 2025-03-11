"""
Real-time Monitoring for AI Testing

This module provides tools for real-time monitoring and visualization of test executions.
It includes dashboard capabilities, event notifications, and test result tracking.
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from datetime import datetime
from threading import Thread, Lock
from collections import defaultdict

logger = logging.getLogger(__name__)

class TestMonitor:
    """
    Monitors test execution in real-time, collecting metrics, and providing 
    notification capabilities.
    """
    
    def __init__(self, notification_threshold: str = "high", data_dir: str = "monitoring_data"):
        """
        Initialize the test monitor.
        
        Args:
            notification_threshold: Minimum severity level for notifications 
                                   ("low", "medium", "high", "critical")
            data_dir: Directory to store monitoring data
        """
        self.notification_threshold = notification_threshold
        self.data_dir = data_dir
        self.notification_callbacks = []
        self.dashboard_callbacks = []
        self.summary_data = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "in_progress_tests": 0,
            "total_scenarios": 0,
            "scenarios_run": set(),
            "scenarios_failed": set(),
            "total_critiques": 0,
            "critiques_by_severity": defaultdict(int),
            "critiques_by_type": defaultdict(int),
            "avg_processing_time": 0,
            "test_history": [],
            "start_time": time.time(),
            "last_update": time.time()
        }
        self.lock = Lock()
        self._setup_data_dir()
        
        # Start metrics collection thread
        self.collection_active = True
        self.metrics_thread = Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()
        
        logger.info("TestMonitor initialized")
        
    def _setup_data_dir(self):
        """Create data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def _metrics_collection_loop(self):
        """Background loop for metrics collection and storage."""
        while self.collection_active:
            # Save current metrics to disk
            try:
                self._save_metrics()
            except Exception as e:
                logger.error(f"Error saving metrics: {str(e)}", exc_info=True)
                
            # Sleep for a bit
            time.sleep(60)  # Update every minute
            
    def _save_metrics(self):
        """Save current metrics to disk."""
        with self.lock:
            # Create a copy of summary data suitable for serialization
            metrics_copy = dict(self.summary_data)
            metrics_copy["scenarios_run"] = list(metrics_copy["scenarios_run"])
            metrics_copy["scenarios_failed"] = list(metrics_copy["scenarios_failed"])
            
            # Add timestamp
            metrics_copy["timestamp"] = datetime.now().isoformat()
            
            # Write to file
            filename = os.path.join(self.data_dir, f"metrics_{int(time.time())}.json")
            with open(filename, 'w') as f:
                json.dump(metrics_copy, f, indent=2)
                
            # Also save latest metrics
            latest_file = os.path.join(self.data_dir, "latest_metrics.json")
            with open(latest_file, 'w') as f:
                json.dump(metrics_copy, f, indent=2)
                
    def add_notification_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback for real-time notifications of important events.
        
        Args:
            callback: Function that receives notification data
        """
        self.notification_callbacks.append(callback)
        
    def add_dashboard_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback for real-time dashboard updates.
        
        Args:
            callback: Function that receives dashboard update data
        """
        self.dashboard_callbacks.append(callback)
        
    def process_test_result(self, result: Dict[str, Any]) -> None:
        """
        Process a test result and update metrics.
        
        Args:
            result: Test result data
        """
        with self.lock:
            # Update summary stats
            self.summary_data["total_tests"] += 1
            
            # Get scenario info
            scenario_name = result.get("scenario", "unknown")
            self.summary_data["scenarios_run"].add(scenario_name)
            self.summary_data["total_scenarios"] = len(self.summary_data["scenarios_run"])
            
            # Calculate status
            status = result.get("status", "unknown")
            if status == "success":
                self.summary_data["passed_tests"] += 1
            elif status == "error" or status == "failed":
                self.summary_data["failed_tests"] += 1
                self.summary_data["scenarios_failed"].add(scenario_name)
            elif status == "in_progress":
                self.summary_data["in_progress_tests"] += 1
                
            # Process critiques
            critiques = result.get("critiques", [])
            self.summary_data["total_critiques"] += len(critiques)
            
            for critique in critiques:
                severity = critique.get("severity", "medium")
                critique_type = critique.get("type", "unknown")
                self.summary_data["critiques_by_severity"][severity] += 1
                self.summary_data["critiques_by_type"][critique_type] += 1
                
                # Check if this needs notification
                severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                threshold_level = severity_levels.get(self.notification_threshold, 1)
                critique_level = severity_levels.get(severity, 1)
                
                if critique_level >= threshold_level:
                    self._send_notification({
                        "type": "critique",
                        "scenario": scenario_name,
                        "critique": critique,
                        "timestamp": time.time()
                    })
                    
            # Process processing time
            processing_time = result.get("processing_time", 0)
            current_avg = self.summary_data["avg_processing_time"]
            total_tests = self.summary_data["total_tests"]
            
            # Update running average
            if total_tests > 1:
                self.summary_data["avg_processing_time"] = (
                    (current_avg * (total_tests - 1) + processing_time) / total_tests
                )
            else:
                self.summary_data["avg_processing_time"] = processing_time
                
            # Add to history (limited to last 100 tests)
            self.summary_data["test_history"].append({
                "scenario": scenario_name,
                "status": status,
                "processing_time": processing_time,
                "critiques_count": len(critiques),
                "timestamp": time.time()
            })
            if len(self.summary_data["test_history"]) > 100:
                self.summary_data["test_history"] = self.summary_data["test_history"][-100:]
                
            # Update timestamp
            self.summary_data["last_update"] = time.time()
            
            # Send dashboard update
            self._send_dashboard_update()
            
            # Check for test failure notification
            if status == "error" or status == "failed":
                self._send_notification({
                    "type": "test_failure",
                    "scenario": scenario_name,
                    "details": result,
                    "timestamp": time.time()
                })
                
    def _send_notification(self, notification_data: Dict[str, Any]) -> None:
        """
        Send a notification to all registered callbacks.
        
        Args:
            notification_data: Notification information
        """
        for callback in self.notification_callbacks:
            try:
                callback(notification_data)
            except Exception as e:
                logger.error(f"Error in notification callback: {str(e)}", exc_info=True)
                
    def _send_dashboard_update(self) -> None:
        """Send a dashboard update to all registered callbacks."""
        # Create a copy of the summary data
        with self.lock:
            dashboard_data = dict(self.summary_data)
            dashboard_data["scenarios_run"] = list(dashboard_data["scenarios_run"])
            dashboard_data["scenarios_failed"] = list(dashboard_data["scenarios_failed"])
            
        # Add elapsed time
        dashboard_data["elapsed_time"] = time.time() - dashboard_data["start_time"]
        
        # Send to callbacks
        for callback in self.dashboard_callbacks:
            try:
                callback(dashboard_data)
            except Exception as e:
                logger.error(f"Error in dashboard callback: {str(e)}", exc_info=True)
                
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get the current metrics.
        
        Returns:
            Dictionary containing current metrics
        """
        with self.lock:
            metrics = dict(self.summary_data)
            metrics["scenarios_run"] = list(metrics["scenarios_run"])
            metrics["scenarios_failed"] = list(metrics["scenarios_failed"])
            metrics["elapsed_time"] = time.time() - metrics["start_time"]
            return metrics
            
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        with self.lock:
            self.summary_data = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "in_progress_tests": 0,
                "total_scenarios": 0,
                "scenarios_run": set(),
                "scenarios_failed": set(),
                "total_critiques": 0,
                "critiques_by_severity": defaultdict(int),
                "critiques_by_type": defaultdict(int),
                "avg_processing_time": 0,
                "test_history": [],
                "start_time": time.time(),
                "last_update": time.time()
            }
            
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self.collection_active = False
        if self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=2)
            
        # Save final metrics
        self._save_metrics()
        
class ConsoleMonitorCallback:
    """Simple callback that prints monitoring updates to the console."""
    
    def __init__(self, show_notifications: bool = True, show_dashboard: bool = False, 
                dashboard_interval: int = 60):
        """
        Initialize the console monitor callback.
        
        Args:
            show_notifications: Whether to show individual notifications
            show_dashboard: Whether to show dashboard updates
            dashboard_interval: How often to show dashboard updates (seconds)
        """
        self.show_notifications = show_notifications
        self.show_dashboard = show_dashboard
        self.dashboard_interval = dashboard_interval
        self.last_dashboard_update = 0
        
    def notification_callback(self, notification: Dict[str, Any]) -> None:
        """
        Handle a notification.
        
        Args:
            notification: Notification data
        """
        if not self.show_notifications:
            return
            
        notification_type = notification.get("type", "unknown")
        scenario = notification.get("scenario", "unknown")
        
        if notification_type == "critique":
            critique = notification.get("critique", {})
            critique_msg = critique.get("message", "No message")
            severity = critique.get("severity", "medium")
            print(f"\n[NOTIFICATION] {severity.upper()} CRITIQUE in scenario '{scenario}':")
            print(f"  {critique_msg}")
            
        elif notification_type == "test_failure":
            print(f"\n[NOTIFICATION] TEST FAILURE in scenario '{scenario}'")
            details = notification.get("details", {})
            if "error" in details:
                print(f"  Error: {details['error']}")
                
    def dashboard_callback(self, dashboard_data: Dict[str, Any]) -> None:
        """
        Handle a dashboard update.
        
        Args:
            dashboard_data: Dashboard update data
        """
        if not self.show_dashboard:
            return
            
        current_time = time.time()
        if current_time - self.last_dashboard_update < self.dashboard_interval:
            return
            
        self.last_dashboard_update = current_time
        
        # Print a dashboard summary
        total_tests = dashboard_data.get("total_tests", 0)
        passed = dashboard_data.get("passed_tests", 0)
        failed = dashboard_data.get("failed_tests", 0)
        in_progress = dashboard_data.get("in_progress_tests", 0)
        avg_time = dashboard_data.get("avg_processing_time", 0)
        total_critiques = dashboard_data.get("total_critiques", 0)
        
        elapsed = dashboard_data.get("elapsed_time", 0)
        elapsed_mins = int(elapsed // 60)
        elapsed_secs = int(elapsed % 60)
        
        print("\n" + "=" * 50)
        print(f"TESTING DASHBOARD (Elapsed: {elapsed_mins:02d}:{elapsed_secs:02d})")
        print("-" * 50)
        print(f"Total Tests: {total_tests} (Passed: {passed}, Failed: {failed}, In Progress: {in_progress})")
        print(f"Success Rate: {(passed / total_tests * 100) if total_tests > 0 else 0:.1f}%")
        print(f"Avg Processing Time: {avg_time:.3f}s")
        print(f"Total Critiques: {total_critiques}")
        
        # Print critique summary by severity
        critiques_by_severity = dashboard_data.get("critiques_by_severity", {})
        if critiques_by_severity:
            print("\nCritiques by Severity:")
            for severity, count in sorted(critiques_by_severity.items(), 
                                         key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(x[0], 0),
                                         reverse=True):
                print(f"  {severity.title()}: {count}")
                
        print("=" * 50)
        
def create_test_monitor() -> Tuple[TestMonitor, Callable[[Dict[str, Any]], None]]:
    """
    Create and configure a test monitor with a console callback.
    
    Returns:
        Tuple containing the monitor and the callback function for the orchestrator
    """
    monitor = TestMonitor()
    console_callback = ConsoleMonitorCallback(
        show_notifications=True,
        show_dashboard=True,
        dashboard_interval=30  # Show dashboard every 30 seconds
    )
    
    # Register callbacks
    monitor.add_notification_callback(console_callback.notification_callback)
    monitor.add_dashboard_callback(console_callback.dashboard_callback)
    
    # Create a callback for the TestingOrchestrator
    def orchestrator_callback(result: Dict[str, Any]) -> None:
        monitor.process_test_result(result)
        
    return monitor, orchestrator_callback 