"""
Unit tests for the ServiceRegistry class.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any

from services.utils.service_registry import ServiceRegistry


# Save the original get_service method to restore after tests
original_get_service = ServiceRegistry.get_service

class TestServiceRegistry:
    """Test class for the ServiceRegistry."""

    def setup_method(self):
        """Setup method that runs before each test."""
        # Reset the class variables before each test
        ServiceRegistry._services = {}
        ServiceRegistry._config = None
        
        # Restore the original get_service method
        ServiceRegistry.get_service = original_get_service

    def teardown_method(self):
        """Cleanup after each test."""
        # Restore the original get_service method
        ServiceRegistry.get_service = original_get_service

    def test_initialize(self):
        """Test initializing the service registry."""
        # Setup test config
        test_config = {"test": "config"}
        
        # Call initialize
        ServiceRegistry.initialize(test_config)
        
        # Verify config was stored and services dict was reset
        assert ServiceRegistry._config == test_config
        assert ServiceRegistry._services == {}

    def test_register(self):
        """Test registering a service factory."""
        # Setup
        test_config = {"test": "config"}
        ServiceRegistry._config = test_config
        
        # Define a mock factory function
        mock_factory = MagicMock()
        mock_factory.return_value = "test_service_instance"
        
        # Call register
        ServiceRegistry.register("test_service", mock_factory)
        
        # Verify service was registered
        assert "test_service" in ServiceRegistry._services
        service_info = ServiceRegistry._services["test_service"]
        assert service_info["factory"] == mock_factory
        assert service_info["instance"] is None
        assert service_info["healthy"] is True

    def test_get_service_success(self):
        """Test getting a service instance successfully."""
        # Setup
        test_config = {"test": "config"}
        ServiceRegistry._config = test_config
        
        mock_instance = MagicMock()
        mock_factory = MagicMock()
        mock_factory.return_value = mock_instance
        
        ServiceRegistry._services = {
            "test_service": {
                "factory": mock_factory,
                "instance": None,
                "healthy": True
            }
        }
        
        # Call get_service
        result = ServiceRegistry.get_service("test_service")
        
        # Verify service was instantiated and returned
        assert result == mock_instance
        mock_factory.assert_called_once_with(test_config)
        assert ServiceRegistry._services["test_service"]["instance"] == mock_instance
        assert ServiceRegistry._services["test_service"]["healthy"] is True

    def test_get_service_already_instantiated(self):
        """Test getting a service that's already been instantiated."""
        # Setup
        mock_instance = MagicMock()
        mock_factory = MagicMock()
        
        ServiceRegistry._services = {
            "test_service": {
                "factory": mock_factory,
                "instance": mock_instance,
                "healthy": True
            }
        }
        
        # Call get_service
        result = ServiceRegistry.get_service("test_service")
        
        # Verify existing instance was returned and factory not called
        assert result == mock_instance
        mock_factory.assert_not_called()

    def test_get_service_not_registered(self):
        """Test getting a service that hasn't been registered."""
        # Setup
        ServiceRegistry._services = {}
        
        # Verify exception is raised
        with pytest.raises(ValueError) as exc_info:
            ServiceRegistry.get_service("nonexistent_service")
        
        assert "not registered" in str(exc_info.value)

    def test_get_service_initialization_failure(self):
        """Test getting a service whose initialization fails."""
        # Setup
        test_config = {"test": "config"}
        ServiceRegistry._config = test_config
        
        mock_factory = MagicMock()
        mock_factory.side_effect = Exception("Initialization failed")
        
        ServiceRegistry._services = {
            "test_service": {
                "factory": mock_factory,
                "instance": None,
                "healthy": True
            }
        }
        
        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            ServiceRegistry.get_service("test_service")
        
        assert "Initialization failed" in str(exc_info.value)
        assert ServiceRegistry._services["test_service"]["healthy"] is False

    def test_check_health_all_healthy(self):
        """Test health check when all services are healthy."""
        # Setup services with health_check methods
        service1 = MagicMock()
        service1.health_check.return_value = True
        
        service2 = MagicMock()
        service2.health_check.return_value = True
        
        ServiceRegistry._services = {
            "service1": {
                "factory": MagicMock(),
                "instance": service1,
                "healthy": True
            },
            "service2": {
                "factory": MagicMock(),
                "instance": service2,
                "healthy": True
            }
        }
        
        # Call check_health
        results = ServiceRegistry.check_health()
        
        # Verify all services reported as healthy
        assert results == {
            "service1": True,
            "service2": True
        }

    def test_check_health_mixed_status(self):
        """Test health check with mixed service health statuses."""
        # Setup services with different health states
        service1 = MagicMock()
        service1.health_check.return_value = False

        service2 = MagicMock()  
        # Service2 should not have a health_check method
        del service2.health_check

        service3 = MagicMock()
        service3.health_check.side_effect = Exception("Health check failed")

        ServiceRegistry._services = {
            "service1": {
                "factory": MagicMock(),
                "instance": service1,
                "healthy": True
            },
            "service2": {
                "factory": MagicMock(),
                "instance": service2,
                "healthy": True
            },
            "service3": {
                "factory": MagicMock(),
                "instance": service3,
                "healthy": True
            },
            "service4": {  # Not instantiated
                "factory": MagicMock(),
                "instance": None,
                "healthy": True
            }
        }

        # Mock get_service to return a mock for service4
        original_get_service = ServiceRegistry.get_service

        def mock_get_service(service_name):
            if service_name == "service4":
                service4 = MagicMock()
                service4.health_check.return_value = True
                return service4
            return original_get_service(service_name)

        with patch.object(ServiceRegistry, 'get_service', side_effect=mock_get_service):
            # Call check_health
            results = ServiceRegistry.check_health()

        # Verify health status for each service
        assert results["service1"] is False  # Explicitly returned False
        assert results["service2"] is True   # No health_check method, assume healthy
        assert results["service3"] is False  # Exception during health check
        assert results["service4"] is True   # Health check returns True 