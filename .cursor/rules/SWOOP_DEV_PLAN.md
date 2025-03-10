# Swoop AI Conversational Query Flow Implementation Plan

## Project Overview

Swoop AI enables club managers to interact with their data through natural conversation, allowing them to:
- Query order history and analytics
- Get information about current menus
- Perform actions like editing prices, enabling/disabling items, options, and option items

This implementation plan outlines the development approach for building the conversational query flow system described in the requirements document.

## Current Implementation Status

### Phase 1: Core Framework & Classification
✅ **COMPLETED**
- Basic architecture has been set up
- Query classification system implemented
- Basic orchestration services created
- Initial context management implemented
- Test suite established

### Phase 2: Specialized Services
✅ **COMPLETED**
- Created a new branch `phase2-specialized-services` from `phase1-query-processor`
- Implemented:
  - Enhanced Context Manager with reference resolution
  - Enhanced Temporal Analysis Service with comparative analysis
  - Entity Resolution Service with fuzzy matching
  - Action Handler with confirmation workflow
  - Comprehensive tests for all new components
  - Integration with the orchestrator

### Phase 3: Data Integration & Response Generation
🔄 **IN PROGRESS**
- Created a new branch `phase3-data-integration` from `phase2-specialized-services`
- Implemented:
  - ✅ Enhanced data access layer with connection pooling and query caching
  - ✅ Database connection manager with robust error handling
  - ✅ Query cache manager with performance optimization
  - ✅ Response Service with template management and natural language generation
  - ✅ Query Processor integrating data access and response generation
  - ✅ Schema Inspector with metadata caching and relationship discovery
  - ✅ Enhanced error handling with centralized error management system
  - ✅ Tests for all new components
- Currently implementing:
  - Performance optimization
  - Comprehensive integration tests

### Implementation Tasks for Phase 2
1. ✅ Created Entity Resolution Service
2. ✅ Enhanced Context Manager with reference resolution
3. ✅ Enhanced Temporal Analysis Service
4. ✅ Created Action Handler
5. ✅ Added tests for all new components
6. ✅ Integrated new services into the orchestrator

### Implementation Tasks for Phase 3
1. ✅ Implement enhanced data access layer
   - ✅ Database connection manager with connection pooling
   - ✅ Query cache manager with performance optimization
   - ✅ Enhanced data access interface with integrated caching
   - ✅ Tests for data access components
2. ✅ Develop response formation and delivery
   - ✅ Template-based response generation
   - ✅ Multiple response types (data, action, error, clarification)
   - ✅ Context-aware response formatting
   - ✅ Natural language variations
3. ✅ Integrate data access with response generation
   - ✅ Query Processor service 
   - ✅ Error handling and recovery
   - ✅ Performance tracking
4. ✅ Implement schema introspection and metadata caching
   - ✅ Schema Inspector service
   - ✅ Database relationship discovery
   - ✅ Query optimization hints
   - ✅ Join condition suggestions
5. ✅ Implement centralized error handling
   - ✅ Standardized error types and codes
   - ✅ Context-aware error messages
   - ✅ Recovery suggestions
   - ✅ Error metrics collection
   - ✅ Detailed logging
6. ⏳ Optimize performance
7. ⏳ Add comprehensive integration tests
8. ⏳ Document API and component interactions

## System Architecture 

### High-Level Components

```
┌─────────────────────┐
│  Frontend           │  • Chat interface
│  (Streamlit)        │  • Voice input/output
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Query Processor    │  • Classification module
│  & Orchestrator     │  • Parameter validation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Specialized        │  • Context Manager
│  Services           │  • Temporal Analysis
│                     │  • Entity Resolution
│                     │  • Clarification
│                     │  • Action Handler
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Data Access Layer  │  • DB connectors
│                     │  • API integrations
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Response Service   │  • Formatting
│                     │  • Delivery (text/voice)
└─────────────────────┘
```

## Development Workflow & Branching Strategy

To ensure systematic development and easy rollback capability, we'll follow a structured branching strategy with comprehensive testing at each step.

### Branching Structure

```
main
 │
 ├── phase1-core-framework
 │        │
 │        └── phase2-specialized-services
 │                 │
 │                 └── phase3-data-integration
 │                          │
 │                          └── phase4-testing-refinement
 │
 └── hotfixes (if needed)
```

