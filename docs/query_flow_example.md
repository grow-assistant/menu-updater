# Query Flow Example: "How many orders were completed on 2/25/2025?"

This document provides a complete trace of how a sample data query flows through the system, from the moment a user inputs the query until they receive a response. The example demonstrates the system's microservices architecture in action, showing how each component handles its specific responsibility.

## Visual Flow Representation

```
┌─────────────────────┐
│                     │
│  User Query Input   │  "How many orders were completed on 2/25/2025?"
│                     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│                     │  • Initialize session
│  Frontend Module    │  • Get context from session
│  (Query Processor)  │  • Update history after processing
│                     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│                     │  • Classify query as "data_query" 
│    Orchestrator     │  • Route to appropriate processing path
│      Service        │  • Coordinate service interactions
│                     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│                     │
│  Classification     │  • Determine query is a data query
│     Service         │  • Uses AI to categorize the intent
│                     │
└─────────┬───────────┘
          │
          │    ┌─────────────────────┐
          │    │                     │
          └───►│    Rule Service     │  • Provide SQL generation rules
               │                     │  • Define constraints for processing
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │                     │  • Generate SQL query:
               │  SQL Generation     │  • "SELECT COUNT(*) FROM orders 
               │     Service         │     WHERE completion_date = '2025-02-25'"
               │                     │
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │                     │  • Connect to database
               │   SQL Execution     │  • Execute query
               │     Service         │  • Return count result (e.g., 42)
               │                     │
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │                     │  • Format natural language response:
               │     Response        │  • "There were 42 orders completed 
               │     Service         │     on February 25, 2025."
               │                     │
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │                     │
               │   Frontend UI       │  • Display response to user
               │                     │
               └─────────────────────┘
```

## 1. Frontend Input Processing

> This section demonstrates how the user's query is captured in the UI layer and then processed through the query processor. It shows the entry point into the system's workflow.

### File: `frontend/ui.py`
```python
def render_chat_interface():
    # User inputs the query in the Streamlit chat interface
    query = st.chat_input("Ask me about menu data...")
    
    if query:
        # Display user query in the chat
        st.chat_message("user").write(query)
        
        # Process the query (see next step)
        response = process_user_query(query)
        
        # Display the response
        st.chat_message("assistant").write(response)
```

**Key Points:**
- The Streamlit interface provides a chat input for the user to enter their query
- The user query is captured and displayed in the chat history
- The query is passed to the processing function
- After processing, the response is displayed back to the user in the chat interface

### File: `frontend/query_processor.py`
```python
def process_user_query(query):
    # Initialize session if not already done
    SessionManager.initialize_session()
    
    # Get current context from session
    context = SessionManager.get_context()
    
    # Get orchestrator service from registry
    orchestrator = ServiceRegistry.get_service("orchestrator")
    
    # Process the query through orchestrator
    result = orchestrator.process_query(query, context)
    
    # Update session history with query and result
    SessionManager.update_history(query, result)
    
    # Return the response to display to the user
    return result["response"]
```

**Key Points:**
- The processor first ensures a session is initialized for the user
- It retrieves the current context (previous interactions, preferences)
- Uses the ServiceRegistry to access the orchestrator (demonstrating dependency injection)
- The orchestrator handles the actual processing logic
- Session history is updated with both the query and its result for context preservation
- Only the readable response portion is returned to the UI layer

## 2. Session Management

> This section shows how user session state is managed to maintain context across interactions. The SessionManager provides persistence for conversation history and user preferences.

### File: `frontend/session_manager.py`
```python
class SessionManager:
    @staticmethod
    def initialize_session():
        # Create default session state if it doesn't exist
        if "user_preferences" not in st.session_state:
            st.session_state.user_preferences = {}
        if "recent_queries" not in st.session_state:
            st.session_state.recent_queries = []
        if "session_history" not in st.session_state:
            st.session_state.session_history = []
        if "active_conversation" not in st.session_state:
            st.session_state.active_conversation = False

    @staticmethod
    def get_context():
        # Return current context from session state
        return {
            "user_preferences": st.session_state.user_preferences,
            "recent_queries": st.session_state.recent_queries,
            "session_history": st.session_state.session_history,
            "active_conversation": st.session_state.active_conversation
        }
        
    @staticmethod
    def update_history(query, result):
        # Add query to recent queries
        st.session_state.recent_queries.append(query)
        if len(st.session_state.recent_queries) > 10:
            st.session_state.recent_queries.pop(0)
            
        # Add interaction to session history
        st.session_state.session_history.append({
            "query": query,
            "response": result["response"],
            "category": result["category"],
            "timestamp": time.time()
        })
        
        # Set conversation as active
        st.session_state.active_conversation = True
```

