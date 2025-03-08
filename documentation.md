# AI Menu Updater System Documentation

## Overview

The AI Menu Updater is a sophisticated system designed to process natural language queries about menu data, analyze them, generate appropriate SQL queries, execute those queries against a database, and return formatted responses. The system is built around a modular service-oriented architecture where each component has a specific responsibility in the query processing pipeline.

## Service Architecture

The system is organized into several key service modules:

```
services/
├── classification/     # Query classification services
├── execution/          # SQL execution and result formatting
├── orchestrator/       # Main workflow coordinator
├── response/           # Response generation services
├── rules/              # Business rules management
├── sql_generator/      # SQL query generation
└── utils/              # Shared utilities
```

### Orchestrator Service

**Location**: `services/orchestrator/orchestrator.py`

The Orchestrator Service acts as the central coordinator for the entire system. It:

- Manages the workflow between all other services
- Initializes and configures each service component
- Maintains conversation history and context
- Handles the processing of user queries from start to finish
- Coordinates error handling and recovery

The `OrchestratorService` class implements methods like:
- `process_query()`: The main entry point that orchestrates the complete query pipeline
- `health_check()`: Verifies the health of all dependent services
- `set_persona()`: Configures different response tones/styles

### Classification Service

**Location**: `services/classification/`

This service identifies the type and intent of user queries:

- `classifier.py`: Implements the `ClassificationService` class that uses LLMs to categorize queries
- `prompt_builder.py`: Builds prompts for the AI to classify queries
- `classifier_interface.py`: Defines the interface for classification services

Classification is the first step in processing user queries, determining how they should be handled downstream.

### Rules Service

**Location**: `services/rules/`

The Rules Service manages business rules and query patterns:

- `rules_service.py`: Main service for loading, caching and retrieving business rules
- `base_rules.py`: Defines foundational rule structures
- `yaml_loader.py`: Parses YAML rule definitions
- `rules_manager.py`: Coordinates rule application
- `business_rules.py`: Implements specific business logic rules
- `query_rules/`: Directory containing specialized rule sets

This service provides constraints and patterns that guide SQL generation and ensure business logic is applied correctly.

### SQL Generator Service

**Location**: `services/sql_generator/`

This module generates SQL queries from natural language:

- `sql_generator.py`: Base class for SQL generation
- `openai_sql_generator.py`: OpenAI-specific implementation
- `gemini_sql_generator.py`: Google Gemini-specific implementation
- `sql_generator_factory.py`: Factory pattern for creating appropriate generators
- `prompt_builder.py`: Builds prompts for AI SQL generation
- `sql_example_loader.py`: Loads example SQL queries for few-shot learning
- `templates/`: Directory with SQL templates
- `sql_files/`: Directory containing SQL examples and patterns

This service transforms the classified natural language query into executable SQL using AI models.

### Execution Service

**Location**: `services/execution/`

The Execution Service handles database interactions:

- `sql_executor.py`: Main class for executing SQL queries
- `sql_execution_layer.py`: Interface to database execution
- `db_utils.py`: Database connection and utility functions
- `result_formatter.py`: Formats query results for response generation
- `db_analyzer.py`: Analyzes database structures

This service safely executes the generated SQL against the database and formats the results.

### Response Service

**Location**: `services/response/`

This service generates natural language responses:

- `response_generator.py`: Creates human-readable responses from query results
- `prompt_builder.py`: Builds prompts for response generation
- `templates/`: Contains response templates for different scenarios

The Response Service takes query results and transforms them into coherent, natural language responses for the user.

### Utilities

**Location**: `services/utils/`

Shared utility functions and services:

- `service_registry.py`: Service locator pattern implementation
- `logging.py`: Logging configuration and utilities
- `prompt_loader.py`: Loads prompt templates
- `sql_builder.py`: SQL query construction utilities
- `schema_extractor.py`: Database schema analysis tools
- `template_extractor.py`: Template processing utilities
- `conversion_utils.py`: Data type and format conversion
- `text_processing/`: Text manipulation utilities

## Workflow

1. **Query Intake**: User query enters the system through the `OrchestratorService`
2. **Classification**: The query is classified by the `ClassificationService`
3. **Rules Application**: `RulesService` provides relevant business rules
4. **SQL Generation**: `SQLGenerator` creates an SQL query using AI models
5. **Execution**: `SQLExecutor` runs the query against the database
6. **Response Generation**: `ResponseGenerator` creates a natural language response
7. **Return**: Final response is returned to the user

## Integration Points

- **Database Connection**: The system connects to the database through the Execution Service
- **AI Models**: The system uses OpenAI (GPT) and Google (Gemini) models for various AI tasks
- **External Services**: TTS (Text-to-Speech) integration is available through the Orchestrator

## Technical Details

- **Caching**: Various services implement caching for performance optimization
- **Async Support**: Many methods support async operations
- **Error Handling**: Comprehensive error handling throughout the pipeline
- **Health Checks**: Each service provides health check capabilities
- **Configurability**: Services are configured through a centralized configuration system

This architecture allows for flexibility, maintainability, and extensibility while providing robust natural language processing of menu-related queries. 