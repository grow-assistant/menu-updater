"""
Mock services for testing the AI agent.

These mock services simulate the AI agent system's components.
"""

import logging
import json
import time
import re
import random
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

class SQLExecutorService:
    """
    Mock SQL execution service.
    
    Simulates database operations and returns mock results.
    """
    
    def __init__(self, max_rows: int = 100, timeout: int = 5, logger: logging.Logger = None):
        """
        Initialize the SQL executor service.
        
        Args:
            max_rows: Maximum number of rows to return
            timeout: Query timeout in seconds
            logger: Logger instance
        """
        self.max_rows = max_rows
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("SQLExecutorService initialized")
        
        # Sample database tables and their schema
        self.tables = {
            "menu_items": ["id", "name", "description", "price", "category", "is_available"],
            "categories": ["id", "name", "description"],
            "orders": ["id", "customer_id", "order_time", "status", "total_amount"],
            "order_items": ["id", "order_id", "menu_item_id", "quantity", "price"]
        }
    
    def execute(self, query: str, *args, **kwargs) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute an SQL query and return mock results.
        
        Args:
            query: SQL query string
            
        Returns:
            Mock query results
        """
        self.logger.info(f"Executing SQL query: {query}")
        
        # Simulate query execution time
        start_time = time.time()
        time.sleep(random.uniform(0.1, 0.5))
        
        # Generate mock results based on the query
        result = self._generate_mock_results(query)
        
        # Log execution time
        execution_time = time.time() - start_time
        self.logger.info(f"SQL query executed in {execution_time:.2f} seconds")
        
        return result
    
    def _generate_mock_results(self, query: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate mock results based on the query.
        
        Args:
            query: SQL query string
            
        Returns:
            Mock query results
        """
        # Extract table name from query
        table_match = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if not table_match:
            self.logger.warning(f"Could not extract table name from query: {query}")
            return []
        
        table_name = table_match.group(1)
        
        # Check if the table exists in our mock database
        if table_name not in self.tables:
            self.logger.warning(f"Table {table_name} not found in mock database")
            return []
        
        # Generate mock data based on the table schema
        columns = self.tables[table_name]
        
        # Determine how many rows to return based on query
        if "COUNT" in query.upper():
            # For COUNT queries, return a count result
            return [{"count": random.randint(10, 100)}]
        elif "WHERE" in query.upper() and "is_available" in query.lower():
            # For queries about menu availability
            rows = []
            for i in range(random.randint(3, 10)):
                row = {
                    "id": i + 1,
                    "name": f"Menu Item {i+1}",
                    "description": f"Description for menu item {i+1}",
                    "price": round(random.uniform(5.99, 29.99), 2),
                    "category": random.choice(["Appetizer", "Main Course", "Dessert", "Beverage"]),
                    "is_available": True  # Since we're querying for available items
                }
                rows.append(row)
            return rows
        else:
            # For general queries, return a random number of rows
            rows = []
            for i in range(random.randint(0, self.max_rows)):
                row = {}
                for col in columns:
                    if col == "id" or col.endswith("_id"):
                        row[col] = i + 1
                    elif col in ["name", "description"]:
                        row[col] = f"{col.capitalize()} {i+1}"
                    elif col == "price" or col.endswith("_amount"):
                        row[col] = round(random.uniform(5.99, 29.99), 2)
                    elif col == "category":
                        row[col] = random.choice(["Appetizer", "Main Course", "Dessert", "Beverage"])
                    elif col.startswith("is_"):
                        row[col] = random.choice([True, False])
                    elif col.endswith("_time") or col.endswith("_date"):
                        row[col] = datetime.now().isoformat()
                    elif col == "status":
                        row[col] = random.choice(["Pending", "Processing", "Completed", "Cancelled"])
                    elif col == "quantity":
                        row[col] = random.randint(1, 5)
                    else:
                        row[col] = f"Value for {col} {i+1}"
                rows.append(row)
            return rows

