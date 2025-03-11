"""
Enhanced Data Access Layer for the Swoop AI Conversational Query Flow.

This package provides a robust data access layer with:
- Connection pooling and management
- Query caching and optimization
- Performance monitoring
- Transaction support
- Schema introspection capabilities
"""

from services.data.db_connection_manager import DatabaseConnectionManager
from services.data.query_cache_manager import QueryCacheManager
from services.data.enhanced_data_access import EnhancedDataAccess, get_data_access

__all__ = [
    'DatabaseConnectionManager',
    'QueryCacheManager',
    'EnhancedDataAccess',
    'get_data_access',
] 