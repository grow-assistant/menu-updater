"""
Service Registry for maintaining references to service instances.

This registry acts as a service locator pattern implementation,
allowing services to be registered and retrieved by name.
"""
import logging
from typing import Dict, Any, Optional, Callable, List, Tuple

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    Registry for service objects that enables dependency injection.
    
    This is implemented as a class with class variables and methods
    to provide a singleton-like registry accessible from anywhere.
    """
    
    # Class variable to store service instances
    _services: Dict[str, Dict[str, Any]] = {}
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def initialize(cls, config: Dict[str, Any]) -> None:
        """
        Initialize the registry with a configuration dictionary.
        
        Args:
            config: Configuration dictionary for service initialization
        """
        cls._config = config
        logger.info("Service registry initialized with configuration")
    
    @classmethod
    def register(cls, service_name: str, service_factory: Callable) -> None:
        """
        Register a service factory function with the registry.
        
        Args:
            service_name: Name to register the service under
            service_factory: Factory function that creates the service instance
        """
        if service_name in cls._services:
            logger.warning(f"Service '{service_name}' is being replaced in the registry")
        
        cls._services[service_name] = {
            "factory": service_factory,
            "instance": None,
            "healthy": True
        }
        
        logger.info(f"Service '{service_name}' registered")
    
    @classmethod
    def get(cls, service_name: str) -> Optional[Any]:
        """
        Get a service from the registry.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            The service instance, or None if not found
        """
        return cls.get_service(service_name)
    
    @classmethod
    def service_exists(cls, service_name: str) -> bool:
        """
        Check if a service exists in the registry.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if the service is registered, False otherwise
        """
        return service_name in cls._services
    
    @classmethod
    def get_service(cls, service_name: str) -> Any:
        """
        Get a service from the registry, instantiating it if necessary.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            The service instance
            
        Raises:
            ValueError: If the service is not registered
        """
        service_info = cls._services.get(service_name)
        if service_info is None:
            logger.warning(f"Service '{service_name}' not found in registry")
            raise ValueError(f"Service '{service_name}' is not registered")
        
        if service_info["instance"] is None:
            try:
                # Instantiate the service using its factory
                factory = service_info["factory"]
                service_info["instance"] = factory(cls._config)
                logger.info(f"Service '{service_name}' instantiated")
            except Exception as e:
                logger.error(f"Failed to instantiate service '{service_name}': {str(e)}")
                service_info["healthy"] = False
                raise
        
        return service_info["instance"]
    
    @classmethod
    def unregister(cls, service_name: str) -> bool:
        """
        Remove a service from the registry.
        
        Args:
            service_name: Name of the service to remove
            
        Returns:
            True if the service was removed, False if it wasn't found
        """
        if service_name in cls._services:
            del cls._services[service_name]
            logger.info(f"Service '{service_name}' unregistered")
            return True
        
        logger.warning(f"Attempt to unregister non-existent service '{service_name}'")
        return False
    
    @classmethod
    def list_services(cls) -> Dict[str, Any]:
        """
        Get a dictionary of all registered services.
        
        Returns:
            Dictionary mapping service names to service instances
        """
        return cls._services.copy()
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered services.
        
        This is mainly useful for testing.
        """
        cls._services.clear()
        logger.info("Service registry cleared")
        
    @classmethod
    def check_health(cls) -> Dict[str, bool]:
        """
        Check the health of all registered services.
        
        Returns:
            Dictionary with service names as keys and health status as boolean values
        """
        results = {}
        
        for service_name, service_info in cls._services.items():
            # Initialize health status as false
            is_healthy = False
            
            instance = service_info.get("instance")
            
            if instance is None:
                try:
                    # Try to instantiate the service
                    instance = cls.get_service(service_name)
                except Exception:
                    # Failed to instantiate, mark as unhealthy
                    results[service_name] = False
                    continue
            
            # Try to call the health_check method if it exists
            try:
                if hasattr(instance, "health_check") and callable(getattr(instance, "health_check")):
                    is_healthy = instance.health_check()
                else:
                    # No health check method, assume healthy if instantiated
                    is_healthy = True
            except Exception:
                is_healthy = False
            
            results[service_name] = is_healthy
        
        return results

# Example of registering core services at module import time
def register_core_services():
    """Register core services that should be available by default."""
    # This function would be called during application initialization
    pass 