class ClassificationService:
    """
    Mock classification service.
    
    Simulates intent classification and entity extraction.
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the classification service.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("ClassificationService initialized")
        
        # Sample intents and entities
        self.intents = [
            "menu_inquiry", 
            "availability_check", 
            "price_inquiry", 
            "order_status", 
            "place_order"
        ]
        self.entities = [
            "menu_item", 
            "category", 
            "price_range", 
            "order_id", 
            "customer_id"
        ]
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text and extract intent and entities.
        
        Args:
            text: Input text
            
        Returns:
            Classification results
        """
        self.logger.info(f"Classifying text: {text}")
        
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.3))
        
        # Determine intent based on keywords in the text
        intent = None
        if "menu" in text.lower() or "items" in text.lower():
            intent = "menu_inquiry"
        elif "available" in text.lower() or "availability" in text.lower():
            intent = "availability_check"
        elif "price" in text.lower() or "cost" in text.lower() or "how much" in text.lower():
            intent = "price_inquiry"
        elif "order" in text.lower() and ("status" in text.lower() or "where" in text.lower()):
            intent = "order_status"
        elif "order" in text.lower() or "buy" in text.lower() or "purchase" in text.lower():
            intent = "place_order"
        else:
            # Default to a random intent
            intent = random.choice(self.intents)
        
        # Extract entities
        entities = []
        if "menu_inquiry" in intent or "availability_check" in intent:
            # Look for menu item or category mentions
            words = text.lower().split()
            for word in words:
                if len(word) > 3 and word not in ["menu", "item", "list", "show", "what", "available"]:
                    entity_type = random.choice(["menu_item", "category"])
                    entities.append({
                        "type": entity_type,
                        "value": word,
                        "confidence": random.uniform(0.7, 0.95)
                    })
                    break
        
        # Return classification results
        result = {
            "intent": {
                "name": intent,
                "confidence": random.uniform(0.75, 0.98)
            },
            "entities": entities
        }
        
        self.logger.info(f"Classification result: {result}")
        return result

