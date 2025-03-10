"""
Query Cache Manager for optimizing database performance by caching query results.

This module provides a configurable caching layer that reduces database load
and improves response times for frequently accessed data.
"""
import logging
import hashlib
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class QueryCacheManager:
    """
    Manages caching of database query results to improve performance.
    
    Features:
    - Time-based cache expiration
    - Memory usage limits
    - Cache statistics and monitoring
    - Partial result caching
    - Cache invalidation patterns
    - Configurable cache strategies
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the query cache manager.
        
        Args:
            config: Dictionary containing configuration options including:
                - enabled: Whether caching is enabled (default: True)
                - default_ttl: Default time-to-live in seconds (default: 300)
                - max_size: Maximum number of cache entries (default: 1000)
                - max_memory_mb: Maximum memory usage in MB (default: 100)
                - min_query_time: Minimum query execution time to cache (default: 0.1)
                - cacheable_tables: List of tables whose queries can be cached
                - uncacheable_tables: List of tables whose queries should not be cached
        """
        cache_config = config.get("cache", {})
        
        # Cache settings
        self.enabled = cache_config.get("enabled", True)
        self.default_ttl = cache_config.get("default_ttl", 300)  # 5 minutes
        self.max_size = cache_config.get("max_size", 1000)
        self.max_memory_mb = cache_config.get("max_memory_mb", 100)
        self.min_query_time = cache_config.get("min_query_time", 0.1)  # 100ms
        
        # Tables that can/cannot be cached
        self.cacheable_tables = set(cache_config.get("cacheable_tables", []))
        self.uncacheable_tables = set(cache_config.get("uncacheable_tables", []))
        
        # Default to false for non-select queries
        self.cache_non_select = cache_config.get("cache_non_select", False)
        
        # Cache storage
        self._cache = {}  # {key: {"data": data, "timestamp": timestamp, "expires": expires}}
        self._memory_usage = 0  # Estimated memory usage in bytes
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "inserts": 0,
            "evictions": 0,
            "invalidations": 0,
            "memory_usage_bytes": 0,
            "hit_rate": 0.0
        }
        
        # Thread safety
        self._cache_lock = threading.RLock()
        
        # Callback for cache invalidation
        self.invalidation_callbacks = []
        
        logger.info(f"Initialized QueryCacheManager with max_size={self.max_size}, "
                   f"default_ttl={self.default_ttl}s, enabled={self.enabled}")
    
    def get(self, query: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        """
        Get a cached query result if available.
        
        Args:
            query: The SQL query string
            params: Query parameters
            
        Returns:
            Tuple of (cache_hit, result)
                - cache_hit: True if cache hit, False if miss
                - result: The cached result if hit, None if miss
        """
        if not self.enabled:
            return False, None
        
        cache_key = self._generate_cache_key(query, params)
        
        with self._cache_lock:
            cache_entry = self._cache.get(cache_key)
            
            if not cache_entry:
                self.stats["misses"] += 1
                self._update_hit_rate()
                return False, None
            
            # Check if expired
            if cache_entry["expires"] < time.time():
                self._evict_entry(cache_key)
                self.stats["misses"] += 1
                self._update_hit_rate()
                return False, None
            
            # Update access time for LRU strategy
            cache_entry["last_accessed"] = time.time()
            
            self.stats["hits"] += 1
            self._update_hit_rate()
            
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return True, cache_entry["data"]
    
    def set(self, 
            query: str, 
            params: Optional[Dict[str, Any]], 
            result: Any, 
            is_select: bool,
            execution_time: float,
            ttl: Optional[int] = None) -> bool:
        """
        Store a query result in the cache.
        
        Args:
            query: The SQL query string
            params: Query parameters
            result: The result to cache
            is_select: Whether this was a SELECT query
            execution_time: How long the query took to execute
            ttl: Time-to-live in seconds (None uses default)
            
        Returns:
            True if cached, False if not cached
        """
        if not self.enabled:
            return False
        
        # Don't cache if execution time is too low (query is already fast)
        if execution_time < self.min_query_time:
            return False
        
        # Don't cache non-SELECT queries unless configured to do so
        if not is_select and not self.cache_non_select:
            return False
        
        # Check if query should be cached based on tables
        if not self._should_cache_query(query):
            logger.debug(f"Query not cached due to table restrictions: {query[:50]}...")
            return False
        
        # Use default TTL if not specified
        actual_ttl = ttl if ttl is not None else self.default_ttl
        
        # Set expiration time
        current_time = time.time()
        expires = current_time + actual_ttl
        
        cache_key = self._generate_cache_key(query, params)
        
        # Estimate memory usage of this entry
        entry_size = self._estimate_size(result)
        
        with self._cache_lock:
            # If we need to make room, evict entries
            while (len(self._cache) >= self.max_size or 
                   self._memory_usage + entry_size > self.max_memory_mb * 1024 * 1024):
                self._evict_lru_entry()
            
            # Store in cache
            self._cache[cache_key] = {
                "data": result,
                "timestamp": current_time,
                "expires": expires,
                "last_accessed": current_time,
                "size": entry_size,
                "query": query[:100] + "..." if len(query) > 100 else query
            }
            
            self._memory_usage += entry_size
            self.stats["memory_usage_bytes"] = self._memory_usage
            self.stats["inserts"] += 1
            
            logger.debug(f"Cached query result for {actual_ttl}s: {query[:50]}...")
            
            return True
    
    def invalidate(self, 
                  table_name: Optional[str] = None, 
                  pattern: Optional[str] = None,
                  complete: bool = False) -> int:
        """
        Invalidate cache entries based on criteria.
        
        Args:
            table_name: Invalidate entries for a specific table
            pattern: Invalidate entries matching this pattern
            complete: If True, clear the entire cache
            
        Returns:
            Number of entries invalidated
        """
        with self._cache_lock:
            if complete:
                count = len(self._cache)
                self._cache = {}
                self._memory_usage = 0
                self.stats["memory_usage_bytes"] = 0
                self.stats["invalidations"] += count
                logger.info(f"Completely cleared query cache ({count} entries)")
                
                # Notify callbacks
                self._notify_invalidation_callbacks(None, None, True)
                
                return count
            
            # Invalidate by table or pattern
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                query = entry.get("query", "")
                
                if (table_name and table_name.lower() in query.lower()) or \
                   (pattern and pattern.lower() in query.lower()):
                    keys_to_remove.append(key)
            
            # Remove matching entries
            for key in keys_to_remove:
                self._evict_entry(key)
            
            count = len(keys_to_remove)
            self.stats["invalidations"] += count
            
            if count > 0:
                if table_name:
                    logger.info(f"Invalidated {count} cache entries for table '{table_name}'")
                    # Notify callbacks
                    self._notify_invalidation_callbacks(table_name, pattern, False)
                elif pattern:
                    logger.info(f"Invalidated {count} cache entries matching '{pattern}'")
                    # Notify callbacks
                    self._notify_invalidation_callbacks(None, pattern, False)
            
            return count
    
    def register_invalidation_callback(self, callback: Callable[[Optional[str], Optional[str], bool], None]):
        """
        Register a callback for cache invalidation events.
        
        Args:
            callback: Function to call when cache is invalidated
                     Function signature: callback(table_name, pattern, complete)
        """
        self.invalidation_callbacks.append(callback)
    
    def _notify_invalidation_callbacks(self, 
                                      table_name: Optional[str], 
                                      pattern: Optional[str],
                                      complete: bool):
        """Notify all registered callbacks of a cache invalidation event."""
        for callback in self.invalidation_callbacks:
            try:
                callback(table_name, pattern, complete)
            except Exception as e:
                logger.error(f"Error in cache invalidation callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        with self._cache_lock:
            stats = self.stats.copy()
            stats["entry_count"] = len(self._cache)
            stats["memory_usage_mb"] = self._memory_usage / (1024 * 1024)
            
            # Add size distribution
            if self._cache:
                sizes = [entry["size"] for entry in self._cache.values()]
                stats["min_entry_size"] = min(sizes)
                stats["max_entry_size"] = max(sizes)
                stats["avg_entry_size"] = sum(sizes) / len(sizes)
            else:
                stats["min_entry_size"] = 0
                stats["max_entry_size"] = 0
                stats["avg_entry_size"] = 0
            
            return stats
    
    def _update_hit_rate(self):
        """Update the cache hit rate statistic."""
        total = self.stats["hits"] + self.stats["misses"]
        self.stats["hit_rate"] = (self.stats["hits"] / total * 100) if total > 0 else 0
    
    def _evict_lru_entry(self):
        """Evict the least recently used cache entry."""
        if not self._cache:
            return
        
        # Find the least recently accessed entry
        lru_key = min(self._cache.keys(), 
                      key=lambda k: self._cache[k]["last_accessed"])
        
        self._evict_entry(lru_key)
    
    def _evict_entry(self, key: str):
        """
        Evict a specific cache entry.
        
        Args:
            key: Cache key to evict
        """
        if key in self._cache:
            # Update memory usage
            self._memory_usage -= self._cache[key]["size"]
            
            # Remove from cache
            del self._cache[key]
            
            # Update stats
            self.stats["evictions"] += 1
            self.stats["memory_usage_bytes"] = self._memory_usage
    
    def _generate_cache_key(self, query: str, params: Optional[Dict[str, Any]]) -> str:
        """
        Generate a unique cache key for a query and its parameters.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cache key as a string
        """
        # Normalize query whitespace
        normalized_query = ' '.join(query.split())
        
        # Create a string representation of params
        params_str = json.dumps(params, sort_keys=True) if params else ""
        
        # Combine and hash
        combined = f"{normalized_query}:{params_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _estimate_size(self, obj: Any) -> int:
        """
        Estimate the memory size of an object in bytes.
        
        Args:
            obj: The object to measure
            
        Returns:
            Estimated size in bytes
        """
        if isinstance(obj, pd.DataFrame):
            # Pandas DataFrame size estimation
            return obj.memory_usage(deep=True).sum()
        elif isinstance(obj, (dict, list)):
            # Rough estimation for dictionaries and lists
            return len(json.dumps(obj)) * 2  # Multiply by 2 for overhead
        elif isinstance(obj, str):
            return len(obj) * 2
        elif isinstance(obj, (int, float, bool)):
            return 8
        else:
            # Default estimation
            return 100
    
    def _should_cache_query(self, query: str) -> bool:
        """
        Determine if a query should be cached based on table restrictions.
        
        Args:
            query: The SQL query
            
        Returns:
            True if the query should be cached, False otherwise
        """
        query_lower = query.lower()
        
        # Check for uncacheable tables first
        for table in self.uncacheable_tables:
            if table.lower() in query_lower:
                return False
        
        # If we have a list of cacheable tables, check if any are in the query
        if self.cacheable_tables:
            for table in self.cacheable_tables:
                if table.lower() in query_lower:
                    return True
            # If we have cacheable tables specified and none matched, don't cache
            return False
        
        # Default to cacheable if no restrictions matched
        return True 