**Key Points:**
- SessionManager uses a static design pattern for global access
- Four key session components are maintained:
  - user_preferences: Stores customization options and user settings
  - recent_queries: Maintains a limited list of recent queries (capped at 10)
  - session_history: Records all query-response pairs with timestamps
  - active_conversation: Flags if the user is in an ongoing conversation
- The context provides richer information for AI services to make better decisions
- History updates maintain a time-ordered log of interactions

## 3. Orchestration

> The Orchestrator is the central coordinator that routes queries through the appropriate processing pipeline based on their classification. It's the "brain" of the system that knows how to connect different services.

### File: `services/orchestrator/orchestrator.py`
```python
class OrchestratorService:
    def __init__(self, config):
        self.config = config
        self.services = {}

    def process_query(self, query, context=None):
        try:
            # Step 1: Get classification service
            classifier = ServiceRegistry.get_service("classification")
            
            # Step 2: Classify the query
            category = classifier.classify(query, context)
            
            # For our example "How many orders were completed on 2/25/2025?"
            # This would be classified as "data_query"
            
            # Step 3: Route based on classification
            if category == "data_query":
                return self._process_data_query(query, context)
            elif category == "menu_update":
                return self._process_menu_update(query, context)
            else:
                return self._process_general_query(query, context)
                
        except Exception as e:
            # Handle any errors in processing
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "category": "error",
                "error": str(e),
                "metadata": {"error_type": type(e).__name__}
            }
    
    def _process_data_query(self, query, context):
        # Step 1: Get the rule service
        rule_service = ServiceRegistry.get_service("rule")
        
        # Step 2: Get relevant rules for data queries
        rules = rule_service.get_rules("data_query")
        
        # Step 3: Get SQL generation service
        sql_generator = ServiceRegistry.get_service("sql_generation")
        
        # Step 4: Generate SQL from the query
        sql_result = sql_generator.generate(query, rules, context)
        
        # For our example, would generate:
        # "SELECT COUNT(*) FROM orders WHERE completion_date = '2025-02-25'"
        
        # Step 5: Get SQL execution service
        sql_executor = ServiceRegistry.get_service("sql_execution")
        
        # Step 6: Execute the generated SQL
        query_results = sql_executor.execute(sql_result["sql"])
        
        # Step 7: Get response service
        response_service = ServiceRegistry.get_service("response")
        
        # Step 8: Generate formatted response
        response = response_service.format_data_response(
            query, 
            sql_result["sql"], 
            query_results,
            context
        )
        
        # Return complete result
        return {
            "response": response,
            "category": "data_query",
            "metadata": {
                "sql_query": sql_result["sql"],
                "results": query_results,
                "processing_time": sql_result["processing_time"]
            }
        }
```

**Key Points:**
- The orchestrator follows a clear workflow with explicit steps
- All service instances are retrieved through the ServiceRegistry (lazy loading)
- The process starts with classifying the query to determine its type
- Based on classification, the query is routed to specialized processing methods
- For data queries, a specific pipeline is followed:
  1. Get business rules relevant to data queries
  2. Generate SQL based on the query and rules
  3. Execute the SQL against the database
  4. Format the results into a natural language response
- Comprehensive error handling catches exceptions at all levels
- The result format includes both user-facing response and internal metadata
- Processing time is tracked for performance monitoring

## 4. Classification

> This section shows how the system determines the type of query being asked, which is critical for routing it to the appropriate processing pipeline. It uses AI to understand user intent.

