# Swoop AI Conversational Query Flow

This project implements a natural language conversational system for interacting with menu and order data in club management systems, as outlined in the SWOOP development plan.

## Overview

The Swoop AI Conversational Query Flow enables club managers to interact with their data through natural language conversations. They can:

- Query order history and analytics
- Get information about current menus
- Perform actions like editing prices, enabling/disabling items, options, and option items

The system is designed to maintain conversation context, handle ambiguities through clarification, and provide natural responses.

## Architecture

The system follows a modular architecture with these main components:

1. **Query Processor & Orchestrator**
   - Classification module
   - Parameter validation
   - Service routing

2. **Specialized Services**
   - Context Manager
   - Temporal Analysis
   - Entity Resolution
   - Clarification
   - Action Handler

3. **Response Service**
   - Formatting
   - Delivery

## Core Components

### Context Manager

The Context Manager maintains conversation state across turns, tracking:
- Conversation history
- Current topic/intent
- Active entities
- Time references
- Filters and pending actions

### Temporal Analysis

The Temporal Analysis Service extracts and resolves time references from queries:
- Explicit dates (e.g., "January 2023")
- Relative references (e.g., "last month")
- Date ranges (e.g., "between March and June")

### Query Classifier

The Query Classifier determines the intent of user queries:
- Order history queries
- Menu information queries
- Action requests
- Clarification responses

### Clarification Service

The Clarification Service handles ambiguous queries:
- Detects missing information
- Generates appropriate clarification questions
- Processes clarification responses
- Updates conversation context

### Query Orchestrator

The Query Orchestrator coordinates all components:
- Routes queries to appropriate services
- Manages the conversation flow
- Preserves context
- Handles clarification workflows

## Usage

### Installation

1. Clone this repository:
   ```
   git clone [repository-url]
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Client

To start an interactive session:

```
python swoop_conversation_client.py
```

Optional arguments:
- `--model [path]`: Path to a custom classification model

### Example Queries

#### Order History Queries

```
"How many orders did we have last month?"
"What was our revenue in January 2023?"
"Show me sales over $100 from last week"
```

#### Menu Queries

```
"What items are in the breakfast category?"
"Is the cheesecake currently enabled?"
"Show me all items under $10"
```

#### Action Requests

```
"Update the price of cheesecake to $9.99"
"Disable the seafood platter"
"Enable all items in the desserts category"
```

### Multi-turn Conversations

The system supports multi-turn conversations with context:

```
User: "How many orders did we have?"
System: "For what time period?"
User: "Last month"
System: "For April 2023, you had 120 orders totaling $3,450.75..."
User: "What about for orders over $50?"
System: "For April 2023, for orders over $50, you had 28 orders..."
```

## Testing

Run the tests with:

```
python -m unittest discover tests
```

## Implementation Status

This implementation covers Phase 1 of the SWOOP development plan, including:
- Core framework and classification
- Basic orchestration
- Context management
- Temporal analysis
- Clarification workflows

Future phases will add:
- Database integration
- Advanced entity resolution
- More sophisticated response generation
- User interface integration

## License

[License information] 