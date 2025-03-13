"""
Service Registry proxy module.

This module re-exports the ServiceRegistry from services.utils.service_registry
to maintain compatibility with imports expecting ai_agent.utils.service_registry.
"""

from services.utils.service_registry import ServiceRegistry

# Re-export ServiceRegistry
__all__ = ["ServiceRegistry"] 