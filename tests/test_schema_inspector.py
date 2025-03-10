"""
Tests for the Schema Inspector.

These tests validate schema discovery, metadata caching, and query optimization features.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import pytest
import pandas as pd
from datetime import datetime, timedelta
import json
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.schema import Index

from services.data.schema_inspector import SchemaInspector


class TestSchemaInspector(unittest.TestCase):
    """Test cases for the SchemaInspector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:')
        
        # Create a simple schema for testing
        metadata = MetaData()
        
        # Users table
        users = Table('users', metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String(50), nullable=False, unique=True),
            Column('email', String(100), nullable=False),
            Column('created_at', String(50))  # Using string for date to avoid SQLite limitations
        )
        
        # Orders table with foreign key to users
        orders = Table('orders', metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
            Column('amount', Integer, nullable=False),
            Column('order_date', String(50))  # Using string for date to avoid SQLite limitations
        )
        
        # Order items table with foreign key to orders
        order_items = Table('order_items', metadata,
            Column('id', Integer, primary_key=True),
            Column('order_id', Integer, ForeignKey('orders.id'), nullable=False),
            Column('product_name', String(100), nullable=False),
            Column('quantity', Integer, nullable=False),
            Column('item_price', Integer, nullable=False)
        )
        
        # Create tables in the database
        metadata.create_all(self.engine)
        
        # Create indices
        Index('idx_orders_user_id', orders.c.user_id).create(self.engine)
        Index('idx_order_items_order_id', order_items.c.order_id).create(self.engine)
        
        # Insert sample data
        with self.engine.connect() as conn:
            # Insert users
            conn.execute(users.insert().values([
                {"id": 1, "username": "user1", "email": "user1@example.com", "created_at": "2023-01-01"},
                {"id": 2, "username": "user2", "email": "user2@example.com", "created_at": "2023-01-15"}
            ]))
            
            # Insert orders
            conn.execute(orders.insert().values([
                {"id": 1, "user_id": 1, "amount": 100, "order_date": "2023-02-01"},
                {"id": 2, "user_id": 1, "amount": 200, "order_date": "2023-02-15"},
                {"id": 3, "user_id": 2, "amount": 150, "order_date": "2023-03-01"}
            ]))
            
            # Insert order items
            conn.execute(order_items.insert().values([
                {"id": 1, "order_id": 1, "product_name": "Product A", "quantity": 2, "item_price": 50},
                {"id": 2, "order_id": 2, "product_name": "Product B", "quantity": 1, "item_price": 200},
                {"id": 3, "order_id": 3, "product_name": "Product A", "quantity": 3, "item_price": 50}
            ]))
        
        # Create config
        self.config = {
            "schema_cache_ttl_hours": 24,
            "preload_tables": ["users"]
        }
        
        # Initialize inspector with direct engine injection for testing
        self.inspector = SchemaInspector('sqlite:///:memory:', self.config)
        self.inspector.engine = self.engine  # Use our engine with sample data
    
    def test_initialization(self):
        """Test initialization with configuration."""
        self.assertEqual(self.inspector.cache_ttl, timedelta(hours=24))
        self.assertEqual(self.inspector.config, self.config)
    
    def test_get_table_metadata(self):
        """Test retrieval of table metadata."""
        # Get metadata for users table
        users_meta = self.inspector.get_table_metadata("users")
        
        # Verify table properties
        self.assertEqual(users_meta["table_name"], "users")
        self.assertEqual(len(users_meta["columns"]), 4)
        self.assertEqual(users_meta["primary_keys"], ["id"])
        
        # Verify columns
        column_names = [col["name"] for col in users_meta["columns"]]
        self.assertIn("id", column_names)
        self.assertIn("username", column_names)
        self.assertIn("email", column_names)
        self.assertIn("created_at", column_names)
        
        # Verify foreign keys (should be empty for users table)
        self.assertEqual(len(users_meta["foreign_keys"]), 0)
    
    def test_get_table_metadata_with_foreign_keys(self):
        """Test retrieval of table metadata with foreign keys."""
        # Get metadata for orders table (has foreign key to users)
        orders_meta = self.inspector.get_table_metadata("orders")
        
        # Verify foreign keys
        self.assertEqual(len(orders_meta["foreign_keys"]), 1)
        fk = orders_meta["foreign_keys"][0]
        self.assertEqual(fk["referred_table"], "users")
        self.assertEqual(fk["constrained_columns"], ["user_id"])
        self.assertEqual(fk["referred_columns"], ["id"])
    
    def test_metadata_caching(self):
        """Test that metadata is properly cached."""
        # Perform initial request to cache metadata
        users_meta1 = self.inspector.get_table_metadata("users")
        
        # Mock the engine to verify we don't hit the database on second request
        original_engine = self.inspector.engine
        mock_engine = MagicMock()
        self.inspector.engine = mock_engine
        
        # Get metadata again - should use cache
        users_meta2 = self.inspector.get_table_metadata("users")
        
        # Restore original engine
        self.inspector.engine = original_engine
        
        # Verify we didn't call the database
        mock_engine.connect.assert_not_called()
        
        # Verify metadata is the same
        self.assertEqual(users_meta1["table_name"], users_meta2["table_name"])
        self.assertEqual(len(users_meta1["columns"]), len(users_meta2["columns"]))
    
    def test_metadata_refresh(self):
        """Test forced metadata refresh."""
        # Perform initial request to cache metadata
        users_meta1 = self.inspector.get_table_metadata("users")
        
        # Create a spy on the inspect function to verify it's called again
        with patch('sqlalchemy.inspect') as mock_inspect:
            # Setup the mock to return our engine's inspector
            mock_inspector = MagicMock()
            mock_inspector.get_columns.return_value = [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                {"name": "email", "type": "VARCHAR(100)", "nullable": False},
                {"name": "created_at", "type": "VARCHAR(50)", "nullable": True}
            ]
            mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
            mock_inspector.get_foreign_keys.return_value = []
            mock_inspector.get_indexes.return_value = []
            
            mock_inspect.return_value = mock_inspector
            
            # Force refresh
            users_meta2 = self.inspector.get_table_metadata("users", refresh=True)
        
        # Verify inspect was called
        mock_inspect.assert_called_once()
    
    def test_get_column_statistics(self):
        """Test retrieval of column statistics."""
        # Get stats for username column in users table
        username_stats = self.inspector.get_column_statistics("users", "username")
        
        # Verify stats properties
        self.assertEqual(username_stats["table_name"], "users")
        self.assertEqual(username_stats["column_name"], "username")
        self.assertIn("count", username_stats)
        self.assertIn("distinct_count", username_stats)
        
        # Verify counts
        self.assertEqual(username_stats["count"], 2)  # 2 users in sample data
        self.assertEqual(username_stats["distinct_count"], 2)  # All usernames are unique
    
    def test_get_column_statistics_numeric(self):
        """Test retrieval of numeric column statistics."""
        # Get stats for amount column in orders table (numeric)
        amount_stats = self.inspector.get_column_statistics("orders", "amount")
        
        # Verify numeric stats
        self.assertEqual(amount_stats["table_name"], "orders")
        self.assertEqual(amount_stats["column_name"], "amount")
        self.assertIn("min", amount_stats)
        self.assertIn("max", amount_stats)
        self.assertIn("avg", amount_stats)
        
        # Verify values
        self.assertEqual(amount_stats["min"], 100)
        self.assertEqual(amount_stats["max"], 200)
        self.assertAlmostEqual(amount_stats["avg"], 150.0)  # Average of 100, 200, 150
    
    def test_column_statistics_caching(self):
        """Test that column statistics are properly cached."""
        # Perform initial request to cache stats
        amount_stats1 = self.inspector.get_column_statistics("orders", "amount")
        
        # Mock the engine to verify we don't hit the database on second request
        original_engine = self.inspector.engine
        mock_engine = MagicMock()
        self.inspector.engine = mock_engine
        
        # Get stats again - should use cache
        amount_stats2 = self.inspector.get_column_statistics("orders", "amount")
        
        # Restore original engine
        self.inspector.engine = original_engine
        
        # Verify we didn't call the database
        mock_engine.connect.assert_not_called()
        
        # Verify stats are the same
        self.assertEqual(amount_stats1["min"], amount_stats2["min"])
        self.assertEqual(amount_stats1["max"], amount_stats2["max"])
        self.assertEqual(amount_stats1["avg"], amount_stats2["avg"])
    
    def test_discover_relationships(self):
        """Test relationship discovery."""
        # Discover all relationships
        relationships = self.inspector.discover_relationships()
        
        # Verify nodes (tables)
        table_nodes = {node["id"] for node in relationships["nodes"]}
        self.assertIn("users", table_nodes)
        self.assertIn("orders", table_nodes)
        self.assertIn("order_items", table_nodes)
        
        # Verify edges (relationships)
        edges = relationships["edges"]
        edge_pairs = [(edge["source"], edge["target"]) for edge in edges]
        
        # There should be a relationship from orders to users
        self.assertIn(("orders", "users"), edge_pairs)
        
        # There should be a relationship from order_items to orders
        self.assertIn(("order_items", "orders"), edge_pairs)
    
    def test_discover_relationships_with_start_table(self):
        """Test relationship discovery from a specific starting table."""
        # Discover relationships starting from orders
        relationships = self.inspector.discover_relationships(start_table="orders")
        
        # Verify nodes (tables)
        table_nodes = {node["id"] for node in relationships["nodes"]}
        self.assertIn("orders", table_nodes)
        self.assertIn("users", table_nodes)  # Referenced by orders
        
        # Verify edges (relationships)
        edges = relationships["edges"]
        edge_pairs = [(edge["source"], edge["target"]) for edge in edges]
        
        # There should be a relationship from orders to users
        self.assertIn(("orders", "users"), edge_pairs)
    
    def test_get_tables_by_column_pattern(self):
        """Test finding tables by column pattern."""
        # Find tables with id columns
        tables_with_id = self.inspector.get_tables_by_column_pattern("^id$")
        
        # All tables should have an id column
        table_names = [table["table_name"] for table in tables_with_id]
        self.assertIn("users", table_names)
        self.assertIn("orders", table_names)
        self.assertIn("order_items", table_names)
        
        # Find tables with date columns
        tables_with_date = self.inspector.get_tables_by_column_pattern("date")
        
        # Only orders has order_date column
        table_names = [table["table_name"] for table in tables_with_date]
        self.assertIn("orders", table_names)
        self.assertNotIn("order_items", table_names)
    
    def test_suggest_join_conditions(self):
        """Test suggestion of join conditions between tables."""
        # Get join suggestions for orders to users
        join_suggestions = self.inspector.suggest_join_conditions("orders", "users")
        
        # There should be at least one suggestion (the foreign key)
        self.assertGreaterEqual(len(join_suggestions), 1)
        
        # Verify foreign key suggestion
        fk_suggestions = [s for s in join_suggestions if s["type"] == "foreign_key"]
        self.assertGreaterEqual(len(fk_suggestions), 1)
        
        # Verify suggestion details
        suggestion = fk_suggestions[0]
        self.assertEqual(suggestion["left_table"], "orders")
        self.assertEqual(suggestion["right_table"], "users")
        self.assertEqual(suggestion["left_columns"], ["user_id"])
        self.assertEqual(suggestion["right_columns"], ["id"])
        self.assertEqual(suggestion["confidence"], "high")
    
    def test_suggest_join_conditions_name_match(self):
        """Test name-based join suggestions when no foreign key exists."""
        # Mock to simulate tables without foreign keys but with common column names
        with patch.object(self.inspector, 'get_table_metadata') as mock_get_metadata:
            # Products table mock
            products_meta = {
                "table_name": "products",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "category_id", "type": "INTEGER"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indices": []
            }
            
            # Categories table mock
            categories_meta = {
                "table_name": "categories",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indices": []
            }
            
            # Configure mock to return appropriate metadata
            mock_get_metadata.side_effect = lambda table, refresh=False: (
                products_meta if table == "products" else categories_meta
            )
            
            # Get join suggestions
            join_suggestions = self.inspector.suggest_join_conditions("products", "categories")
        
        # Verify name-based suggestions
        name_suggestions = [s for s in join_suggestions if s["type"] == "name_match"]
        self.assertGreaterEqual(len(name_suggestions), 1)
        
        # There should be a suggestion matching category_id to id
        category_id_suggestion = None
        for suggestion in name_suggestions:
            if suggestion["left_columns"] == ["category_id"] and suggestion["right_columns"] == ["id"]:
                category_id_suggestion = suggestion
                break
        
        self.assertIsNotNone(category_id_suggestion)
        self.assertEqual(category_id_suggestion["confidence"], "medium")  # Should be medium for id fields
    
    def test_generate_query_hints(self):
        """Test generation of query optimization hints."""
        # Test with a query that could benefit from indexing
        query = "SELECT * FROM orders WHERE amount > 100"
        hints = self.inspector.generate_query_hints(query)
        
        # Verify tables referenced
        self.assertIn("orders", hints["tables_referenced"])
        
        # Verify suggested indices (should suggest index on amount if not already indexed)
        amount_index_suggestions = [
            s for s in hints["suggested_indices"] 
            if s["table"] == "orders" and s["column"] == "amount"
        ]
        self.assertGreaterEqual(len(amount_index_suggestions), 1)
    
    def test_generate_query_hints_with_missing_order_by(self):
        """Test hints for queries with LIMIT but no ORDER BY."""
        query = "SELECT * FROM orders LIMIT 10"
        hints = self.inspector.generate_query_hints(query)
        
        # Verify potential issues
        missing_order_by_issues = [
            issue for issue in hints["potential_issues"]
            if issue["type"] == "missing_order_by"
        ]
        self.assertGreaterEqual(len(missing_order_by_issues), 1)
    
    def test_refresh_schema_cache(self):
        """Test refreshing the entire schema cache."""
        # Mock get_table_metadata to verify it's called with refresh=True
        with patch.object(self.inspector, 'get_table_metadata') as mock_get_metadata:
            # Mock inspector to return a list of tables
            with patch('sqlalchemy.inspect') as mock_inspect:
                mock_inspector = MagicMock()
                mock_inspector.get_table_names.return_value = ["users", "orders", "order_items"]
                mock_inspect.return_value = mock_inspector
                
                # Run refresh
                result = self.inspector.refresh_schema_cache()
        
        # Verify get_table_metadata called for each table with refresh=True
        expected_calls = [
            call("users", refresh=True),
            call("orders", refresh=True),
            call("order_items", refresh=True)
        ]
        mock_get_metadata.assert_has_calls(expected_calls, any_order=True)
        
        # Verify result
        self.assertEqual(result["tables_refreshed"], 3)
        self.assertIn("completed_at", result)
    
    def test_health_check(self):
        """Test health check functionality."""
        # Set last_full_refresh for testing
        self.inspector.last_full_refresh = datetime.now() - timedelta(hours=12)
        
        # Run health check
        health_info = self.inspector.health_check()
        
        # Verify health info
        self.assertEqual(health_info["service"], "schema_inspector")
        self.assertEqual(health_info["status"], "ok")
        self.assertTrue(health_info["connection_test"])
        self.assertEqual(health_info["cache_status"], "fresh")  # Should be fresh (less than 24h)
        
        # Verify cache age
        self.assertGreaterEqual(health_info["cache_age_hours"], 11)
        self.assertLessEqual(health_info["cache_age_hours"], 13)


if __name__ == "__main__":
    unittest.main() 