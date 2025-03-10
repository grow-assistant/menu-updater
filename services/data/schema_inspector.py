"""
Schema Inspector for the Swoop AI Conversational Query Flow.

This module provides advanced schema introspection, metadata caching, and 
relationship discovery to enhance database operations and query optimization.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Set, Union
import pandas as pd
import time
import threading
import json
from datetime import datetime, timedelta
import re
import traceback

from sqlalchemy import create_engine, inspect, MetaData, Table, Column, select, func
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class SchemaInspector:
    """
    Provides advanced schema introspection and metadata caching services.
    
    Features:
    - Database schema discovery and caching
    - Table relationship detection
    - Query optimization recommendations
    - Schema change monitoring
    - Entity relationship mapping
    """
    
    def __init__(self, connection_string: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the schema inspector.
        
        Args:
            connection_string: Database connection string
            config: Optional configuration dictionary with settings
        """
        self.connection_string = connection_string
        self.config = config or {}
        
        # Initialize engine
        self.engine = create_engine(connection_string)
        
        # Cache settings
        cache_ttl_hours = self.config.get("schema_cache_ttl_hours", 24)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # Initialize caches
        self.table_cache = {}  # {table_name: {columns, indices, pk, fk, etc.}}
        self.relationship_cache = {}  # {(table1, table2): relationship_info}
        self.usage_stats = {}  # {table_name: {last_accessed, access_count}}
        self.column_stats_cache = {}  # {table.column: {min, max, avg, distinct_count}}
        
        # Cache timestamps
        self.last_full_refresh = None
        self.table_refresh_times = {}  # {table_name: last_refresh_time}
        
        # Thread safety
        self._cache_lock = threading.RLock()
        
        # Preload common tables if specified
        preload_tables = self.config.get("preload_tables", [])
        if preload_tables:
            for table_name in preload_tables:
                try:
                    self.get_table_metadata(table_name, refresh=True)
                except Exception as e:
                    logger.warning(f"Failed to preload table {table_name}: {e}")
        
        logger.info(f"SchemaInspector initialized with cache TTL of {cache_ttl_hours} hours")
    
    def get_table_metadata(self, table_name: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete metadata for a specific table.
        
        Args:
            table_name: Name of the table
            refresh: Whether to force a refresh from database
            
        Returns:
            Dict with table metadata
        """
        with self._cache_lock:
            current_time = datetime.now()
            
            # Check if we have valid cached metadata
            if (not refresh and 
                table_name in self.table_cache and
                table_name in self.table_refresh_times and
                self.table_refresh_times[table_name] + self.cache_ttl > current_time):
                
                # Update usage stats
                if table_name not in self.usage_stats:
                    self.usage_stats[table_name] = {"access_count": 0, "last_accessed": None}
                
                self.usage_stats[table_name]["access_count"] += 1
                self.usage_stats[table_name]["last_accessed"] = current_time
                
                return self.table_cache[table_name]
        
        # Need to fetch from database
        try:
            inspector = inspect(self.engine)
            
            # Get columns
            columns = []
            for col in inspector.get_columns(table_name):
                column_info = {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                    "primary_key": col.get("primary_key", False),
                    "autoincrement": col.get("autoincrement", False),
                    "comment": col.get("comment")
                }
                columns.append(column_info)
            
            # Get primary key
            pk = inspector.get_pk_constraint(table_name)
            primary_keys = pk.get("constrained_columns", [])
            
            # Get foreign keys
            foreign_keys = []
            for fk in inspector.get_foreign_keys(table_name):
                fk_info = {
                    "name": fk.get("name"),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns"),
                    "constrained_columns": fk.get("constrained_columns")
                }
                foreign_keys.append(fk_info)
            
            # Get indices
            indices = []
            for idx in inspector.get_indexes(table_name):
                idx_info = {
                    "name": idx.get("name"),
                    "unique": idx.get("unique", False),
                    "columns": idx.get("column_names", [])
                }
                indices.append(idx_info)
            
            # Get constraints (check, unique)
            constraints = []
            # Note: SQLAlchemy doesn't have a direct method for check constraints
            # For specific databases like PostgreSQL, you can use specific methods
            
            # Compile schema info
            table_metadata = {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indices": indices,
                "constraints": constraints
            }
            
            # Additional metadata if available
            try:
                # Try to get row count estimate (this may not work on all databases)
                with self.engine.connect() as conn:
                    count_query = select(func.count()).select_from(Table(table_name, MetaData(), autoload_with=self.engine))
                    row_count = conn.execute(count_query).scalar() or 0
                    table_metadata["row_count_estimate"] = row_count
            except Exception as e:
                logger.debug(f"Could not get row count for {table_name}: {e}")
                table_metadata["row_count_estimate"] = None
            
            # Cache the result
            with self._cache_lock:
                self.table_cache[table_name] = table_metadata
                self.table_refresh_times[table_name] = datetime.now()
                
                # Initialize usage stats if not present
                if table_name not in self.usage_stats:
                    self.usage_stats[table_name] = {"access_count": 0, "last_accessed": None}
                
                self.usage_stats[table_name]["access_count"] += 1
                self.usage_stats[table_name]["last_accessed"] = datetime.now()
            
            return table_metadata
            
        except Exception as e:
            logger.error(f"Error getting metadata for table {table_name}: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "table_name": table_name}
    
    def get_column_statistics(self, 
                             table_name: str, 
                             column_name: str, 
                             refresh: bool = False) -> Dict[str, Any]:
        """
        Get statistics for a specific column.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            refresh: Whether to force a refresh from database
            
        Returns:
            Dict with column statistics
        """
        cache_key = f"{table_name}.{column_name}"
        
        with self._cache_lock:
            current_time = datetime.now()
            
            # Check if we have valid cached stats
            if (not refresh and 
                cache_key in self.column_stats_cache and
                self.column_stats_cache[cache_key].get("refresh_time") and
                self.column_stats_cache[cache_key]["refresh_time"] + self.cache_ttl > current_time):
                
                return self.column_stats_cache[cache_key]
        
        # Need to fetch from database
        try:
            # Get column type from metadata
            table_metadata = self.get_table_metadata(table_name)
            column_info = next((c for c in table_metadata["columns"] if c["name"] == column_name), None)
            
            if not column_info:
                raise ValueError(f"Column {column_name} not found in table {table_name}")
            
            column_type = column_info["type"]
            
            # Initialize statistics dict
            stats = {
                "table_name": table_name,
                "column_name": column_name,
                "type": column_type,
                "refresh_time": datetime.now()
            }
            
            # For numeric columns, calculate min, max, avg
            # For string columns, calculate length stats, sample values
            # For date columns, calculate date range
            
            with self.engine.connect() as conn:
                if "int" in column_type.lower() or "float" in column_type.lower() or "double" in column_type.lower() or "decimal" in column_type.lower():
                    # Numeric column
                    t = Table(table_name, MetaData(), autoload_with=self.engine)
                    c = getattr(t.c, column_name)
                    
                    # Count, min, max, avg
                    query = select(
                        func.count(c).label("count"),
                        func.min(c).label("min"),
                        func.max(c).label("max"),
                        func.avg(c).label("avg"),
                        func.count(func.distinct(c)).label("distinct_count")
                    )
                    
                    result = conn.execute(query).first()
                    if result:
                        stats.update({
                            "count": result.count,
                            "min": result.min,
                            "max": result.max,
                            "avg": result.avg,
                            "distinct_count": result.distinct_count,
                            "null_count": table_metadata.get("row_count_estimate", 0) - result.count if table_metadata.get("row_count_estimate") else None
                        })
                
                elif "char" in column_type.lower() or "text" in column_type.lower() or "string" in column_type.lower():
                    # String column
                    t = Table(table_name, MetaData(), autoload_with=self.engine)
                    c = getattr(t.c, column_name)
                    
                    # Count, distinct count, avg length
                    query = select(
                        func.count(c).label("count"),
                        func.count(func.distinct(c)).label("distinct_count")
                    )
                    
                    result = conn.execute(query).first()
                    if result:
                        stats.update({
                            "count": result.count,
                            "distinct_count": result.distinct_count,
                            "null_count": table_metadata.get("row_count_estimate", 0) - result.count if table_metadata.get("row_count_estimate") else None
                        })
                    
                    # Sample values (top 10 most frequent)
                    try:
                        sample_query = select(c, func.count(c).label("count")) \
                            .group_by(c) \
                            .order_by(func.count(c).desc()) \
                            .limit(10)
                        
                        samples = []
                        for row in conn.execute(sample_query):
                            samples.append({"value": row[0], "count": row[1]})
                        
                        stats["frequent_values"] = samples
                    except:
                        # This might fail on some databases
                        pass
                
                elif "date" in column_type.lower() or "time" in column_type.lower():
                    # Date/time column
                    t = Table(table_name, MetaData(), autoload_with=self.engine)
                    c = getattr(t.c, column_name)
                    
                    # Count, min, max dates
                    query = select(
                        func.count(c).label("count"),
                        func.min(c).label("min_date"),
                        func.max(c).label("max_date"),
                        func.count(func.distinct(c)).label("distinct_count")
                    )
                    
                    result = conn.execute(query).first()
                    if result:
                        stats.update({
                            "count": result.count,
                            "min_date": result.min_date,
                            "max_date": result.max_date,
                            "distinct_count": result.distinct_count,
                            "null_count": table_metadata.get("row_count_estimate", 0) - result.count if table_metadata.get("row_count_estimate") else None
                        })
                
                else:
                    # Other type - just get counts
                    t = Table(table_name, MetaData(), autoload_with=self.engine)
                    c = getattr(t.c, column_name)
                    
                    query = select(
                        func.count(c).label("count"),
                        func.count(func.distinct(c)).label("distinct_count")
                    )
                    
                    result = conn.execute(query).first()
                    if result:
                        stats.update({
                            "count": result.count,
                            "distinct_count": result.distinct_count,
                            "null_count": table_metadata.get("row_count_estimate", 0) - result.count if table_metadata.get("row_count_estimate") else None
                        })
            
            # Cache the result
            with self._cache_lock:
                self.column_stats_cache[cache_key] = stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics for column {table_name}.{column_name}: {e}")
            logger.error(traceback.format_exc())
            return {
                "error": str(e), 
                "table_name": table_name,
                "column_name": column_name
            }
    
    def discover_relationships(self, 
                              start_table: Optional[str] = None, 
                              max_depth: int = 2) -> Dict[str, Any]:
        """
        Discover table relationships in the database, either from a specific
        table or across the entire schema.
        
        Args:
            start_table: Optional starting table (if None, discover all)
            max_depth: Maximum depth for relationship traversal
            
        Returns:
            Dict with relationship information
        """
        result = {
            "nodes": [],  # Tables
            "edges": [],  # Relationships
            "discovered_at": datetime.now().isoformat()
        }
        
        try:
            # Get list of tables
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            tables_to_process = [start_table] if start_table else all_tables
            processed_tables = set()
            
            # Process each table
            for depth in range(max_depth):
                next_level_tables = []
                
                for table_name in tables_to_process:
                    if table_name in processed_tables:
                        continue
                    
                    processed_tables.add(table_name)
                    
                    # Get table metadata
                    table_meta = self.get_table_metadata(table_name)
                    
                    # Add table node if not already added
                    if not any(n["id"] == table_name for n in result["nodes"]):
                        node = {
                            "id": table_name,
                            "label": table_name,
                            "properties": {
                                "columns": len(table_meta["columns"]),
                                "primary_keys": table_meta["primary_keys"],
                                "row_count": table_meta.get("row_count_estimate")
                            }
                        }
                        result["nodes"].append(node)
                    
                    # Add foreign key relationships
                    for fk in table_meta["foreign_keys"]:
                        referred_table = fk["referred_table"]
                        
                        # Add to next level for processing
                        if referred_table not in processed_tables:
                            next_level_tables.append(referred_table)
                        
                        # Add relationship edge
                        edge_id = f"{table_name}_to_{referred_table}"
                        if not any(e["id"] == edge_id for e in result["edges"]):
                            edge = {
                                "id": edge_id,
                                "source": table_name,
                                "target": referred_table,
                                "label": "references",
                                "properties": {
                                    "source_columns": fk["constrained_columns"],
                                    "target_columns": fk["referred_columns"]
                                }
                            }
                            result["edges"].append(edge)
                
                # Update tables to process for next depth level
                tables_to_process = next_level_tables
                
                # If no more tables to process, we're done
                if not tables_to_process:
                    break
            
            return result
            
        except Exception as e:
            logger.error(f"Error discovering relationships: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "nodes": [], "edges": []}
    
    def get_tables_by_column_pattern(self, 
                                    column_pattern: str, 
                                    case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Find tables containing columns that match a pattern.
        
        Args:
            column_pattern: Regex pattern to match column names
            case_sensitive: Whether the match should be case sensitive
            
        Returns:
            List of matching tables with column information
        """
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(column_pattern, flags)
        
        try:
            # Get list of tables
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            for table_name in all_tables:
                # Check columns in this table
                columns = inspector.get_columns(table_name)
                matching_columns = [
                    {
                        "name": col["name"],
                        "type": str(col["type"])
                    }
                    for col in columns if pattern.search(col["name"])
                ]
                
                if matching_columns:
                    matches.append({
                        "table_name": table_name,
                        "matching_columns": matching_columns
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"Error finding tables by column pattern: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def suggest_join_conditions(self, 
                               left_table: str, 
                               right_table: str) -> List[Dict[str, Any]]:
        """
        Suggest possible join conditions between two tables.
        
        Args:
            left_table: Left table name
            right_table: Right table name
            
        Returns:
            List of suggested join conditions
        """
        suggestions = []
        
        try:
            # Get metadata for both tables
            left_meta = self.get_table_metadata(left_table)
            right_meta = self.get_table_metadata(right_table)
            
            # 1. Check explicit foreign keys
            for fk in left_meta["foreign_keys"]:
                if fk["referred_table"] == right_table:
                    suggestions.append({
                        "type": "foreign_key",
                        "left_table": left_table,
                        "right_table": right_table,
                        "left_columns": fk["constrained_columns"],
                        "right_columns": fk["referred_columns"],
                        "confidence": "high"
                    })
            
            # Check reverse direction too
            for fk in right_meta["foreign_keys"]:
                if fk["referred_table"] == left_table:
                    suggestions.append({
                        "type": "foreign_key",
                        "left_table": left_table,
                        "right_table": right_table,
                        "left_columns": fk["referred_columns"],
                        "right_columns": fk["constrained_columns"],
                        "confidence": "high"
                    })
            
            # 2. Name-based heuristic matches if no FK found
            if not suggestions:
                # Check for columns with same name in both tables
                left_columns = {c["name"].lower(): c for c in left_meta["columns"]}
                right_columns = {c["name"].lower(): c for c in right_meta["columns"]}
                
                # Common column names
                common_columns = set(left_columns.keys()) & set(right_columns.keys())
                
                # Filter by likely join columns (id fields, etc.)
                likely_join_columns = [
                    col for col in common_columns
                    if "id" in col.lower() or  # id fields
                       "key" in col.lower() or  # key fields
                       col.lower() == left_table.lower() or  # table name matches column
                       col.lower() == right_table.lower() or
                       left_columns[col]["primary_key"] or  # primary key
                       right_columns[col]["primary_key"]
                ]
                
                for col in likely_join_columns:
                    suggestions.append({
                        "type": "name_match",
                        "left_table": left_table,
                        "right_table": right_table,
                        "left_columns": [col],
                        "right_columns": [col],
                        "confidence": "medium" if "id" in col.lower() or "key" in col.lower() else "low"
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting join conditions: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def generate_query_hints(self, query: str) -> Dict[str, Any]:
        """
        Analyze a SQL query and generate optimization hints.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dict with optimization hints
        """
        hints = {
            "tables_referenced": [],
            "suggested_indices": [],
            "potential_issues": [],
            "optimization_suggestions": []
        }
        
        try:
            # Very basic SQL parsing to extract table names
            # A real implementation would use a proper SQL parser
            query_lower = query.lower()
            
            # Extract table names after FROM and JOIN clauses
            # This is a simplistic approach - real SQL parsing is more complex
            from_pattern = r"from\s+([a-zA-Z0-9_]+)"
            join_pattern = r"join\s+([a-zA-Z0-9_]+)"
            
            tables = set()
            tables.update(re.findall(from_pattern, query_lower))
            tables.update(re.findall(join_pattern, query_lower))
            
            hints["tables_referenced"] = list(tables)
            
            # Check if we know these tables
            unknown_tables = []
            for table in tables:
                if table not in self.table_cache:
                    try:
                        self.get_table_metadata(table)
                    except:
                        unknown_tables.append(table)
            
            if unknown_tables:
                hints["potential_issues"].append({
                    "type": "unknown_tables",
                    "tables": unknown_tables,
                    "message": f"Tables not found in schema: {', '.join(unknown_tables)}"
                })
            
            # Check for WHERE clauses that might benefit from indices
            where_pattern = r"where\s+(.+?)(?:order by|group by|limit|$)"
            where_matches = re.search(where_pattern, query_lower)
            if where_matches:
                where_clause = where_matches.group(1)
                
                # Extract potential column names from WHERE
                # This is simplistic - a real implementation would be more sophisticated
                column_pattern = r"([a-zA-Z0-9_]+)\s*(?:=|>|<|>=|<=|like|in)"
                potential_columns = re.findall(column_pattern, where_clause)
                
                # Check if these columns have indices
                for table in tables:
                    if table in self.table_cache:
                        table_meta = self.table_cache[table]
                        
                        # Get list of indexed columns
                        indexed_columns = set()
                        for idx in table_meta.get("indices", []):
                            indexed_columns.update(idx.get("columns", []))
                        
                        # Check if WHERE columns are indexed
                        for column in potential_columns:
                            if column not in indexed_columns and any(c["name"] == column for c in table_meta.get("columns", [])):
                                hints["suggested_indices"].append({
                                    "table": table,
                                    "column": column,
                                    "reason": f"Used in WHERE clause: {column} in table {table}"
                                })
            
            # Check if query has a LIMIT but no ORDER BY
            if "limit" in query_lower and "order by" not in query_lower:
                hints["potential_issues"].append({
                    "type": "missing_order_by",
                    "message": "Query contains LIMIT but no ORDER BY clause. Results may be inconsistent."
                })
            
            # Check if query might benefit from pagination
            row_count_estimates = []
            for table in tables:
                if table in self.table_cache and "row_count_estimate" in self.table_cache[table]:
                    row_count_estimates.append(self.table_cache[table]["row_count_estimate"])
            
            if row_count_estimates and max(row_count_estimates) > 10000 and "limit" not in query_lower:
                hints["optimization_suggestions"].append({
                    "type": "pagination",
                    "message": "Consider adding pagination (LIMIT/OFFSET) for large result sets."
                })
            
            return hints
            
        except Exception as e:
            logger.error(f"Error generating query hints: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), **hints}
    
    def refresh_schema_cache(self) -> Dict[str, Any]:
        """
        Refresh the entire schema cache.
        
        Returns:
            Dict with refresh results
        """
        result = {
            "tables_refreshed": 0,
            "errors": [],
            "started_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        try:
            # Get list of all tables
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            # Refresh each table
            for table_name in all_tables:
                try:
                    self.get_table_metadata(table_name, refresh=True)
                    result["tables_refreshed"] += 1
                except Exception as e:
                    result["errors"].append({
                        "table": table_name,
                        "error": str(e)
                    })
            
            self.last_full_refresh = datetime.now()
            result["completed_at"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Error refreshing schema cache: {e}")
            logger.error(traceback.format_exc())
            result["errors"].append({"error": str(e)})
            result["completed_at"] = datetime.now().isoformat()
            return result
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the schema inspector.
        
        Returns:
            Dict with health status information
        """
        status = {
            "service": "schema_inspector",
            "status": "ok",
            "connection_test": True,
            "cached_tables": len(self.table_cache),
            "last_full_refresh": self.last_full_refresh.isoformat() if self.last_full_refresh else None,
            "column_stats_cached": len(self.column_stats_cache)
        }
        
        # Test connection
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            status["status"] = "error"
            status["connection_test"] = False
            status["error"] = str(e)
            logger.error(f"Schema inspector health check failed: {e}")
        
        # Check cache age
        if self.last_full_refresh:
            age = datetime.now() - self.last_full_refresh
            status["cache_age_hours"] = age.total_seconds() / 3600
            
            if age > self.cache_ttl:
                status["cache_status"] = "stale"
            else:
                status["cache_status"] = "fresh"
        else:
            status["cache_status"] = "empty"
        
        return status 