### Development Process for Each Phase

1. **Create Branch**
   - Each phase will have its own branch created from the previous phase branch
   - Branch naming convention: `phase{number}-{description}`
   - Initial phase1 branch is created from main

2. **Implement Features**
   - Develop features according to the phase requirements
   - Commit frequently with descriptive commit messages
   - Document changes and implementation details

3. **Write Tests**
   - Write comprehensive unit tests for all components
   - Create integration tests for component interactions
   - Develop scenario-based tests for real-world use cases

4. **Test Verification**
   - Run full test suite: `pytest`
   - Ensure all tests pass with minimum 90% coverage
   - Fix any failing tests before proceeding

5. **Code Review**
   - Submit for code review
   - Address feedback and make necessary adjustments
   - Get approval from at least one reviewer

6. **Merge to Next Phase**
   - Once fully tested and approved, this branch becomes the base for the next phase
   - Create the next phase branch from this point

### Testing Requirements

Before moving to the next phase, the current phase must meet these criteria:
- All unit tests pass
- All integration tests pass
- Code coverage is at least 90%
- All scenario tests for implemented features pass

### Rollback Procedure

If issues are discovered in a later phase:
1. Identify the last stable phase branch
2. Create a hotfix branch from that phase
3. Fix the issue and test thoroughly
4. Merge back into the sequential branches

## Implementation Roadmap

### Phase 1: Core Framework & Classification (2 weeks)

#### Branch: `phase1-core-framework`

#### Objectives:
- Set up the foundational architecture
- Implement the query classification system
- Create basic orchestration services
- Establish initial context management

#### Key Components:

1. **Query Processor**
   - Query classification using NLP:
     - Order history queries
     - Menu queries
     - Action requests
     - Clarification responses
   - Parameter extraction and validation
   - Confidence scoring

2. **Basic Orchestrator**
   - Service routing based on classification
   - Error handling and logging
   - Basic context preservation between turns

3. **Initial Context Manager**
   - Context storage (query type, entities, time periods, filters)
   - Basic session management
   - Context retrieval for follow-up queries

#### Technical Specifications:

```python
# Query classification model requirements
- Model: Fine-tuned transformer-based classification model
- Minimum accuracy: 90% on validation set
- Input: Raw user query text
- Output: Query type, confidence score, extracted parameters

# Context manager data structure
- User session ID
- Conversation history (last 10 turns)
- Current topic/intent
- Active entities (items, categories, etc.)
- Time references and resolutions
- Active filters
- Pending actions
```

#### Success Criteria:
- Correctly classify >90% of test queries
- Successfully route queries to appropriate mock services
- Maintain basic context over multi-turn conversations

#### Testing Requirements:
- Unit tests for each component
- Integration tests for component interactions
- Test with sample conversations
- Run `pytest` to verify all tests pass before moving to Phase 2

### Phase 2: Specialized Services (3 weeks)

#### Branch: `phase2-specialized-services` (created from `phase1-core-framework`)

#### Objectives:
- Implement all specialized services for query processing
- Develop robust context management
- Create clarification workflow

#### Key Components:

1. **Enhanced Context Manager**
   - Full implementation of context tracking
   - Topic change detection
   - Context reset/update logic
   - Reference resolution (e.g., "that category")

2. **Temporal Analysis Service**
   - Date/time expression parsing
   - Relative time reference resolution (e.g., "last month")
   - Default time period management
   - Time ambiguity detection

3. **Entity Resolution Service**
   - Menu item/category lookup and matching
   - Fuzzy matching for approximate names
   - Pronoun and reference resolution
   - Entity type classification

4. **Clarification Service**
   - Missing information detection
   - Clarification question generation
   - Multi-turn clarification state tracking
   - Response incorporation into original query

5. **Action Handler**
   - Action validation and authorization
   - Confirmation workflow for critical changes
   - Action execution and result verification
   - Undo/rollback capability

#### Technical Specifications:

