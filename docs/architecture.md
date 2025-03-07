# System Architecture Documentation

## Overview

This document outlines the architecture of the menu query application after the Phase 1 refactoring. The system has been restructured to follow a microservices architecture pattern, with clearly defined components that communicate through well-defined interfaces.

## Component Architecture

The system is composed of the following major components:

```
┌───────────────────────────────────────────────────────────────────┐
│                          Frontend Module                           │
│                                                                    │
│  ┌────────────────┐             ┌────────────────────────────┐    │
│  │  Streamlit UI  │◄────────────┤      Session Manager       │    │
│  └────────────────┘             └────────────────────────────┘    │
│          │                                    ▲                    │
│          ▼                                    │                    │
│  ┌────────────────┐                           │                    │
│  │  User Input    │                           │                    │
│  │  Processing    ├───────────────────────────┘                    │
│  └────────────────┘                                                │
└───────────┬───────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                       Orchestrator Service                         │
│                                                                    │
│  ┌────────────────┐             ┌────────────────────────────┐    │
│  │ Query Router   │◄────────────┤     Service Registry       │    │
│  └────────────────┘             └────────────────────────────┘    │
│          │                                    ▲                    │
│          ▼                                    │                    │
│  ┌────────────────┐                           │                    │
│  │ Result         │                           │                    │
│  │ Formatter      ├───────────────────────────┘                    │
│  └────────────────┘                                                │
└───────────┬───────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                       Backend Services                             │
│                                                                    │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐     │
│  │ Classification │   │ SQL Generation │   │ SQL Execution  │     │
│  │   Service      │   │    Service     │   │    Service     │     │
│  └───────┬────────┘   └────────┬───────┘   └────────┬───────┘     │
│          │                     │                    │              │
│          │            ┌────────▼───────┐            │              │
│          └────────────►  Rule Service  ◄────────────┘              │
│                       └────────────────┘                           │
│                                                                    │
│  ┌────────────────┐                                                │
│  │   Response     │                                                │
│  │   Service      │                                                │
│  └────────────────┘                                                │
└───────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. SessionManager

**Purpose:** Manages the application's state and user session data.

**Responsibilities:**
- Initialize and maintain session state
- Provide context for query processing
- Update conversation history
- Track user preferences and UI state

**Interfaces:**
- `initialize_session()`: Sets up initial session state
- `get_context()`: Retrieves current session context
- `update_history(query, result)`: Updates conversation history

### 2. ServiceRegistry

**Purpose:** Centralizes service management and initialization.

**Responsibilities:**
- Register and instantiate services
- Provide lazy initialization
- Monitor service health
- Handle service initialization errors

**Interfaces:**
- `register(service_name, service_class)`: Register a service
- `get_service(service_name)`: Get an instance of a service
- `check_health()`: Check the health of all services

### 3. OrchestratorService

**Purpose:** Coordinates the flow of requests between services.

**Responsibilities:**
- Route queries to appropriate services
- Manage error handling
- Track processing metrics
- Format and return results

**Interfaces:**
- `process_query(query, context)`: Process a user query
- `health_check()`: Check the health of the orchestrator and its services

### 4. ClassificationService

**Purpose:** Categorizes user queries.

**Responsibilities:**
- Analyze user queries
- Determine query category
- Validate results
- Provide contextual understanding

**Interfaces:**
- `classify(query, context)`: Classify a user query
- `health_check()`: Check the health of the classifier

## Data Flow

1. **User Input** → The user submits a query through the frontend interface.

2. **Context Retrieval** → SessionManager provides context from previous interactions.

3. **Query Classification** → The OrchestratorService sends the query to the ClassificationService to determine its type.

4. **Service Selection** → Based on the classification, the OrchestratorService selects the appropriate processing path.

5. **Query Processing** → For data queries:
   - Retrieves rules and examples
   - Generates SQL
   - Executes SQL
   - Formats the response

6. **Result Delivery** → The result is returned to the frontend.

7. **History Update** → SessionManager updates the conversation history.

## Error Handling

The system implements multi-level error handling:

1. **Service Level** → Each service handles its internal errors and provides meaningful error messages.

2. **Orchestrator Level** → The OrchestratorService catches errors from services and provides fallback mechanisms.

3. **Frontend Level** → The UI displays appropriate error messages and maintains system usability.

## Testing Strategy

The application employs a comprehensive testing strategy:

1. **Unit Tests** → Test individual components in isolation.
   - `test_session_manager.py`
   - `test_service_registry.py`
   - `test_updated_classifier.py`
   - `test_updated_orchestrator.py`

2. **Integration Tests** → Test interactions between components.
   - `test_updated_flow.py` - Tests end-to-end service interactions
   - `test_frontend_integration.py` - Tests frontend integration with backend

## Configuration Management

The application uses a hierarchical configuration system:

1. **Environment Variables** → For sensitive information (API keys)
2. **Configuration Files** → For service settings
3. **Dynamic Configuration** → For runtime adjustable settings

## Future Enhancements

Planned enhancements for future phases include:

1. **Caching Layer** → Implement caching for frequent queries and service results
2. **Service Scaling** → Enable horizontal scaling of services
3. **Monitoring** → Add comprehensive logging and monitoring
4. **Security** → Enhance authentication and authorization mechanisms
5. **API Gateway** → Add a proper API gateway for external service access 