"""
Service Initializer for setting up and registering all required services.

This module handles the initialization of application services and
registers them with the ServiceRegistry for access by other components.
"""
import logging
from typing import Dict, Any, List

from services.utils.service_registry import ServiceRegistry
from services.validation.sql_validation_service import SQLValidationService

logger = logging.getLogger(__name__)

def initialize_services(config: Dict[str, Any]) -> List[str]:
    """
    Initialize all required services based on configuration.
    
    Args:
        config: Application configuration dictionary
        
    Returns:
        List of successfully initialized service names
    """
    initialized_services = []
    
    try:
        # Clear any existing services (in case of reinitializing)
        ServiceRegistry.clear()
        
        # Initialize database connection manager if needed
        if "database" in config:
            try:
                from services.data.db_connection_manager import DatabaseConnectionManager
                db_connection_manager = DatabaseConnectionManager(config)
                ServiceRegistry.register("db_connection_manager", db_connection_manager)
                initialized_services.append("db_connection_manager")
                logger.info("Database connection manager initialized and registered")
            except Exception as e:
                logger.error(f"Failed to initialize database connection manager: {str(e)}")
        
        # Initialize SQL Response Validation
        if should_initialize_service(config, "validation", "sql_validation"):
            try:
                sql_validation_service = SQLValidationService(config)
                sql_validation_service.register_service()
                initialized_services.append("sql_validation")
                logger.info("SQL Validation Service initialized and registered")
            except Exception as e:
                logger.error(f"Failed to initialize SQL Validation Service: {str(e)}")
        
        # Initialize Response Generator if needed
        if should_initialize_service(config, "response", "generator"):
            try:
                from services.response.response_generator import ResponseGenerator
                response_generator = ResponseGenerator(config)
                ServiceRegistry.register("response_generator", response_generator)
                initialized_services.append("response_generator")
                logger.info("Response Generator initialized and registered")
            except Exception as e:
                logger.error(f"Failed to initialize Response Generator: {str(e)}")
        
        # Additional service initialization can be added here
        
        logger.info(f"Service initialization complete. Initialized {len(initialized_services)} services.")
        return initialized_services
        
    except Exception as e:
        logger.error(f"Error during service initialization: {str(e)}")
        return initialized_services

def should_initialize_service(config: Dict[str, Any], service_category: str, service_name: str) -> bool:
    """
    Check if a service should be initialized based on configuration.
    
    Args:
        config: Application configuration dictionary
        service_category: Category of the service in config
        service_name: Name of the service
        
    Returns:
        True if the service should be initialized, False otherwise
    """
    # Check if the service is explicitly disabled
    service_config = config.get("services", {}).get(service_category, {})
    
    # If the service has a specific enabled flag
    if service_name in service_config:
        return service_config[service_name].get("enabled", True)
    
    # Otherwise check if the service category is enabled
    return service_config.get("enabled", True)

def health_check() -> Dict[str, bool]:
    """
    Check the health of all registered services.
    
    Returns:
        Dictionary mapping service names to health status
    """
    health_status = {}
    
    services = ServiceRegistry.list_services()
    for service_name, service in services.items():
        try:
            # Check if service has a health_check method
            if hasattr(service, "health_check") and callable(service.health_check):
                health_status[service_name] = service.health_check()
            else:
                # If no health check method, assume service is healthy
                health_status[service_name] = True
        except Exception as e:
            logger.error(f"Health check failed for service {service_name}: {str(e)}")
            health_status[service_name] = False
    
    return health_status 