```python
# Temporal Analysis Requirements
- Support for explicit dates (e.g., "October 2024")
- Support for relative dates (e.g., "last month", "previous quarter")
- Support for ranges (e.g., "between January and March")
- Default resolution for vague terms (e.g., "recently" → last 7 days)

# Entity Resolution 
- Direct matching against database entities
- Fuzzy matching (Levenshtein distance < 0.2)
- Contextual reference resolution (e.g., "that item" → from previous turn)
- Ambiguity detection threshold: < 90% confidence

# Clarification Workflow States
- NEED_CLARIFICATION: Missing required parameters
- CLARIFYING: Waiting for user response to clarification
- RECEIVED_CLARIFICATION: Processing user clarification
- RESOLVED: All required information collected
```

#### Success Criteria:
- Correctly resolve >85% of temporal references
- Successfully resolve >85% of entity references
- Generate appropriate clarification questions for ambiguous queries
- Successfully execute actions with proper validation

#### Testing Requirements:
- Comprehensive tests for each specialized service
- Integration tests for interactions between services
- Scenario-based tests for each service workflow
- Run `pytest` with minimum 90% coverage before moving to Phase 3

### Phase 3: Data Integration & Response Generation (2 weeks)

#### Branch: `phase3-data-integration` (created from `phase2-specialized-services`)

#### Objectives:
- Implement data access layer for real data
- Develop response formation and delivery
- Enhance error handling
- Optimize performance

#### Key Components:

1. **Data Access Layer**
   - Database connectors (SQL)
   - API integrations
   - Caching layer for performance
   - Error handling and retries

2. **Query Execution Engine**
   - SQL query generation
   - Results processing
   - Aggregation and analysis
   - Performance optimization

3. **Response Service**
   - Response template management
   - Natural language generation
   - Context-aware response formatting
   - Multi-modal response preparation (text/voice)

4. **Error Handling Service**
   - Error classification
   - User-friendly error messages
   - Recovery suggestions
   - Logging and monitoring

#### Technical Specifications:

```python
# Data Access Layer
- Connection pooling
- Query parameterization for security
- Result set pagination (max 1000 records per query)
- Timeout handling (max 5 seconds)

# Response Templates
- Order history responses
- Menu information responses
- Action confirmation responses
- Error and clarification responses
- Each with variations for different contexts

# Performance Requirements
- Query processing < 100ms
- Database operations < 500ms
- Total response time < 1s for 95% of queries
```

#### Success Criteria:
- Successfully retrieve accurate data for >95% of valid queries
- Generate natural, context-aware responses
- Meet performance requirements under load
- Gracefully handle all error conditions

#### Testing Requirements:
- Unit tests for data access and response generation
- Integration tests with test databases
- Performance tests to verify response time requirements
- End-to-end tests for full query-to-response flow
- Run `pytest` with all tests passing before moving to Phase 4

### Phase 4: Testing & Refinement (2 weeks)

#### Branch: `phase4-testing-refinement` (created from `phase3-data-integration`)

#### Objectives:
- Comprehensive testing of the entire system
- Scenario-based validation
- Performance optimization
- Documentation finalization

#### Key Components:

1. **Automated Testing Suite**
   - Unit tests for all components
   - Integration tests for component interactions
   - End-to-end scenario tests based on real-life examples
   - Performance and load testing

2. **Scenario Validation**
   - Test cases covering all scenarios in the requirements
   - Edge case testing
   - Error path testing
   - Multi-turn conversation testing

3. **Performance Optimization**
   - Profiling and bottleneck identification
   - Query optimization
   - Caching enhancements
   - Resource utilization improvements

4. **Documentation**
   - API documentation
   - Component interaction diagrams
   - Development guides
   - Maintenance procedures

#### Technical Specifications:

```python
# Test Coverage Requirements
- Minimum unit test coverage: 90%
- Scenario coverage: 100% of documented scenarios
- Performance test criteria: 95% of requests < 1s

# Documentation Deliverables
- Architecture overview
- Component specifications
- API documentation
- Database schema
- Deployment guide
- Troubleshooting manual
```

#### Success Criteria:
- Pass >95% of automated tests
- Successfully handle all documented scenarios
- Meet performance requirements under load
- Complete and accurate documentation