### File: `services/classification/classifier.py`
```python
class ClassificationService:
    def __init__(self, config):
        self.config = config
        self.threshold = config["services"]["classification"]["confidence_threshold"]
        self.openai_client = self._initialize_openai_client(config)
        
    def _initialize_openai_client(self, config):
        # Initialize OpenAI client with API key from config
        return OpenAI(api_key=config["api"]["openai"]["api_key"])
        
    def classify(self, query, context=None):
        # Prepare classification prompt
        prompt = self._prepare_classification_prompt(query, context)
        
        # Call OpenAI API for classification
        response = self.openai_client.chat.completions.create(
            model=self.config["api"]["openai"]["model"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1
        )
        
        # Extract and validate classification
        classification = response.choices[0].message.content.strip().lower()
        
        # Validate the classification
        if classification not in ["data_query", "menu_update", "general"]:
            # Default to general if classification is invalid
            classification = "general"
            
        # For our example "How many orders were completed on 2/25/2025?"
        # This would classify as "data_query"
        
        return classification
        
    def _prepare_classification_prompt(self, query, context):
        # Create a prompt for the OpenAI API to classify the query
        prompt = f"""
        Classify the following query into one of these categories:
        - data_query: Questions requesting information from the database
        - menu_update: Requests to update menu items
        - general: General questions or conversation
        
        Query: {query}
        
        Respond with just the category name.
        """
        
        if context and context["session_history"]:
            # Add context from previous interactions if available
            prompt += "\n\nRecent conversation history:"
            for item in context["session_history"][-3:]:
                prompt += f"\nUser: {item['query']}\nAssistant: {item['response']}\n"
                
        return prompt
```

**Key Points:**
- Classification uses an AI (OpenAI) model to determine query intent
- The service configures its behavior based on the provided configuration
- A confidence threshold determines when to trust the classification
- Temperature of 0.1 ensures consistent, deterministic classifications
- The prompt is carefully crafted to guide the AI classification
- Three main categories are recognized:
  - data_query: Database information requests
  - menu_update: Requests to modify menu data
  - general: Conversational queries or other questions
- Input validation ensures only valid categories are returned
- Session history is included in the prompt to provide context
- Only the 3 most recent interactions are included to keep the prompt concise

## 5. SQL Generation

> This service translates natural language into structured SQL queries. It's the bridge between human language and database queries, using AI to understand what data the user is requesting.

### File: `services/sql/sql_generator.py`
```python
class SQLGenerationService:
    def __init__(self, config):
        self.config = config
        self.openai_client = self._initialize_openai_client(config)
        
    def _initialize_openai_client(self, config):
        return OpenAI(api_key=config["api"]["openai"]["api_key"])
        
    def generate(self, query, rules, context=None):
        start_time = time.time()
        
        # Prepare SQL generation prompt
        prompt = self._prepare_sql_prompt(query, rules, context)
        
        # Call OpenAI API to generate SQL
        response = self.openai_client.chat.completions.create(
            model=self.config["api"]["openai"]["model"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1
        )
        
        # Extract SQL query from response
        sql_query = self._extract_sql(response.choices[0].message.content)
        
        # Validate the SQL query
        self._validate_sql(sql_query)
        
        # For our example, would generate:
        # "SELECT COUNT(*) FROM orders WHERE completion_date = '2025-02-25'"
        
        processing_time = time.time() - start_time
        
        return {
            "sql": sql_query,
            "processing_time": processing_time
        }
        
    def _prepare_sql_prompt(self, query, rules, context):
        # Create a prompt for the OpenAI API to generate SQL
        table_schemas = self._get_table_schemas()
        
        prompt = f"""
        Generate SQL for the following query based on the database schema:
        
        Query: {query}
        
        Database Schema:
        {table_schemas}
        
        Rules to follow:
        {self._format_rules(rules)}
        
        Return only the SQL query without any explanations.
        """
        
        return prompt
        
    def _get_table_schemas(self):
        # Return database schema information
        return """
        Table: orders
        Columns:
        - order_id (INTEGER): Primary key for orders
        - customer_id (INTEGER): Foreign key to customers table
        - updated_at (DATE): Date when order was placed
        - completion_date (DATE): Date when order was completed
        - status (TEXT): Order status (pending, completed, cancelled)
        - total_amount (DECIMAL): Total order amount
        
        Table: order_items
        Columns:
        - order_item_id (INTEGER): Primary key for order items
        - order_id (INTEGER): Foreign key to orders table
        - menu_item_id (INTEGER): Foreign key to menu_items table
        - quantity (INTEGER): Number of items ordered
        - price (DECIMAL): Price per item at time of order
        """
        
    def _format_rules(self, rules):
        # Format the rules for the prompt
        return "\n".join([f"- {rule}" for rule in rules])
        
    def _extract_sql(self, content):
        # Extract SQL from the model's response
        # Look for SQL between triple backticks or just take the whole response
        sql_match = re.search(r"```sql\n(.*?)\n```", content, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        return content.strip()
        
    def _validate_sql(self, sql_query):
        # Basic validation of SQL query
        if not sql_query or "SELECT" not in sql_query.upper():
            raise ValueError("Invalid SQL query generated")
```

