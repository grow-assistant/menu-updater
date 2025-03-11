# Swoop AI Development Plan & Collaboration Guide

## Conversation Framework

### Initial Setup
1. **Establish AI capabilities**: "You are an expert programmer skilled in Python, Streamlit, LangChain, SQL, and voice integration technologies. You understand restaurant management systems and data analytics."

2. **Project context**: "Swoop AI is a restaurant data assistant that helps managers analyze performance, manage menus, and answer business questions through a conversational interface with voice capabilities."

3. **Current status**: "We've integrated LangChain for the agent architecture, ElevenLabs for voice output, speech recognition for voice input, and multi-location support with a Streamlit UI."

4. **Request planning**: "Before coding, please summarize your understanding of the project and outline a plan for implementing [specific feature]. Don't write any code yet."

### For Each Development Iteration

**Request this structure for each response:**

1. **Explanation phase**: "First, explain in detail what you're planning to implement, including:
   - The logic behind the solution
   - How it integrates with existing components
   - Why this approach is optimal
   - Any potential edge cases to handle"

2. **Implementation phase**: "Then provide the necessary code changes with clear comments"

3. **Recap phase**: "Finally, recap what we've accomplished and outline what should be tackled next according to our plan"

## Project Roadmap

### Phase 1: Core Infrastructure (Completed)
- ✓ LangChain agent integration with custom tools
- ✓ Streamlit UI with chat interface
- ✓ Basic voice output with ElevenLabs
- ✓ Multi-location support

### Phase 2: Enhanced Voice & Interaction (In Progress)
- Speech recognition for hands-free operation
- Voice persona customization
- Auto-listen feature after responses
- Improved error handling for voice systems

### Phase 3: Advanced Analytics
- Visualization tool integration
- Complex query handling for time-based analytics
- Performance optimization for large datasets
- Enhanced context management for follow-up questions

### Phase 4: Testing & Refinement
- User acceptance testing
- Performance optimization
- Edge case handling
- Documentation updates

## Guidelines for Maintaining Context

1. **Reference the plan regularly**: "Before we continue, let's review our plan to ensure we're on track."

2. **Summarize progress**: "Please summarize what we've accomplished so far and what's next on our roadmap."

3. **Address context degradation**: "I notice we might be drifting from our plan. Let me restate our goals and current phase..."

4. **Document key decisions**: Keep track of important design decisions and technical choices for future reference.

## Technical Integration Points

When working on new features, consider these integration points:

1. **LangChain Agent**: How the feature interacts with the agent architecture
   - Tool definitions in `utils/langchain_integration.py`
   - Agent creation and memory management

2. **Voice System**: Integration with ElevenLabs and speech recognition
   - Voice persona configuration in `prompts/personas.py`
   - Speech recognition in `background_speech_recognition_with_timeout()`

3. **UI Components**: Streamlit interface elements
   - Chat display and interaction
   - Sidebar configuration options
   - Status indicators and feedback

4. **Data Flow**: How information moves through the system
   - Query processing pipeline
   - Response formatting for both text and voice
   - Context preservation between interactions

## Success Metrics

For each feature implementation, evaluate against these criteria:

1. **Functionality**: Does it work as expected in all scenarios?
2. **User Experience**: Is it intuitive and responsive?
3. **Robustness**: Does it handle edge cases and errors gracefully?
4. **Integration**: Does it work seamlessly with existing components?
5. **Performance**: Is it efficient with resources and response time? 