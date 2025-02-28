# LangChain Integration for Swoop AI

This document provides an overview of how LangChain has been integrated with the Swoop AI application to enhance its capabilities.

## Overview

LangChain is a framework designed to simplify the development of applications using Large Language Models (LLMs). It provides tools for building sophisticated applications powered by LLMs without having to write complex custom code.

In this integration, we've added the following LangChain capabilities to the Swoop AI application:

1. **Agent-based query handling** - LangChain agents can use tools to handle complex queries by breaking them down into steps
2. **Conversation memory** - Persistent memory across queries for better context handling
3. **Streaming responses** - Real-time streaming of responses to improve user experience
4. **Structured tools** - Custom tools for SQL execution and menu updates

## Files Added

- `utils/langchain_integration.py` - Core integration utilities and classes
- `langchain_app.py` - A standalone Streamlit app using LangChain
- `LANGCHAIN_INTEGRATION.md` - This documentation file

## How to Use

### Running the LangChain-Integrated App

To run the application with LangChain integration:

```bash
streamlit run langchain_app.py
```

This will start a Streamlit server with the LangChain-integrated version of Swoop AI.

### Using LangChain Components in Your Existing App

You can also integrate the LangChain components into your existing app by importing from the `utils.langchain_integration` module:

```python
from utils.langchain_integration import (
    create_langchain_agent,
    StreamlitCallbackHandler,
    SQLDatabaseTool,
    MenuUpdateTool,
    integrate_with_existing_flow
)
```

## Key Components

### 1. StreamlitCallbackHandler

This callback handler enables real-time streaming of responses to the Streamlit UI. It displays intermediate steps of the agent's thinking process and the final response.

### 2. Custom Tools

#### SQLDatabaseTool

Executes SQL queries against your database using your existing database connection functions.

```python
sql_tool = SQLDatabaseTool(execute_query_func=your_sql_execution_function)
```

#### MenuUpdateTool

Updates menu items, prices, and item status (enabled/disabled) using your existing menu update functions.

```python
menu_tool = MenuUpdateTool(execute_update_func=your_menu_update_function)
```

### 3. Agent Creation

The `create_langchain_agent` function creates a LangChain agent with the specified configuration:

```python
agent = create_langchain_agent(
    tools=tools,
    memory=memory,
    verbose=True,
    model_name="gpt-4-turbo",
    temperature=0.3,
    streaming=True
)
```

### 4. Integration with Existing Flow

The `integrate_with_existing_flow` function provides a bridge between your existing query processing flow and LangChain:

```python
result = integrate_with_existing_flow(
    query=user_query,
    tools=tools,
    context=existing_context,
    agent=agent,
    callback_handler=callback_handler
)
```

The function implements the complete 4-step flow from `integrate_app.py`:

1. **OpenAI Query Categorization**: Uses OpenAI to categorize the query and extract metadata
2. **Google Gemini SQL Generation**: Generates SQL based on the query type and metadata
3. **SQL Execution**: Executes the SQL query with error handling and retries
4. **OpenAI Result Summarization**: Summarizes the results with both verbal and text answers

The LangChain agent is used as a fallback mechanism if any step in the process fails. This ensures that users always get a response, even if there are issues with the primary flow.

If the flow completes successfully, the function returns a comprehensive result object with:

```python
{
    "success": True,
    "summary": "Formatted text answer for display",
    "verbal_answer": "Concise verbal response for voice output",
    "text_answer": "Detailed text response",
    "sql_query": "Generated SQL query",
    "execution_result": {/* SQL execution results */},
    "categorization": {/* Query categorization data */},
    "steps": {/* Status and data for each step */},
    "context": {/* Updated context for next query */}
}
```

## Customization Options

### Adding New Tools

To add new tools, create a new class that extends the LangChain `Tool` class:

```python
class MyCustomTool(Tool):
    name = "custom_tool"
    description = "Description of what the tool does"
    
    def __init__(self, your_function):
        super().__init__(name=self.name, func=self._run, description=self.description)
        self.your_function = your_function
    
    def _run(self, input_str: str) -> str:
        # Process the input and call your function
        result = self.your_function(input_str)
        return str(result)
```

### Customizing the Agent

You can customize the agent by modifying the `create_langchain_agent` function call:

```python
agent = create_langchain_agent(
    tools=tools,
    memory=memory,
    verbose=True,
    model_name="gpt-3.5-turbo",  # Use a different model
    temperature=0.7,  # Increase creativity
    streaming=True
)
```

## Performance Considerations

- The LangChain agent makes multiple API calls to the LLM, which can increase latency and token usage
- Consider implementing caching for frequent queries
- For simple queries, you might want to bypass the agent and use a direct call to the LLM

## Comparison with Original Approach

| Feature | Original Approach | LangChain Approach |
|---------|------------------|-------------------|
| Conversation memory | Limited | Enhanced with ConversationBufferMemory |
| Tool selection | Manual in code | Automatic by agent |
| Response streaming | No | Yes |
| Error handling | Custom | Integrated with agent |
| Multiple steps | Manual orchestration | Automatic by agent |

## Example Queries

Here are some example queries that showcase the power of the LangChain integration:

1. "What were the top-selling items last month?"
2. "Increase the price of the chicken sandwich by $2"
3. "Show me the revenue trend over the past 3 months"
4. "Disable the seasonal dessert menu items"
5. "Which staff member processed the most orders yesterday?"

## Troubleshooting

### Agent Not Using Tools

If the agent isn't using the tools as expected, check:
- Tool descriptions - Make them clearer and more specific
- Input format - Ensure the input format matches what the tool expects
- Error handling - Check for errors in the tool execution

### High Latency

If you're experiencing high latency:
- Use a faster model (e.g., gpt-3.5-turbo instead of gpt-4)
- Implement caching for repeated queries
- Reduce the context size being sent to the agent

### Memory Issues

If the agent isn't remembering previous context:
- Ensure the memory object is being preserved between requests
- Check that the memory is being correctly passed to the agent
- Consider using a different memory implementation (e.g., ConversationSummaryMemory for longer conversations)

## Next Steps

Future enhancements to consider:
1. Adding document retrieval tools for accessing documentation and help content
2. Implementing more sophisticated memory with summaries for longer conversations
3. Creating specialized agents for different types of queries
4. Adding feedback collection to improve the agent over time 