**Key Points:**
- Like the classifier, this service uses AI to bridge human language to SQL
- Performance timing measures how long the SQL generation takes
- The prompt includes three critical components:
  1. The user's query in natural language
  2. The database schema with detailed column information
  3. Rules to follow for SQL generation
- Low temperature (0.1) ensures deterministic and consistent SQL output
- The system knows about the database schema, including:
  - Table relationships (foreign keys)
  - Column data types
  - Primary keys
- SQL extraction handles different model response formats
- Basic validation ensures the generated SQL is valid before execution
- For the example query, the service recognizes the need for:
  - A COUNT function for a quantity question
  - The correct date format (YYYY-MM-DD)
  - The appropriate WHERE clause to filter by completion date

## 6. SQL Execution

> The SQL Execution service safely connects to the database and runs the generated SQL queries. It handles database connections, executes queries, and formats results for further processing.

### File: `services/sql/sql_executor.py`
```python
class SQLExecutionService:
    def __init__(self, config):
        self.config = config
        self.db_connection = self._initialize_db_connection(config)
        
    def _initialize_db_connection(self, config):
        # Initialize database connection
        return sqlite3.connect(config["database"]["path"])
        
    def execute(self, sql_query):
        try:
            # Execute the SQL query
            cursor = self.db_connection.cursor()
            cursor.execute(sql_query)
            
            # Fetch results
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            
            # For our example query counting orders on a specific date
            # This would return a single value, e.g., 42
            
            # Format results as a list of dictionaries
            formatted_results = []
            for row in results:
                formatted_results.append(dict(zip(columns, row)))
                
            return formatted_results
            
        except Exception as e:
            # Handle any SQL execution errors
            raise SQLExecutionError(f"Error executing SQL query: {str(e)}")
```

**Key Points:**
- Database connection is established during service initialization
- The service is responsible for:
  - Executing the SQL query
  - Fetching results from the database
  - Formatting results into a structured format
- Column names are extracted from cursor description
- Results are transformed from tuples to dictionaries for easier access
- Each row is converted to a dictionary with column names as keys
- Error handling catches and wraps database errors
- For our example COUNT query, the result would be a single-row, single-column value
- Custom exception type (SQLExecutionError) provides clear error context

## 7. Response Generation

> This service transforms raw data results into natural language responses. It's responsible for making database query results understandable to human users.

### File: `services/response/response_formatter.py`
```python
class ResponseService:
    def __init__(self, config):
        self.config = config
        
    def format_data_response(self, query, sql, results, context=None):
        # Format the response based on the query type and results
        
        # For our example "How many orders were completed on 2/25/2025?"
        if "count" in sql.lower() and len(results) == 1:
            # Extract the count value from results
            count_value = list(results[0].values())[0]
            
            # Generate natural language response
            response = f"There were {count_value} orders completed on February 25, 2025."
            
            # Add additional context if available
            if count_value == 0:
                response += " No orders were completed on that date."
            elif count_value > 100:
                response += " This was a particularly busy day."
                
            return response
            
        # For other types of data queries...
        # (handling for other query result types)
        
        # Default response if no specific formatting applies
        return f"Query results: {results}"
```

**Key Points:**
- The service analyzes both the SQL query and results to determine response format
- It understands different query types and formats responses accordingly
- For count queries, it:
  - Recognizes the COUNT pattern in the SQL
  - Extracts the count value from the first result
  - Formats a natural language response
  - Adds contextual information based on the value
- The response uses proper date formatting for readability
- Additional context enhances the response with business insights:
  - Zero results get special handling
  - High count values are identified as "particularly busy"
- Default formatting exists for unrecognized query types
- The service bridges the gap between raw data and human-friendly responses

## 8. Rule Service

> The Rule Service maintains business rules that guide how queries are processed. It ensures that SQL generation follows system constraints and requirements.

