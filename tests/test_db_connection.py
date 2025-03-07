"""
Database Connection Performance Test

This script tests various aspects of database connection and query performance:
1. Connection establishment time
2. Query execution time for simple queries
3. Connection pooling efficiency
4. Parameterized query performance
"""
import os
import sys
import time
import logging
import statistics
from pathlib import Path
from datetime import datetime
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, exc, pool

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_connection_test")

# Load environment variables
load_dotenv()

def load_config():
    """Load the application configuration."""
    config_path = os.path.join(project_root, "config", "config.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Replace environment variables
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = replace_env_vars(value)
            return obj
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            # Handle default values with colon syntax
            if ":-" in env_var:
                env_var, default_value = env_var.split(":-", 1)
            else:
                default_value = ""
            env_value = os.environ.get(env_var, default_value)
            if env_value is None:
                logger.warning(f"Environment variable {env_var} not found")
                return default_value
            return env_value
        else:
            return obj
    
    # Apply recursive replacement
    config = replace_env_vars(config)
    
    return config

def test_connection_establishment(connection_string, iterations=5):
    """Test how long it takes to establish a database connection."""
    logger.info(f"Testing connection establishment time ({iterations} iterations)...")
    connection_times = []
    
    for i in range(iterations):
        start_time = time.time()
        try:
            # Create a new engine without pooling for each test
            engine = create_engine(connection_string, poolclass=pool.NullPool)
            # Establish and immediately close connection
            with engine.connect() as conn:
                # Just create a connection
                pass
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            logger.info(f"  Connection {i+1}/{iterations}: {connection_time:.4f}s")
        except Exception as e:
            logger.error(f"  Connection error on iteration {i+1}: {str(e)}")
    
    if connection_times:
        avg_time = sum(connection_times) / len(connection_times)
        median_time = statistics.median(connection_times)
        logger.info(f"Connection establishment stats:")
        logger.info(f"  Average: {avg_time:.4f}s")
        logger.info(f"  Median: {median_time:.4f}s")
        logger.info(f"  Min: {min(connection_times):.4f}s")
        logger.info(f"  Max: {max(connection_times):.4f}s")
        return avg_time
    return None

def test_simple_query(connection_string, iterations=5):
    """Test how long it takes to run a simple query."""
    logger.info(f"Testing simple query execution time ({iterations} iterations)...")
    query_times = []
    
    # Use a connection pool for query tests
    engine = create_engine(connection_string)
    
    for i in range(iterations):
        start_time = time.time()
        try:
            with engine.connect() as conn:
                # Execute a simple COUNT query
                result = conn.execute(text("SELECT COUNT(*) FROM orders"))
                count = result.scalar()
            query_time = time.time() - start_time
            query_times.append(query_time)
            logger.info(f"  Query {i+1}/{iterations}: {query_time:.4f}s, Result: {count}")
        except Exception as e:
            logger.error(f"  Query error on iteration {i+1}: {str(e)}")
    
    if query_times:
        avg_time = sum(query_times) / len(query_times)
        median_time = statistics.median(query_times)
        logger.info(f"Query execution stats:")
        logger.info(f"  Average: {avg_time:.4f}s")
        logger.info(f"  Median: {median_time:.4f}s")
        logger.info(f"  Min: {min(query_times):.4f}s")
        logger.info(f"  Max: {max(query_times):.4f}s")
        return avg_time
    return None

def test_connection_pool(connection_string, pool_size=5, iterations=10):
    """Test connection pool performance."""
    logger.info(f"Testing connection pool performance (pool_size={pool_size}, {iterations} iterations)...")
    
    # Create an engine with connection pooling
    engine = create_engine(
        connection_string,
        pool_size=pool_size,
        max_overflow=2
    )
    
    # Warm up the pool
    logger.info("Warming up connection pool...")
    connections = []
    try:
        for _ in range(pool_size):
            connections.append(engine.connect())
        
        # Close connections to return them to the pool
        for conn in connections:
            conn.close()
    except Exception as e:
        logger.error(f"Error warming up pool: {str(e)}")
        # Make sure to close any open connections
        for conn in connections:
            try:
                conn.close()
            except:
                pass
    
    # Test pooled connections
    logger.info("Testing pooled connection queries...")
    query_times = []
    
    for i in range(iterations):
        start_time = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM orders"))
                count = result.scalar()
            query_time = time.time() - start_time
            query_times.append(query_time)
            logger.info(f"  Pooled query {i+1}/{iterations}: {query_time:.4f}s, Result: {count}")
        except Exception as e:
            logger.error(f"  Pooled query error on iteration {i+1}: {str(e)}")
    
    if query_times:
        avg_time = sum(query_times) / len(query_times)
        median_time = statistics.median(query_times)
        logger.info(f"Pooled connection stats:")
        logger.info(f"  Average: {avg_time:.4f}s")
        logger.info(f"  Median: {median_time:.4f}s")
        logger.info(f"  Min: {min(query_times):.4f}s")
        logger.info(f"  Max: {max(query_times):.4f}s")
        return avg_time
    return None

def test_parametrized_query(connection_string, iterations=5):
    """Test parameterized query performance."""
    logger.info(f"Testing parameterized query performance ({iterations} iterations)...")
    query_times = []
    
    # Use a connection pool for query tests
    engine = create_engine(connection_string)
    
    # Test date for our query
    test_date = '2025-02-21'
    
    # First, let's check what the status values actually are
    try:
        with engine.connect() as conn:
            # Get status values
            status_query = text("SELECT DISTINCT status FROM orders LIMIT 10")
            status_result = conn.execute(status_query)
            statuses = [row[0] for row in status_result]
            logger.info(f"Available status values: {statuses}")
            
            # Use first status value for testing if available
            status_value = statuses[0] if statuses else 1  # Default to 1 if no statuses found
    except Exception as e:
        logger.error(f"Error getting status values: {str(e)}")
        status_value = 1  # Default to 1
    
    for i in range(iterations):
        start_time = time.time()
        try:
            with engine.connect() as conn:
                # Execute a parametrized query similar to the slow one in logs
                # Using numeric status value instead of string
                query = text("""
                SELECT COUNT(id) 
                FROM orders 
                WHERE (updated_at - INTERVAL '7 hours')::date = :query_date 
                AND status = :status_value
                """)
                result = conn.execute(query, {"query_date": test_date, "status_value": status_value})
                count = result.scalar()
            query_time = time.time() - start_time
            query_times.append(query_time)
            logger.info(f"  Parametrized query {i+1}/{iterations}: {query_time:.4f}s, Result: {count}")
        except Exception as e:
            logger.error(f"  Parametrized query error on iteration {i+1}: {str(e)}")
    
    if query_times:
        avg_time = sum(query_times) / len(query_times)
        median_time = statistics.median(query_times)
        logger.info(f"Parametrized query stats:")
        logger.info(f"  Average: {avg_time:.4f}s")
        logger.info(f"  Median: {median_time:.4f}s")
        logger.info(f"  Min: {min(query_times):.4f}s")
        logger.info(f"  Max: {max(query_times):.4f}s")
        return avg_time
    return None

def test_index_usage(connection_string):
    """Check if the relevant indexes exist and are being used."""
    logger.info("Checking for indexes on the orders table...")
    
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            # Check for existing indexes
            indexes_query = text("""
            SELECT
                indexname,
                indexdef
            FROM
                pg_indexes
            WHERE
                tablename = 'orders'
            """)
            
            indexes_result = conn.execute(indexes_query)
            indexes = list(indexes_result)
            
            if not indexes:
                logger.warning("No indexes found on the orders table!")
            else:
                logger.info(f"Found {len(indexes)} indexes on orders table:")
                for idx in indexes:
                    logger.info(f"  {idx.indexname}: {idx.indexdef}")
                
                # Look for indexes on updated_at and status columns
                updated_at_indexed = any('updated_at' in idx.indexdef for idx in indexes)
                status_indexed = any('status' in idx.indexdef for idx in indexes)
                
                if not updated_at_indexed:
                    logger.warning("No index found for 'updated_at' column - could cause slow queries!")
                if not status_indexed:
                    logger.warning("No index found for 'status' column - could cause slow queries!")
            
            # Get status values
            status_query = text("SELECT DISTINCT status FROM orders LIMIT 5")
            status_result = conn.execute(status_query)
            statuses = [row[0] for row in status_result]
            status_value = statuses[0] if statuses else 1  # Default to 1
                
            # Run EXPLAIN on the slow query
            logger.info("Running EXPLAIN on the slow query...")
            explain_query = text("""
            EXPLAIN ANALYZE
            SELECT COUNT(id) 
            FROM orders 
            WHERE (updated_at - INTERVAL '7 hours')::date = '2025-02-21' 
            AND status = :status_value
            """)
            
            explain_result = conn.execute(explain_query, {"status_value": status_value})
            explain_output = list(explain_result)
            
            logger.info("Query execution plan:")
            for line in explain_output:
                logger.info(f"  {line[0]}")
                
            # Check for sequential scans in the output
            has_seq_scan = any('Seq Scan' in line[0] for line in explain_output)
            if has_seq_scan:
                logger.warning("Query is using a sequential scan! This indicates missing or unused indexes.")
                
            return True
            
    except Exception as e:
        logger.error(f"Error checking indexes: {str(e)}")
        return False

def suggest_improvements(config, connection_avg, query_avg, pooled_avg, param_avg):
    """Suggest performance improvements based on test results."""
    logger.info("\n=== Performance Improvement Suggestions ===")
    
    suggestions = []
    
    # Connection establishment suggestions
    if connection_avg > 0.5:
        suggestions.append("Connection establishment is slow (>0.5s). Consider:") 
        suggestions.append("- Check network latency to database server")
        suggestions.append("- Review database server configuration")
        suggestions.append("- Use persistent connection pooling")
    
    # Query performance suggestions
    if query_avg > 0.2:
        suggestions.append("Simple queries are slow (>0.2s). Consider:")
        suggestions.append("- Adding appropriate indexes")
        suggestions.append("- Analyzing query plans with EXPLAIN ANALYZE")
        suggestions.append("- Checking database server load")
    
    # Connection pool suggestions
    if pooled_avg and query_avg and pooled_avg > query_avg * 1.2:  # If pooled connections are 20% slower
        suggestions.append("Connection pooling is not effective. Consider:")
        suggestions.append("- Reviewing pool size (currently: {})".format(
            config.get("database", {}).get("pool_size", "N/A")))
        suggestions.append("- Adjusting max_overflow setting")
        suggestions.append("- Checking for connection leaks")
    
    # Parameterized query suggestions
    if param_avg and param_avg > 0.5:
        suggestions.append("Parameterized queries are slow (>0.5s). Consider:")
        suggestions.append("- Adding composite indexes for the WHERE clause")
        suggestions.append("- Ensuring date expression ((updated_at - INTERVAL '7 hours')::date) isn't preventing index usage")
        suggestions.append("- Creating a functional index if needed")
    
    # Check current timeout settings
    timeout = config.get("database", {}).get("default_timeout", "N/A")
    suggestions.append(f"Current DB timeout setting: {timeout}s - Adjust based on average query time")
    
    # Output suggestions
    if not suggestions:
        logger.info("Performance looks good! No specific suggestions.")
    else:
        for suggestion in suggestions:
            logger.info(suggestion)

def main():
    """Run the database connection tests."""
    logger.info("Starting database connection performance tests")
    
    # Load configuration
    config = load_config()
    connection_string = config["database"]["connection_string"]
    
    # Display current database settings
    logger.info("Current database configuration:")
    logger.info(f"  Pool size: {config['database'].get('pool_size', 'Default')}")
    logger.info(f"  Max overflow: {config['database'].get('max_overflow', 'Default')}")
    logger.info(f"  Timeout: {config['database'].get('default_timeout', 'Default')}s")
    logger.info(f"  Pool recycle: {config['database'].get('pool_recycle', 'Default')}s")
    
    # Run tests
    connection_avg = test_connection_establishment(connection_string)
    query_avg = test_simple_query(connection_string)
    pooled_avg = test_connection_pool(connection_string)
    param_avg = test_parametrized_query(connection_string)
    
    # Check indexes
    test_index_usage(connection_string)
    
    # Suggest improvements
    suggest_improvements(config, connection_avg, query_avg, pooled_avg, param_avg)
    
    logger.info("Database performance testing completed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 