#### Testing Requirements:
- Full system tests across all components
- Load testing with simulated user volumes
- Final comprehensive test suite run before deployment
- Run `pytest` with full coverage to verify all functionality

## Detailed Technical Specifications

### Context Manager Implementation

The Context Manager is a critical component that maintains conversation state across turns.

```python
class ConversationContext:
    def __init__(self, session_id):
        self.session_id = session_id
        self.conversation_history = []  # List of (query, response) tuples
        self.current_topic = None  # 'order_history', 'menu', 'action'
        self.active_entities = {
            'items': [],
            'categories': [],
            'options': [],
            'option_items': []
        }
        self.time_references = {
            'explicit_dates': [],  # Parsed datetime objects
            'relative_references': [],  # E.g., 'last month'
            'resolved_time_period': None  # Final resolved time period
        }
        self.active_filters = []  # E.g., {'field': 'price', 'operator': '>', 'value': 100}
        self.clarification_state = None  # NONE, NEED_CLARIFICATION, CLARIFYING, etc.
        self.pending_actions = []  # Actions awaiting confirmation
        
    def update_with_query(self, query, classification_result):
        # Update context based on new query
        pass
        
    def detect_topic_change(self, new_topic):
        # Return True if topic has changed
        pass
        
    def reset_for_new_topic(self, new_topic):
        # Reset relevant parts of context for new topic
        pass
        
    def resolve_references(self, query):
        # Resolve pronouns and references to previous entities
        pass
```

### Query Classification Implementation

The Query Classifier determines the intent and extracts parameters.

```python
class QueryClassifier:
    def __init__(self, model_path):
        # Load NLP model
        pass
        
    def classify(self, query_text):
        """
        Classify the query and extract parameters
        
        Returns:
            dict: {
                'query_type': 'order_history'|'menu'|'action'|'clarification',
                'confidence': 0.95,
                'extracted_params': {
                    'time_references': [...],
                    'entities': [...],
                    'filters': [...],
                    'actions': [...]
                }
            }
        """
        pass
```

### Temporal Analysis Service Implementation

```python
class TemporalAnalysisService:
    def __init__(self):
        # Initialize date/time parsers
        pass
        
    def analyze(self, query_text, context):
        """
        Extract and resolve time references
        
        Returns:
            dict: {
                'explicit_dates': [...],
                'relative_references': [...],
                'resolved_time_period': {
                    'start_date': datetime,
                    'end_date': datetime
                },
                'is_ambiguous': False,
                'needs_clarification': False,
                'clarification_question': None
            }
        """
        pass
        
    def resolve_relative_reference(self, reference, base_date=None):
        """
        Resolve references like 'last month', 'previous quarter'
        """
        pass
```

### Clarification Service Implementation

```python
class ClarificationService:
    def __init__(self):
        pass
        
    def check_needs_clarification(self, query_classification, context):
        """
        Check if query needs clarification
        
        Returns:
            dict: {
                'needs_clarification': True|False,
                'missing_parameters': [...],
                'clarification_question': 'For what time period?',
                'clarification_type': 'time'|'entity'|'filter'|'action'
            }
        """
        pass
        
    def process_clarification_response(self, original_query, clarification_response, clarification_type):
        """
        Incorporate clarification response into original query
        
        Returns:
            dict: {
                'updated_query': str,
                'resolved_parameters': {...},
                'is_fully_resolved': True|False
            }
        """
        pass
```

## Real-Life Scenario Implementation Details

### Scenario 1: Ambiguous Time Reference

**Query Flow:**
1. User: "How many orders were completed last month?"
2. System processes:
   - Query Classifier identifies: type="order_history", params=[time_reference="last month"]
   - Temporal Analysis resolves "last month" to specific date range
   - Context Manager stores the time reference and query type
3. System executes query and responds
4. User follow-up: "How many were over $100?"
5. System processes:
   - Query Classifier identifies: type="order_history", params=[filter="over $100"]
   - Context Manager retrieves previous time reference
   - Combined query executed with both time reference and price filter

**Implementation Focus:**
- Maintaining time references in context
- Adding filters to existing queries
- Recognizing follow-up patterns without explicit time references

### Scenario 2: Ambiguous Initial Query