class ResponseGenerationService:
    """
    Mock response generation service.
    
    Generates responses based on intent and SQL results.
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the response generation service.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("ResponseGenerationService initialized")
        
        # Sample response templates
        self.templates = {
            "menu_inquiry": [
                "Here is our menu: {items}",
                "We offer the following items: {items}",
                "Our menu includes: {items}"
            ],
            "availability_check": [
                "Yes, {item} is available.",
                "I checked and {item} is currently available.",
                "Good news! {item} is available to order."
            ],
            "price_inquiry": [
                "The price of {item} is ${price}.",
                "{item} costs ${price}.",
                "You can get {item} for ${price}."
            ],
            "order_status": [
                "Your order #{order_id} is {status}.",
                "Order #{order_id} status: {status}",
                "The status of your order #{order_id} is {status}."
            ],
            "place_order": [
                "Your order has been placed. Order #{order_id}",
                "Thanks for your order! Your order number is #{order_id}",
                "Order placed successfully. Your order number is #{order_id}"
            ]
        }
    
    def generate_response(self, intent: str, entities: List[Dict[str, Any]], sql_results: List[Dict[str, Any]]) -> str:
        """
        Generate a response based on intent, entities, and SQL results.
        
        Args:
            intent: Intent
            entities: Extracted entities
            sql_results: SQL query results
            
        Returns:
            Generated response
        """
        self.logger.info(f"Generating response for intent: {intent} with {len(sql_results)} SQL results")
        
        # Simulate processing time
        time.sleep(random.uniform(0.2, 0.5))
        
        # Select a template based on intent
        templates = self.templates.get(intent, ["I'm not sure how to respond to that."])
        template = random.choice(templates)
        
        # Fill in template based on intent and data
        if intent == "menu_inquiry":
            if sql_results:
                items = ", ".join([item.get("name", f"Item {i+1}") for i, item in enumerate(sql_results[:5])])
                if len(sql_results) > 5:
                    items += f", and {len(sql_results) - 5} more items"
                response = template.format(items=items)
            else:
                response = "I couldn't find any menu items."
                
        elif intent == "availability_check":
            if entities and "menu_item" in [e.get("type") for e in entities]:
                item = next((e.get("value") for e in entities if e.get("type") == "menu_item"), "the item")
                if sql_results and sql_results[0].get("is_available", False):
                    response = template.format(item=item)
                else:
                    response = f"Sorry, {item} is not available at the moment."
            else:
                response = "What item are you asking about?"
                
        elif intent == "price_inquiry":
            if entities and "menu_item" in [e.get("type") for e in entities]:
                item = next((e.get("value") for e in entities if e.get("type") == "menu_item"), "the item")
                if sql_results:
                    price = sql_results[0].get("price", "N/A")
                    response = template.format(item=item, price=price)
                else:
                    response = f"I couldn't find pricing information for {item}."
            else:
                response = "What item are you asking about the price of?"
                
        elif intent == "order_status":
            if sql_results:
                order_id = sql_results[0].get("id", random.randint(1000, 9999))
                status = sql_results[0].get("status", "processing")
                response = template.format(order_id=order_id, status=status)
            else:
                response = "I couldn't find information about your order."
                
        elif intent == "place_order":
            order_id = random.randint(1000, 9999)
            response = template.format(order_id=order_id)
            
        else:
            response = "I'm not sure how to respond to that."
        
        self.logger.info(f"Generated response: {response}")
        return response

class OrchestratorService:
    """
    Mock orchestrator service.
    
    Coordinates the AI agent's components to process requests and generate responses.
    """
    
    def __init__(
        self, 
        sql_executor: SQLExecutorService,
        classification_service: ClassificationService,
        response_service: ResponseGenerationService,
        logger: logging.Logger = None
    ):
        """
        Initialize the orchestrator service.
        
        Args:
            sql_executor: SQL executor service
            classification_service: Classification service
            response_service: Response generation service
            logger: Logger instance
        """
        self.sql_executor = sql_executor
        self.classification_service = classification_service
        self.response_service = response_service
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("OrchestratorService initialized")
    
    def process_request(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user request.
        
        Args:
            text: User input text
            session_id: Session ID
            
        Returns:
            Response data
        """
        self.logger.info(f"Processing request: {text} (Session: {session_id})")
        
        # Classify the input
        classification = self.classification_service.classify(text)
        intent = classification["intent"]["name"]
        entities = classification["entities"]
        
        self.logger.info(f"Classified intent: {intent} with {len(entities)} entities")
        
        # Generate an SQL query based on intent and entities
        sql_query = self._generate_sql_query(intent, entities)
        
        # Execute the SQL query
        if sql_query:
            self.logger.info(f"Executing SQL query: {sql_query}")
            sql_results = self.sql_executor.execute(sql_query)
        else:
            self.logger.info("No SQL query to execute")
            sql_results = []
        
        # Generate a response
        response_text = self.response_service.generate_response(intent, entities, sql_results)
        
        # Return the response
        return {
            "text": response_text,
            "intent": intent,
            "confidence": classification["intent"]["confidence"],
            "session_id": session_id
        }
    
    def _generate_sql_query(self, intent: str, entities: List[Dict[str, Any]]) -> str:
        """
        Generate an SQL query based on intent and entities.
        
        Args:
            intent: Intent
            entities: Extracted entities
            
        Returns:
            SQL query
        """
        if intent == "menu_inquiry":
            return "SELECT id, name, description, price, category, is_available FROM menu_items WHERE is_available = TRUE"
            
        elif intent == "availability_check":
            if entities and "menu_item" in [e.get("type") for e in entities]:
                item = next((e.get("value") for e in entities if e.get("type") == "menu_item"), "")
                return f"SELECT id, name, is_available FROM menu_items WHERE name LIKE '%{item}%'"
            else:
                return "SELECT id, name, is_available FROM menu_items WHERE is_available = TRUE LIMIT 10"
                
        elif intent == "price_inquiry":
            if entities and "menu_item" in [e.get("type") for e in entities]:
                item = next((e.get("value") for e in entities if e.get("type") == "menu_item"), "")
                return f"SELECT id, name, price FROM menu_items WHERE name LIKE '%{item}%'"
            else:
                return "SELECT id, name, price FROM menu_items LIMIT 5"
                
        elif intent == "order_status":
            if entities and "order_id" in [e.get("type") for e in entities]:
                order_id = next((e.get("value") for e in entities if e.get("type") == "order_id"), "")
                return f"SELECT id, status, order_time FROM orders WHERE id = '{order_id}'"
            else:
                return "SELECT id, status, order_time FROM orders ORDER BY order_time DESC LIMIT 1"
        
        elif intent == "place_order":
            # For place_order, we might not need an initial SQL query
            return ""
            
        else:
            return "" 