### File: `services/rules/rule_service.py`
```python
class RuleService:
    def __init__(self, config):
        self.config = config
        self.rules = self._load_rules()
        
    def _load_rules(self):
        # Load rules from configuration or database
        return {
            "data_query": [
                "Always use proper date formatting in SQL (YYYY-MM-DD)",
                "For count queries, use COUNT() function",
                "Limit to 100 results by default unless specified otherwise",
                "Use appropriate joins when data spans multiple tables",
                "Properly handle NULL values in all queries"
            ],
            "menu_update": [
                "Validate menu item names against existing items",
                "Require price validation for any price updates",
                "Log all update operations with timestamp"
            ]
        }
        
    def get_rules(self, category):
        # Return rules for the specified category
        return self.rules.get(category, [])
```

**Key Points:**
- Rules are organized by query category for targeted application
- For data queries, rules focus on:
  - Date formatting standards (YYYY-MM-DD)
  - SQL function usage for aggregations
  - Result limiting for performance
  - Proper join techniques
  - NULL value handling
- For menu updates, rules focus on:
  - Data validation
  - Price validation
  - Audit logging
- Rules could be loaded from configuration files or databases
- Rules guide the AI to generate SQL that follows system standards
- The service provides a simple interface to retrieve rules by category
- Default empty list is returned for unknown categories

## 9. Service Registry

> The Service Registry implements the service locator pattern, centralizing service instantiation and management. It provides a single point of access for all services.

### File: `services/utils/service_registry.py`
```python
class ServiceRegistry:
    _services = {}
    _instances = {}
    _config = None
    
    @classmethod
    def initialize(cls, config):
        cls._config = config
        
    @classmethod
    def register(cls, service_name, service_class):
        cls._services[service_name] = service_class
        
    @classmethod
    def get_service(cls, service_name):
        if service_name not in cls._services:
            raise ServiceNotRegisteredError(f"Service '{service_name}' is not registered")
            
        if service_name not in cls._instances:
            try:
                # Instantiate the service with config
                cls._instances[service_name] = cls._services[service_name](cls._config)
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize service '{service_name}': {str(e)}")
                
        return cls._instances[service_name]
```

**Key Points:**
- Uses a class-level design for global access to services
- Implements the service locator and singleton patterns
- Maintains three key pieces of state:
  - _services: Maps service names to their classes
  - _instances: Caches instantiated service objects
  - _config: Stores configuration to pass to services
- Lazy initialization creates services only when needed
- Service instantiation happens automatically on first request
- All services receive the same configuration object
- Custom exceptions provide clear error messages for:
  - Missing service registrations
  - Service initialization failures
- Services are singletons - only one instance per service type

## Complete Flow Summary

For our example query "How many orders were completed on 2/25/2025?", the flow is:

1. **User inputs** the query in the Streamlit interface (`frontend/ui.py`)
2. **Query processor** receives the input and initializes session (`frontend/query_processor.py`)
3. **SessionManager** provides conversation context (`frontend/session_manager.py`)
4. **OrchestratorService** receives the query (`services/orchestrator/orchestrator.py`)
5. **ClassificationService** classifies it as a "data_query" (`services/classification/classifier.py`)
6. **RuleService** provides rules for SQL generation (`services/rules/rule_service.py`)
7. **SQLGenerationService** generates the SQL: `SELECT COUNT(*) FROM orders WHERE completion_date = '2025-02-25'` (`services/sql/sql_generator.py`)
8. **SQLExecutionService** executes the SQL and returns results (`services/sql/sql_executor.py`)
9. **ResponseService** formats the result: "There were 42 orders completed on February 25, 2025." (`services/response/response_formatter.py`)
10. **SessionManager** updates history with the query and response (`frontend/session_manager.py`)
11. **Streamlit UI** displays the response to the user (`frontend/ui.py`)

The entire process happens within milliseconds, with the most time-consuming parts being the AI-based classification and SQL generation steps.

## Key Benefits of the Architecture

- **Separation of Concerns**: Each service has a clear, focused responsibility
- **Scalability**: Services can be scaled independently based on load
- **Testability**: Components can be tested in isolation with mocks
- **Flexibility**: New query types or processing paths can be added with minimal changes
- **Maintainability**: Services can be updated independently
- **Error Isolation**: Failures in one service don't crash the entire system
- **Clear Data Flow**: The system has a well-defined processing pipeline
- **Configurability**: Service behavior can be adjusted through configuration