**Query Flow:**
1. User: "How many orders were completed?"
2. System processes:
   - Query Classifier identifies: type="order_history", missing required param=time_period
   - Clarification Service generates question
3. System asks: "For what time period?"
4. User: "Last week"
5. System processes:
   - Temporal Analysis resolves "last week"
   - Original query combined with clarification
   - Complete query executed

**Implementation Focus:**
- Detecting missing required parameters
- Formulating clarification questions
- Incorporating clarification responses into original queries

### Scenario 3: Multi-turn Exploration with Filters

**Implementation Focus:**
- Tracking comparison queries across time periods
- Determining highest growth categories
- Applying multiple filters (time period, customer type)
- Complex query generation from multiple parameters

### Scenario 4: Topic Change

**Implementation Focus:**
- Detecting shifts in conversation topic
- Appropriate context resetting
- Preserving relevant context across topic changes

### Scenario 5: Correction or Modification

**Implementation Focus:**
- Detecting correction keywords
- Updating existing query parameters
- Re-executing modified queries
- Providing appropriate confirmation of changes

## Integration Points with Existing Systems

### LangChain Integration

```python
# integration with existing LangChain agent
def create_conversational_query_tools():
    """
    Create custom tools for the LangChain agent to support the conversational query flow
    """
    tools = [
        Tool(
            name="query_processor",
            func=process_and_route_query,
            description="Process and route a query through the conversational flow system"
        ),
        Tool(
            name="context_manager",
            func=update_conversation_context,
            description="Update or retrieve conversation context"
        ),
        # Additional tools for specific services
    ]
    return tools
```

### Voice System Integration

```python
# Integration with ElevenLabs and speech recognition
def prepare_voice_response(response_text, context):
    """
    Prepare response for voice output
    - Format for spoken delivery
    - Add clarification cues if needed
    - Adjust pacing based on content type
    """
    pass
```

### UI Integration

```python
# Streamlit integration
def display_conversation_state(st, context):
    """
    Display relevant context information in the UI
    - Current time period
    - Active filters
    - Detected entities
    - Clarification state
    """
    if st.session_state.get('show_debug'):
        with st.expander("Conversation Context"):
            st.write(f"Current topic: {context.current_topic}")
            st.write(f"Time period: {context.time_references['resolved_time_period']}")
            st.write(f"Active filters: {context.active_filters}")
            st.write(f"Entities: {context.active_entities}")
```

## Success Metrics and Validation

### Performance Metrics

- **Response Time:** < 1 second for 95% of queries
- **Accuracy:**
  - Query classification: > 90%
  - Entity resolution: > 85%
  - Temporal resolution: > 85%
  - End-to-end correct responses: > 80%
- **Clarification Rate:** < 25% of queries should require clarification
- **Context Preservation:** > 90% success in follow-up queries

### Validation Approach

1. **Automated Testing:**
   - Unit tests for each component
   - Integration tests for component interactions
   - End-to-end scenario tests

2. **Scenario Testing:**
   - Test suite covering all documented scenarios
   - Additional edge cases and error scenarios
   - Performance testing under load

3. **User Acceptance Testing:**
   - Real-world testing with club managers
   - Feedback collection and analysis
   - Iterative refinement

## Maintenance and Monitoring Plan

1. **Monitoring:**
   - Query success/failure rates
   - Clarification rates by query type
   - Performance metrics
   - Error logs and patterns

2. **Improvement Process:**
   - Regular review of failed queries
   - Model retraining with new examples
   - Performance optimization
   - Feature enhancement based on usage patterns

3. **Documentation:**
   - Maintained API documentation
   - Component specifications
   - Troubleshooting guide
   - Regular updates based on system changes

## Conclusion

This implementation plan provides a detailed roadmap for developing the Swoop AI Conversational Query Flow system. By following this phased approach and focusing on the key components and integration points, we can build a robust system that handles natural conversations with context awareness, clarification capabilities, and accurate response generation.

The plan addresses all the requirements and scenarios outlined in the original document, with special attention to maintaining context, resolving ambiguities, and handling the complexities of real-world conversations. 

The branching strategy ensures that we can track progress methodically and provides the ability to roll back to a stable state if needed. By ensuring comprehensive testing at each phase, we maintain high quality throughout the development process. 