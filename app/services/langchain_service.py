"""
LangChain integration services for the Streamlit app.

This module provides LangChain agent setup and integration with query paths.
"""

import os
import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Callable

# Configure logger
logger = logging.getLogger("ai_menu_updater")

# Try to import LangChain components with fallbacks for different versions
try:
    # Try newer LangChain versions first
    try:
        from langchain_core.tools import BaseTool as Tool
        from langchain.agents import AgentType, initialize_agent, AgentExecutor
        from langchain.memory import ConversationBufferMemory
        from langchain_openai import ChatOpenAI
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.outputs import LLMResult
        from langchain_core.agents import AgentAction, AgentFinish
        
        LANGCHAIN_AVAILABLE = True
        logger.info("Using newer LangChain imports")
    except ImportError:
        # Fallback to older LangChain 
        from langchain.tools import BaseTool as Tool
        from langchain.chains import ConversationChain
        from langchain.agents import AgentType, initialize_agent, AgentExecutor
        from langchain.memory import ConversationBufferMemory
        from langchain.chat_models import ChatOpenAI
        from langchain.schema import AgentAction, AgentFinish, LLMResult
        from langchain.callbacks.base import BaseCallbackHandler
        
        LANGCHAIN_AVAILABLE = True
        logger.info("Using older LangChain imports")
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.error("LangChain is not available. Install required packages.")

class StreamlitCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for streaming LangChain output to Streamlit.
    This can be used to update the Streamlit UI in real-time as
    the agent executes.
    """

    def __init__(self, container):
        self.container = container
        self.text = ""
        self.is_thinking = True
        self.tool_used = ""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs
    ) -> None:
        """Called when LLM starts processing"""
        self.text = ""
        self.is_thinking = True
        self.container.empty()
        self.container.markdown("_Thinking..._")

    def on_text(self, text: str, **kwargs) -> None:
        """Called when raw text is available"""
        self.is_thinking = False
        self.text += text
        # Apply a typewriter effect with clean formatting
        self.container.markdown(self.text + "▌")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Stream tokens to Streamlit UI with a cleaner display"""
        self.is_thinking = False
        self.text += token
        # Apply a typewriter effect with clean formatting
        self.container.markdown(self.text + "▌")

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM ends"""
        self.is_thinking = False
        # Remove the cursor at the end
        self.container.markdown(self.text)

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called on LLM error"""
        self.is_thinking = False
        self.container.error(f"Error: {error}")

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs
    ) -> None:
        """Called at the start of a chain"""
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called at the end of a chain"""
        self.is_thinking = False

    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called on chain error"""
        self.is_thinking = False
        self.container.error(f"Chain error: {error}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs
    ) -> None:
        """Called when a tool starts running"""
        tool_name = serialized.get("name", "unknown")
        self.tool_used = tool_name
        with self.container:
            try:
                # This might fail in older Streamlit versions
                with self.container.status(f"Using tool: {tool_name}", state="running"):
                    self.container.write(f"Input: {input_str[:100]}")
            except:
                # Fallback for older Streamlit versions
                self.container.info(f"Using tool: {tool_name}")
                self.container.write(f"Input: {input_str[:100]}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends"""
        if self.tool_used:
            with self.container:
                self.container.success(f"Tool '{self.tool_used}' completed")
        self.tool_used = ""

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called on tool error"""
        self.container.error(f"Tool error: {error}")
        self.tool_used = ""

    def on_agent_action(self, action: AgentAction, **kwargs) -> Any:
        """Run when agent takes action"""
        with self.container:
            self.container.info(
                f"**Action**: {action.tool}\n**Input**: {action.tool_input[:150]}..."
            )

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Run when agent finishes"""
        self.is_thinking = False


def create_sql_database_tool(execute_query_func: Callable) -> Tool:
    """
    Create a Tool for executing SQL queries on the database.
    
    Args:
        execute_query_func: Function that executes SQL queries
        
    Returns:
        Tool: A LangChain Tool for executing SQL queries
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error("LangChain is not available. Cannot create SQL tool.")
        return None

    try:
        # Define the function that will be called by the tool
        def _run_query(query: str) -> str:
            """Execute a SQL query and return the results as a string"""
            logger.info(f"Executing SQL query: {query}")
            
            # Execute the query
            result = execute_query_func(query)
            
            # Check if the query was successful
            if result.get("success", False):
                # Return the results as a string
                return str(result.get("results", []))
            else:
                # Return an error message
                return f"Error executing query: {result.get('error', 'Unknown error')}"

        # Create the tool
        return Tool(
            name="sql_database",
            func=_run_query,
            description="""Useful for when you need to execute SQL queries against the database.

Important database schema information:
- The orders table has columns: id, customer_id, location_id, created_at, updated_at, status (NOT order_date or order_status)
- For date filtering, use 'updated_at' instead of 'order_date'
- For status filtering, use 'status' (NOT 'order_status')
- Date format should be 'YYYY-MM-DD'
- When querying orders without a specific status filter, ALWAYS filter for completed orders (status = 7)

Example valid queries:
- SELECT COUNT(*) FROM orders WHERE updated_at::date = '2025-02-21' AND status = 7; -- 7 is the status code for completed orders
- SELECT * FROM orders WHERE updated_at BETWEEN '2025-02-01' AND '2025-02-28' AND status = 7;
- SELECT * FROM orders WHERE status = 7; -- Default to completed orders""",
        )
    except Exception as e:
        logger.error(f"Error creating SQL tool: {str(e)}")
        return None


def create_menu_update_tool(execute_update_func: Callable) -> Tool:
    """
    Create a Tool for updating menu items.
    
    Args:
        execute_update_func: Function that executes menu updates
        
    Returns:
        Tool: A LangChain Tool for updating menu items
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error("LangChain is not available. Cannot create menu update tool.")
        return None

    try:
        # Define the function that will be called by the tool
        def _run_update(update_spec: str) -> str:
            """Execute a menu update and return the results as a string"""
            try:
                # Parse the update specification
                spec = json.loads(update_spec)
                
                # Log the update
                logger.info(f"Executing menu update: {update_spec}")

                # Execute the update
                result = execute_update_func(spec)

                if result.get("success", False):
                    return f"Update successful. Affected {result.get('affected_rows', 0)} rows."
                else:
                    return f"Error updating menu: {result.get('error', 'Unknown error')}"
            except json.JSONDecodeError:
                return "Error: Invalid JSON in update specification"
            except Exception as e:
                return f"Error parsing update specification: {str(e)}"

        # Create the tool
        return Tool(
            name="update_menu",
            func=_run_update,
            description="""Useful for updating menu items, prices, or enabling/disabling items.

The input should be a JSON object with the following structure:
{
  "item_name": "The name of the menu item to update",
  "new_price": 10.99,  // Optional: The new price of the item
  "disabled": true     // Optional: Set to true to disable, false to enable
}

You must include either new_price or disabled, but not necessarily both.
The item_name is always required.

Examples:
- Update price: {"item_name": "French Fries", "new_price": 5.99}
- Disable item: {"item_name": "Club Sandwich", "disabled": true}
- Enable item: {"item_name": "Caesar Salad", "disabled": false}
""",
        )
    except Exception as e:
        logger.error(f"Error creating menu update tool: {str(e)}")
        return None


def create_tools_for_agent(location_id: int = 62) -> List[Tool]:
    """
    Create all needed tools for the LangChain agent.
    
    Args:
        location_id: Location ID to use for queries
        
    Returns:
        List[Tool]: List of LangChain tools
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error("LangChain is not available. Cannot create agent tools.")
        return []

    logger.info(f"Creating tools for agent with location_id: {location_id}")
    tools = []
    
    # Import database functions only when needed
    from app.utils.database import execute_sql_query
    
    # SQL database tool
    def _execute_query_wrapper(query: str) -> Dict[str, Any]:
        """Execute SQL query with the location ID"""
        return execute_sql_query(query, location_id)
    
    sql_tool = create_sql_database_tool(execute_query_func=_execute_query_wrapper)
    if sql_tool:
        tools.append(sql_tool)

    # Menu update tool
    def _execute_menu_update(update_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute menu update with proper SQL generation"""
        item_name = update_spec.get("item_name")
        new_price = update_spec.get("new_price")
        disabled = update_spec.get("disabled")

        if not item_name:
            return {
                "success": False,
                "error": "Missing item_name in update specification",
            }

        if new_price is not None:
            # Update price query
            query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        elif disabled is not None:
            # Enable/disable query
            disabled_value = str(disabled).lower()
            query = f"UPDATE items SET disabled = {disabled_value} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        else:
            return {
                "success": False,
                "error": "Invalid update specification - must include either new_price or disabled",
            }

        return execute_sql_query(query, location_id)

    menu_tool = create_menu_update_tool(execute_update_func=_execute_menu_update)
    if menu_tool:
        tools.append(menu_tool)

    return tools


def create_langchain_agent(
    openai_api_key: str = None,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.3,
    streaming: bool = True,
    callback_handler = None,
    memory = None,
    tools: List[Tool] = None,
    verbose: bool = False,
) -> AgentExecutor:
    """
    Create a LangChain agent with the specified configuration.
    
    Args:
        openai_api_key: OpenAI API key
        model_name: Model name to use
        temperature: Temperature for the model
        streaming: Whether to use streaming
        callback_handler: Callback handler for UI updates
        memory: Memory object for the agent
        tools: List of tools to use
        verbose: Whether to log verbose output
        
    Returns:
        AgentExecutor: The LangChain agent
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error("LangChain is not available. Cannot create agent.")
        return None

    # Use provided API key or get from environment
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment")

    # Create the LLM
    llm_kwargs = {
        "model_name": model_name,
        "temperature": temperature,
        "openai_api_key": api_key,
    }

    # Only add streaming if supported in this environment
    if streaming:
        llm_kwargs["streaming"] = True

    # Create the LLM with ChatOpenAI
    llm = ChatOpenAI(**llm_kwargs)

    # Set up callbacks
    callbacks = None
    if callback_handler:
        callbacks = [callback_handler]

    # Create memory if not provided
    if memory is None:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

    # Initialize tools list if not provided
    if tools is None:
        tools = []

    try:
        # For newer LangChain, initialize the agent with callbacks
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=memory,
            verbose=verbose,
        )

        # Set the callbacks on the agent executor if needed
        if callbacks and hasattr(agent, "callbacks"):
            agent.callbacks = callbacks

        return agent
    except Exception as e:
        # Fallback method if there was an error with the first approach
        try:
            # Try the alternate approach with different parameters
            agent_kwargs = {
                "llm": llm,
                "tools": tools,
                "verbose": verbose,
                "memory": memory,
            }

            if callbacks:
                agent_kwargs["callbacks"] = callbacks

            agent = AgentExecutor.from_agent_and_tools(
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                tools=tools,
                llm=llm,
                verbose=verbose,
                memory=memory,
            )

            return agent
        except Exception as inner_e:
            logger.error(f"Failed to initialize agent: {str(e)}. Inner error: {str(inner_e)}")
            raise ValueError(
                f"Failed to initialize agent: {str(e)}. Inner error: {str(inner_e)}"
            )


def process_query_with_langchain(
    query: str,
    tools: List[Tool],
    context: Dict[str, Any] = None,
    agent = None,
    callback_handler = None,
) -> Dict[str, Any]:
    """
    Process a query using the LangChain agent.
    
    Args:
        query: User query
        tools: List of tools for the agent
        context: Context from previous queries
        agent: Existing agent to use, or None to create a new one
        callback_handler: Callback handler for streaming
        
    Returns:
        Dict: Results from the agent execution
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error("LangChain is not available. Cannot process query.")
        return {
            "success": False,
            "error": "LangChain is not available.",
            "text_answer": "I'm sorry, but the LangChain integration is not available. Please check your installation."
        }

    # Log the incoming user query
    logger.info(f"Processing query with LangChain: '{query}'")
    
    # Initialize context if not provided
    if context is None:
        context = {}
    
    try:
        # Import main_integration directly here to avoid circular imports
        try:
            import main_integration
            from main_integration import integrate_with_existing_flow
            
            # Process using main_integration
            result = integrate_with_existing_flow(
                query=query,
                tools=tools,
                context=context,
                agent=agent,
                callback_handler=callback_handler,
            )
            
            return result
        except ImportError:
            logger.warning("main_integration module not found, using direct agent execution")
            
            # Create agent if needed
            if agent is None:
                agent = create_langchain_agent(
                    tools=tools,
                    verbose=True,
                    callback_handler=callback_handler
                )
                
            # Run the agent directly
            agent_result = agent.run(query)
            
            # Format the result
            return {
                "success": True,
                "summary": agent_result,
                "verbal_answer": agent_result,
                "text_answer": agent_result,
                "agent_result": agent_result,
                "context": context,
            }
            
    except Exception as e:
        logger.error(f"Error processing query with LangChain: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "verbal_answer": f"I encountered an error: {str(e)}",
            "text_answer": f"**Error Processing Query**\n\nI encountered the following error: {str(e)}",
        } 