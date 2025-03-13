# API Reference

This document provides the API reference for the major components implemented in Phase 1 of the microservices migration.

## 1. SessionManager API

The `SessionManager` class provides methods for managing session state in the application.

### Class Methods

#### `initialize_session()`

Initializes the session state with default values if it doesn't exist.

**Parameters:** None

**Returns:** None

**Example:**
```python
from frontend.session_manager import SessionManager

# Initialize the session state
SessionManager.initialize_session()
```

#### `get_context()`

Retrieves the current context from the session state.

**Parameters:** None

**Returns:** 
- `dict`: A dictionary containing the current context, including:
  - `user_preferences`: User-specific preferences
  - `recent_queries`: List of recent user queries
  - `session_history`: List of processed queries and responses
  - `active_conversation`: Boolean indicating if there's an ongoing conversation

**Example:**
```python
context = SessionManager.get_context()
recent_queries = context["recent_queries"]
```

#### `update_history(query, result)`

Updates the session history with a new query and result.

**Parameters:**
- `query` (str): The user's query
- `result` (dict): The result from processing the query, containing:
  - `response`: The response text
  - `category`: The query category
  - `metadata`: Additional metadata about the query processing

**Returns:** None

**Example:**
```python
result = {
    "response": "Here are the menu items under $10",
    "category": "data_query",
    "metadata": {
        "sql_query": "SELECT * FROM menu WHERE price < 10",
        "results": [{"name": "Burger", "price": 8.99}]
    }
}
SessionManager.update_history("Show me menu items under $10", result)
```

## 2. ServiceRegistry API

The `ServiceRegistry` class manages service instantiation and lifecycle.

### Class Methods

#### `initialize(config)`

Initializes the ServiceRegistry with the provided configuration.

**Parameters:**
- `config` (dict): Application configuration dictionary

**Returns:** None

**Example:**
```python
from services.utils.service_registry import ServiceRegistry

config = {
    "api": {"openai": {"api_key": "sk-..."}},
    "services": {"classification": {"threshold": 0.7}}
}
ServiceRegistry.initialize(config)
```

#### `register(service_name, service_class)`

Registers a service with the registry.

**Parameters:**
- `service_name` (str): A unique name for the service
- `service_class` (class): The class of the service to instantiate

**Returns:** None

**Example:**
```python
from services.classification.classifier import ClassificationService

ServiceRegistry.register("classification", ClassificationService)
```

#### `get_service(service_name)`

Gets an instance of the requested service, instantiating it if necessary.

**Parameters:**
- `service_name` (str): The name of the service to retrieve

**Returns:**
- Service instance: An instance of the requested service

**Raises:**
- `ServiceNotRegisteredError`: If the service name is not registered
- `ServiceInitializationError`: If the service fails to initialize

**Example:**
```python
classifier = ServiceRegistry.get_service("classification")
category = classifier.classify("Show me menu items under $10", context)
```

#### `check_health()`

Checks the health of all registered services.

**Parameters:** None

**Returns:**
- `dict`: A dictionary mapping service names to their health status (True/False)

**Example:**
```python
health_status = ServiceRegistry.check_health()
for service, is_healthy in health_status.items():
    print(f"{service}: {'Healthy' if is_healthy else 'Unhealthy'}")
```

## 3. ClassificationService API

The `ClassificationService` classifies user queries into predefined categories.

### Methods

#### `__init__(config)`

Initializes the ClassificationService with the provided configuration.

**Parameters:**
- `config` (dict): Configuration dictionary containing API keys and settings

**Example:**
```python
from services.classification.classifier import ClassificationService

config = {
    "api": {
        "openai": {
            "api_key": "sk-...",
            "model": "gpt-4o-mini"
        }
    },
    "services": {
        "classification": {
            "confidence_threshold": 0.7
        }
    }
}

classifier = ClassificationService(config)
```

#### `classify(query, context=None)`

Classifies a user query into a predefined category.

**Parameters:**
- `query` (str): The user's query text
- `context` (dict, optional): Context information for the query

**Returns:**
- `str`: The determined category (e.g., "data_query", "menu_update", "general")

**Example:**
```python
category = classifier.classify("Show me menu items under $10", context)
print(f"Query category: {category}")
```

#### `health_check()`

Checks if the service is operational.

**Parameters:** None

**Returns:**
- `bool`: True if the service is healthy, False otherwise

**Example:**
```python
if classifier.health_check():
    print("Classifier service is healthy")
else:
    print("Classifier service is unhealthy")
```

## 4. OrchestratorService API

The `OrchestratorService` orchestrates the processing of user queries across multiple services.

### Methods

#### `__init__(config)`

Initializes the OrchestratorService with the provided configuration.

**Parameters:**
- `config` (dict): Configuration dictionary with service settings

**Example:**
```python
from services.orchestrator.orchestrator import OrchestratorService

config = {...}  # Configuration dictionary
orchestrator = OrchestratorService(config)
```

#### `process_query(query, context=None)`

Processes a user query by routing it through the appropriate services.

**Parameters:**
- `query` (str): The user's query text
- `context` (dict, optional): Context information for the query

**Returns:**
- `dict`: A result dictionary containing:
  - `response` (str): The response text
  - `category` (str): The query category
  - `metadata` (dict): Additional information about the processing

**Example:**
```python
context = SessionManager.get_context()
result = orchestrator.process_query("Show me menu items under $10", context)

print(f"Response: {result['response']}")
print(f"Category: {result['category']}")
if "sql_query" in result["metadata"]:
    print(f"SQL Query: {result['metadata']['sql_query']}")
```

#### `health_check()`

Checks the health of the orchestrator and its dependent services.

**Parameters:** None

**Returns:**
- `dict`: A dictionary mapping service names to their health status

**Example:**
```python
health_status = orchestrator.health_check()
for service, is_healthy in health_status.items():
    print(f"{service}: {'Healthy' if is_healthy else 'Unhealthy'}")
```

## Common Data Structures

### Query Context

The context dictionary contains information about the current session state:

```python
{
    "user_preferences": {
        "favorite_category": "burgers",
        # ... other preferences
    },
    "recent_queries": [
        "What's on the menu?",
        "Show me vegetarian options"
    ],
    "session_history": [
        {
            "query": "What's on the menu?",
            "response": "We have burgers, salads, and pasta.",
            "category": "general",
            "timestamp": 1621500000
        },
        # ... other history entries
    ],
    "active_conversation": True
}
```

### Query Result

The result dictionary contains the processed response and metadata:

```python
{
    "response": "Here are the menu items under $10",
    "category": "data_query",
    "metadata": {
        "sql_query": "SELECT * FROM menu WHERE price < 10",
        "results": [
            {"name": "Burger", "price": 8.99},
            {"name": "Salad", "price": 7.99}
        ],
        "processing_time": 0.25
    }
}
```

## Error Handling

All components use a consistent error handling approach:

1. **Service-specific exceptions** are raised for domain-specific errors.
2. **General exceptions** are caught at the orchestrator level.
3. **Error results** include an `error` key with details.

Example error result:

```python
{
    "response": "I'm sorry, there was an error processing your query.",
    "category": "error",
    "error": "Failed to generate SQL: Invalid table reference",
    "metadata": {
        "error_type": "SQLGenerationError",
        "query": "Show me menu items from the invalid_table"
    }
}
``` 