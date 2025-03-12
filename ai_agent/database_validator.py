"""
Database Validator for AI Testing

This module validates AI-generated responses against the actual database content,
ensuring factual correctness and accuracy of information provided to users.
"""

import logging
import re
import psycopg2
import psycopg2.extras
import os
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DatabaseValidator:
    """Validates the factual correctness of AI responses against database records."""
    
    def __init__(self, db_connection_string=None):
        """Initialize with database connection."""
        load_dotenv()
        self.connection_string = db_connection_string or os.getenv("DB_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("Database connection string not provided and not found in environment variables")
        
        self.conn = self._create_connection()
        self.validation_templates = self._load_validation_templates()
        
    def _create_connection(self):
        """Create a database connection."""
        try:
            return psycopg2.connect(self.connection_string)
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
        
    def _load_validation_templates(self) -> Dict[str, str]:
        """Load SQL query templates for different validation scenarios."""
        return {
            "menu_item_exists": "SELECT COUNT(*) FROM menu_items WHERE name ILIKE %s",
            "menu_item_price": "SELECT price FROM menu_items WHERE name ILIKE %s",
            "order_history": "SELECT COUNT(*) FROM orders WHERE customer_id = %s AND DATE(order_date) = %s",
            "order_items": """
                SELECT oi.quantity, mi.name 
                FROM order_items oi 
                JOIN menu_items mi ON oi.menu_item_id = mi.id 
                WHERE oi.order_id = %s
            """,
            "customer_orders": """
                SELECT o.id, o.order_date, SUM(oi.quantity * mi.price) as total_amount
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.customer_id = %s
                GROUP BY o.id, o.order_date
                ORDER BY o.order_date DESC
                LIMIT %s
            """,
        }
        
    def validate_response(self, response_text: str, response_type: str, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate response against database using appropriate queries."""
        validation_results = []
        
        # Extract facts that can be validated from the response
        facts = self._extract_facts(response_text, response_type, entities)
        
        if not facts:
            logger.warning(f"No validatable facts found in response: {response_text[:100]}...")
            return {
                "validation_results": [],
                "accuracy_score": 0,
                "valid": False,
                "error": "No validatable facts found"
            }
        
        # Validate each fact against the database
        for fact in facts:
            result = self._validate_fact(fact)
            validation_results.append(result)
            
        # Calculate overall accuracy score
        accuracy = sum(1 for r in validation_results if r['valid']) / len(validation_results) if validation_results else 0
        
        return {
            "validation_results": validation_results,
            "accuracy_score": accuracy,
            "valid": accuracy > 0.8,  # Consider valid if 80% or more facts are correct
            "validation_count": len(validation_results)
        }
        
    def _extract_facts(self, response_text: str, response_type: str, entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract verifiable facts from the response text based on response type."""
        facts = []
        
        # Use provided entities if available (extracted by NLP or provided by the test)
        if entities:
            return self._create_facts_from_entities(entities, response_type)
            
        if response_type == "menu_query":
            # Extract menu items and their prices
            price_pattern = r'([a-zA-Z\s]+) (?:costs|is|for) \$?(\d+\.?\d*)'
            matches = re.findall(price_pattern, response_text)
            
            for item, price in matches:
                facts.append({
                    "type": "menu_item_price",
                    "item": item.strip().replace("The ", "").strip(),
                    "claimed_price": float(price)
                })
                
        elif response_type == "order_history":
            # Extract order details and dates
            # This is a simplified example; in a real implementation, you would use 
            # more sophisticated NLP techniques to extract structured data
            order_pattern = r'(?:ordered|purchased|bought) (?:a|an|the)? ([a-zA-Z\s]+) on ([a-zA-Z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)'
            matches = re.findall(order_pattern, response_text)
            
            for item, date_str in matches:
                # Convert date string to proper format (simplified)
                facts.append({
                    "type": "order_item",
                    "item": item.strip(),
                    "date_str": date_str
                })
                
        return facts
    
    def _create_facts_from_entities(self, entities: Dict[str, Any], response_type: str) -> List[Dict[str, Any]]:
        """Create facts from pre-extracted entities."""
        facts = []
        
        if response_type == "menu_query" and "menu_items" in entities:
            for item in entities["menu_items"]:
                if "price" in item:
                    facts.append({
                        "type": "menu_item_price",
                        "item": item["name"],
                        "claimed_price": float(item["price"])
                    })
                else:
                    facts.append({
                        "type": "menu_item_exists",
                        "item": item["name"]
                    })
                    
        elif response_type == "order_history" and "orders" in entities:
            for order in entities["orders"]:
                if "items" in order:
                    for item in order["items"]:
                        facts.append({
                            "type": "order_item",
                            "order_id": order.get("id"),
                            "item": item["name"],
                            "quantity": item.get("quantity", 1),
                            "date": order.get("date")
                        })
                        
        return facts
        
    def _validate_fact(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single fact against the database."""
        cursor = self.conn.cursor()
        valid = False
        explanation = ""
        actual_data = None
        
        try:
            if fact["type"] == "menu_item_price":
                cursor.execute(self.validation_templates["menu_item_price"], (fact["item"],))
                result = cursor.fetchone()
                if result:
                    actual_price = result[0]
                    valid = abs(actual_price - fact["claimed_price"]) < 0.01  # Allow for tiny float differences
                    actual_data = {"actual_price": actual_price}
                    explanation = f"Price {'matches' if valid else 'does not match'} database. Actual: ${actual_price}, Claimed: ${fact['claimed_price']}"
                else:
                    explanation = f"Menu item '{fact['item']}' not found in database"
                    
            elif fact["type"] == "menu_item_exists":
                cursor.execute(self.validation_templates["menu_item_exists"], (fact["item"],))
                result = cursor.fetchone()
                if result:
                    count = result[0]
                    valid = count > 0
                    actual_data = {"count": count}
                    explanation = f"Menu item {'exists' if valid else 'does not exist'} in database"
                else:
                    explanation = "Failed to execute query"
                
            elif fact["type"] == "order_item":
                if "order_id" in fact and fact["order_id"]:
                    cursor.execute(self.validation_templates["order_items"], (fact["order_id"],))
                    results = cursor.fetchall()
                    item_name = fact["item"]
                    valid = any(item_name.lower() in result[1].lower() for result in results)
                    actual_data = [{"quantity": r[0], "item": r[1]} for r in results]
                    explanation = f"Order item {'found' if valid else 'not found'} in order {fact['order_id']}"
                elif "customer_id" in fact and "date" in fact:
                    cursor.execute(self.validation_templates["order_history"], (fact["customer_id"], fact["date"]))
                    result = cursor.fetchone()
                    count = result[0] if result else 0
                    valid = count > 0
                    actual_data = {"order_count": count}
                    explanation = f"{'Found' if valid else 'Did not find'} orders for customer on {fact['date']}"
                else:
                    explanation = "Insufficient data to validate order item"
                
        except Exception as e:
            explanation = f"Error during validation: {str(e)}"
            logger.error(f"Validation error for fact {fact}: {str(e)}", exc_info=True)
            
        finally:
            cursor.close()
            
        return {
            "fact": fact,
            "valid": valid,
            "explanation": explanation,
            "actual_data": actual_data
        }
        
    def check_sql_query(self, sql_query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """Run a custom SQL query for validation purposes."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql_query, params or ())
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing custom SQL: {str(e)}", exc_info=True)
            raise
        finally:
            cursor.close()
            
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get the schema for a specific table to improve validation queries."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
            """, (table_name,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()
            
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def __del__(self):
        """Ensure connection is closed on object destruction."""
        self.close() 