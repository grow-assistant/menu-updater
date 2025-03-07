from typing import Dict, Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Registry for microservices."""
    
    _services = {}
    _config = None
    
    @classmethod
    def initialize(cls, config: Dict[str, Any]):
        """Initialize the registry with configuration."""
        cls._config = config
        cls._services = {}
    
    @classmethod
    def register(cls, service_name: str, service_factory: Callable):
        """Register a service factory function."""
        cls._services[service_name] = {
            "factory": service_factory,
            "instance": None,
            "healthy": True
        }
        logger.info(f"Registered service: {service_name}")
    
    @classmethod
    def get_service(cls, service_name: str) -> Any:
        """Get a service instance, creating it if necessary."""
        if service_name not in cls._services:
            raise ValueError(f"Service {service_name} not registered")
        
        service_info = cls._services[service_name]
        
        if service_info["instance"] is None:
            try:
                service_info["instance"] = service_info["factory"](cls._config)
                service_info["healthy"] = True
            except Exception as e:
                service_info["healthy"] = False
                logger.error(f"Failed to initialize service {service_name}: {str(e)}")
                raise
        
        return service_info["instance"]
    
    @classmethod
    def check_health(cls) -> Dict[str, bool]:
        """Check the health of all registered services."""
        health_status = {}
        
        for service_name, service_info in cls._services.items():
            if service_info["instance"] is None:
                try:
                    # Try to initialize the service
                    cls.get_service(service_name)
                    health_status[service_name] = True
                except:
                    health_status[service_name] = False
            else:
                # Check if the service has a health check method
                instance = service_info["instance"]
                if hasattr(instance, "health_check") and callable(instance.health_check):
                    try:
                        health_status[service_name] = instance.health_check()
                    except:
                        health_status[service_name] = False
                else:
                    # Assume healthy if it exists
                    health_status[service_name] = True
        
        return health_status 