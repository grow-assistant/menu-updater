"""
LangChain integration for the Swoop AI application.
This module provides classes and functions to integrate LangChain functionality
into the existing Swoop AI application.
"""

import os
import re
import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import streamlit as st

# Store current session ID
current_session_id = None

# Configure logging
def setup_logging():
    """Ensure logging is properly configured with the necessary directories"""
    global current_session_id
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Generate a session ID based on timestamp
    current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_log_path = f"logs/session_{current_session_id}.log"
    
    # Reset root logger to avoid duplicate handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # Create a formatter for consistent log formatting
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure root logger with multiple handlers
    root_logger.setLevel(logging.INFO)
    
    # Handler for global log file (all sessions)
    global_file_handler = logging.FileHandler("logs/ai_interaction.log")
    global_file_handler.setFormatter(formatter)
    root_logger.addHandler(global_file_handler)
    
    # Handler for session-specific log file
    session_file_handler = logging.FileHandler(session_log_path)
    session_file_handler.setFormatter(formatter)
    root_logger.addHandler(session_file_handler)
    
    # Handler for console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Get the application-specific logger
    logger = logging.getLogger("ai_menu_updater")
    logger.info(f"Session {current_session_id} started - Logging to both global log and {session_log_path}")
    
    return logger

# Set up logging
logger = setup_logging()

# LangChain imports for version 0.0.150
from langchain.chains import ConversationChain
from langchain.agents import AgentType, initialize_agent, Tool, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Load environment variables
load_dotenv()


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
        """Called when a tool starts running - show this in the UI"""
        tool_name = serialized.get("name", "unknown")
        self.tool_used = tool_name
        with self.container:
            with st.status(f"Using tool: {tool_name}", state="running"):
                st.write(f"Input: {input_str[:100]}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends - show completion in UI"""
        if self.tool_used:
            with self.container:
                st.success(f"Tool '{self.tool_used}' completed")
        self.tool_used = ""

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called on tool error"""
        self.container.error(f"Tool error: {error}")
        self.tool_used = ""

    def on_agent_action(self, action: AgentAction, **kwargs) -> Any:
        """Run when agent takes action - display nicely"""
        with self.container:
            st.info(
                f"**Action**: {action.tool}\n**Input**: {action.tool_input[:150]}..."
            )

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Run when agent finishes"""
        self.is_thinking = False


def create_sql_database_tool(execute_query_func):
    """
    Create a Tool for executing SQL queries on the database.

    Args:
        execute_query_func: Function that executes SQL queries

    Returns:
        Tool: A LangChain Tool for executing SQL queries
    """

    def _run_query(query: str) -> str:
        result = execute_query_func(query)
        if result.get("success", False):
            return str(result.get("results", []))
        else:
            return f"Error executing query: {result.get('error', 'Unknown error')}"

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


def create_menu_update_tool(execute_update_func):
    """
    Create a Tool for updating menu items.

    Args:
        execute_update_func: Function that executes menu updates

    Returns:
        Tool: A LangChain Tool for updating menu items
    """

    def _run_update(update_spec: str) -> str:
        try:
            # Parse the update specification
            import json

            spec = json.loads(update_spec)

            # Execute the update
            result = execute_update_func(spec)

            if result.get("success", False):
                return f"Update successful. Affected {result.get('affected_rows', 0)} rows."
            else:
                return f"Error updating menu: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"Error parsing update specification: {str(e)}"

    return Tool(
        name="update_menu",
        func=_run_update,
        description="Useful for updating menu items, prices, or enabling/disabling items.",
    )


def create_langchain_agent(
    openai_api_key: str = None,
    model_name: str = "gpt-3.5-turbo",  # Use model compatible with older OpenAI
    temperature: float = 0.3,
    streaming: bool = True,
    callback_handler=None,
    memory=None,
    tools: List[Tool] = None,
    verbose: bool = False,
) -> AgentExecutor:
    """
    Create a LangChain agent with the specified configuration.

    Args:
        openai_api_key: OpenAI API key (will use env var if not provided)
        model_name: Name of the OpenAI model to use
        temperature: Temperature for the model
        streaming: Whether to stream the output
        callback_handler: Callback handler for streaming output
        memory: Memory to use for the agent
        tools: List of tools for the agent to use
        verbose: Whether to print verbose output

    Returns:
        AgentExecutor: The configured LangChain agent
    """
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
    elif streaming and verbose:
        callbacks = [StreamingStdOutCallbackHandler()]

    # Create memory if not provided
    if memory is None:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

    # Initialize tools list if not provided
    if tools is None:
        tools = []

    try:
        # For LangChain 0.0.150, initialize the agent with the callbacks in the specific way that works
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
            raise ValueError(
                f"Failed to initialize agent: {str(e)}. Inner error: {str(inner_e)}"
            )


def create_simple_chain(
    openai_api_key: str = None,
    model_name: str = "gpt-3.5-turbo",  # Use model compatible with older OpenAI
    temperature: float = 0.3,
    streaming: bool = True,
    callback_handler=None,
    prompt_template: str = None,
    system_message: str = None,
) -> ConversationChain:
    """
    Create a simple LangChain conversation chain.

    Args:
        openai_api_key: OpenAI API key (will use env var if not provided)
        model_name: Name of the OpenAI model to use
        temperature: Temperature for the model
        streaming: Whether to stream the output
        callback_handler: Callback handler for streaming output
        prompt_template: Custom prompt template to use
        system_message: System message to use

    Returns:
        ConversationChain: The configured conversation chain
    """
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

    # Create the LLM instance
    llm = ChatOpenAI(**llm_kwargs)

    # Prepare callbacks for chain initialization - don't set them on LLM
    callbacks = None
    if callback_handler:
        callbacks = [callback_handler]

    # Create memory
    memory = ConversationBufferMemory(return_messages=True)

    # Create prompt template if provided
    chain_kwargs = {"llm": llm, "memory": memory, "verbose": True}

    # Add callbacks to chain initialization if they exist
    if callbacks:
        chain_kwargs["callbacks"] = callbacks

    if prompt_template:
        prompt = PromptTemplate(
            input_variables=["history", "input"], template=prompt_template
        )
        chain_kwargs["prompt"] = prompt

    # Create the chain
    chain = ConversationChain(**chain_kwargs)

    return chain


def integrate_with_existing_flow(
    query: str,
    tools: List[Tool],
    context: Dict[str, Any] = None,
    agent: Optional[AgentExecutor] = None,
    callback_handler=None,
) -> Dict[str, Any]:
    """
    Integrate LangChain with the existing query flow.

    Args:
        query: User query
        tools: List of tools to use
        context: Context from previous queries
        agent: Existing agent to use, or None to create a new one
        callback_handler: Callback handler for streaming

    Returns:
        Dict: Results from the agent execution
    """
    # Log the incoming user query
    logger.info(f"Received user query: '{query}'")
    
    from integrate_app import (
        get_clients,
        create_categorization_prompt,
        call_sql_generator,
        create_summary_prompt,
        create_system_prompt_with_business_rules,
        load_application_context,
    )
    import app  # For SQL execution
    import openai

    # Remove the import of OpenAI class which doesn't exist in version 0.28.1
    # from openai import OpenAI

    # Initialize callback if provided
    # callbacks = [callback_handler] if callback_handler else None

    # Tracking for the 4-step flow
    flow_steps = {
        "categorization": {
            "name": "OpenAI Categorization",
            "status": "pending",
            "data": None,
        },
        "sql_generation": {"name": "SQL Generation", "status": "pending", "data": None},
        "execution": {"name": "SQL Execution", "status": "pending", "data": None},
        "summarization": {
            "name": "Result Summarization",
            "status": "pending",
            "data": None,
        },
    }

    try:
        # Get clients for API access
        openai_client, _ = get_clients()

        # Load context from previous state
        conversation_history = []
        if context and "conversation_history" in context:
            conversation_history = context["conversation_history"]

        # Get cached dates from previous context
        cached_dates = context.get("date_filter") if context else None

        # STEP 1: OpenAI Categorization
        if callback_handler:
            callback_handler.on_text("Step 1: OpenAI Query Categorization\n")

        # Create prompt with cached dates context
        categorization_result = create_categorization_prompt(cached_dates=cached_dates)
        categorization_prompt = categorization_result["prompt"]

        # Check if the OpenAI client has the right structure for the version used
        # Handle both old and new OpenAI API versions
        try:
            # For new OpenAI client (>=1.0.0)
            categorization_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": categorization_prompt},
                    {
                        "role": "user",
                        "content": f"Analyze this query and return a JSON response: {query}",
                    },
                ],
                response_format={"type": "json_object"},
            )
        except (AttributeError, TypeError):
            # For older OpenAI client (<1.0.0) or if client is a function
            # Try to create a new OpenAI client
            try:
                # Directly try the new API format
                # Use the legacy OpenAI API format for 0.28.1
                categorization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": categorization_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this query and return a JSON response: {query}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )
            except (ImportError, Exception):
                # Try old OpenAI SDK style
                categorization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": categorization_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this query and return a JSON response: {query}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )

        # Process OpenAI response
        if hasattr(categorization_response, "choices"):
            # New OpenAI API format
            raw_response = categorization_response.choices[0].message.content
        else:
            # Old OpenAI API format
            raw_response = categorization_response["choices"][0]["message"]["content"]

        json_response = json.loads(raw_response)
        
        # Log the categorization response
        logger.info(f"Categorization response: {raw_response[:200]}..." if len(raw_response) > 200 else raw_response)
        
        # For long responses, also dump to a file for easier debugging
        if len(raw_response) > 1000:
            log_to_file(raw_response, prefix="categorization")

        # Update flow tracking
        flow_steps["categorization"]["data"] = json_response
        flow_steps["categorization"]["status"] = "completed"

        # Extract query metadata
        query_type = json_response.get("request_type")
        time_period = json_response.get("time_period")
        start_date = json_response.get("start_date")
        end_date = json_response.get("end_date")
        item_name = json_response.get("item_name")
        new_price = json_response.get("new_price")

        if callback_handler:
            callback_handler.on_text(f"Query categorized as: {query_type}\n")

        # STEP 2: Google Gemini SQL Generation
        if callback_handler:
            callback_handler.on_text("\nStep 2: Google Gemini SQL Generation\n")

        # Load application context
        context_files = load_application_context()

        # Determine SQL based on query type
        sql_query = None

        # For direct menu operations, generate SQL directly
        if query_type in ["update_price", "disable_item", "enable_item"]:
            if query_type == "update_price" and item_name and new_price:
                # Get location IDs from session
                location_ids = context.get(
                    "selected_location_ids", [1]
                )  # Default to location 1

                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                else:
                    location_id = location_ids[0] if location_ids else 1
                    sql_query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
            elif query_type in ["disable_item", "enable_item"] and item_name:
                state = "true" if query_type == "disable_item" else "false"

                # Get location IDs from session
                location_ids = context.get(
                    "selected_location_ids", [1]
                )  # Default to location 1

                if len(location_ids) > 1:
                    locations_str = ", ".join(map(str, location_ids))
                    sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id IN ({locations_str}) RETURNING *"
                else:
                    location_id = location_ids[0] if location_ids else 1
                    sql_query = f"UPDATE items SET disabled = {state} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        else:
            # For analytics queries, use Google Gemini to generate SQL
            # Format date context
            date_context_str = ""
            if start_date and end_date:
                date_context_str = f"""
                ACTIVE DATE FILTERS:
                - Start Date: {start_date}
                - End Date: {end_date}
                """
            elif time_period:
                date_context_str = f"""
                ACTIVE DATE FILTERS:
                - Time Period: {time_period}
                """

            # Get location ID from context
            location_id = context.get(
                "selected_location_id", 1
            )  # Default to location 1
            location_ids = context.get(
                "selected_location_ids", [1]
            )  # Default to location 1

            # Get previous SQL for context
            previous_sql = None
            if context and "last_sql_query" in context:
                previous_sql = context["last_sql_query"]

            # Call Google Gemini to generate SQL
            sql_query = call_sql_generator(
                query,
                context_files,
                location_id=location_id,
                previous_sql=previous_sql,
                conversation_history=conversation_history,
                date_context=date_context_str,
                time_period=time_period,
                location_ids=location_ids,
            )

            # Log the generated SQL query
            logger.info(f"Generated SQL query: {sql_query}")
            
            # For complex queries, also dump to a file for easier debugging
            if len(sql_query) > 500:
                log_to_file(sql_query, prefix="sql_query")

        # Update flow tracking
        if sql_query:
            flow_steps["sql_generation"]["data"] = {"sql_query": sql_query}
            flow_steps["sql_generation"]["status"] = "completed"

            if callback_handler:
                # Format SQL for display
                display_sql = sql_query.strip().replace("\n", " ").replace("  ", " ")
                callback_handler.on_text(f"Generated SQL: {display_sql}\n")
        else:
            flow_steps["sql_generation"]["status"] = "error"
            flow_steps["sql_generation"]["data"] = {"error": "Failed to generate SQL"}

            if callback_handler:
                callback_handler.on_text("Error: Failed to generate SQL\n")

            # If we can't generate SQL, use the LangChain agent as fallback
            if agent is None:
                agent = create_langchain_agent(
                    tools=tools, verbose=True, callback_handler=callback_handler
                )

            # Run the agent with callbacks passed directly
            agent_result = agent.run(query)

            return {
                "success": True,
                "summary": agent_result,
                "agent_result": agent_result,
                "context": context or {},
                "steps": flow_steps,
            }

        # STEP 3: SQL Execution
        if callback_handler:
            callback_handler.on_text("\nStep 3: SQL Execution\n")

        # Execute SQL query with timeout and retries
        max_retries = 2
        execution_result = None

        for attempt in range(max_retries + 1):
            try:
                execution_result = app.execute_menu_query(sql_query)
                break
            except Exception:
                if attempt < max_retries:
                    if callback_handler:
                        callback_handler.on_text(
                            f"Retry {attempt+1}/{max_retries} after execution error\n"
                        )
                else:
                    raise

        # Update flow tracking
        if execution_result and execution_result.get("success"):
            flow_steps["execution"]["data"] = execution_result
            flow_steps["execution"]["status"] = "completed"

            result_count = len(execution_result.get("results", []))
            if callback_handler:
                callback_handler.on_text(f"Query returned {result_count} result(s)\n")
        else:
            error_msg = (
                execution_result.get("error", "Unknown error")
                if execution_result
                else "Execution failed"
            )
            flow_steps["execution"]["status"] = "error"
            flow_steps["execution"]["data"] = {"error": error_msg}

            if callback_handler:
                callback_handler.on_text(f"SQL Execution Error: {error_msg}\n")

            # If execution fails, use the LangChain agent as fallback
            if agent is None:
                agent = create_langchain_agent(
                    tools=tools, verbose=True, callback_handler=callback_handler
                )

            # Run the agent with callbacks passed directly
            agent_result = agent.run(query)

            return {
                "success": True,
                "summary": agent_result,
                "agent_result": agent_result,
                "context": context or {},
                "steps": flow_steps,
            }

        # STEP 4: Result Summarization
        if callback_handler:
            callback_handler.on_text("\nStep 4: Result Summarization\n")

        # Create summary prompt
        summary_prompt = create_summary_prompt(
            query,
            sql_query,
            execution_result,
            query_type=query_type,
            conversation_history=conversation_history,
        )

        # Get system prompt with business rules
        system_prompt = create_system_prompt_with_business_rules()

        # Updated prompt to request both verbal and text answers
        enhanced_summary_prompt = f"""
{summary_prompt}

IMPORTANT: Please provide TWO distinct responses:
1. VERBAL_ANSWER: Provide a CONCISE but natural-sounding response that will be spoken aloud.
   - Keep it brief (2-3 conversational sentences)
   - Include key numbers and facts with a natural speaking cadence
   - You can use brief conversational elements like "We had" or "I found"
   - Avoid unnecessary elaboration, metaphors, or overly formal language
   - Focus on the most important information, but sound like a helpful colleague
   - No need for follow-up questions
   - When mentioning dates, use "on February 21st, 2025" format with clear comma pauses
   - Avoid ambiguous date formats that might be misinterpreted when spoken
   - Always add a comma before the year when mentioning a full date
   - For number ranges, say "from X to Y" rather than "X-Y"

2. TEXT_ANSWER: A more detailed response with all relevant information, formatted nicely for display on screen.

Format your response exactly like this:
VERBAL_ANSWER: [Your concise, natural-sounding response here]
TEXT_ANSWER: [Your detailed response here]
"""

        # Handle both old and new OpenAI API versions for summarization
        try:
            # For new OpenAI client (>=1.0.0)
            summarization_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_summary_prompt},
                ],
                temperature=0.2,
            )
        except (AttributeError, TypeError):
            # For older OpenAI client (<1.0.0) or if client is a function
            try:
                # Directly try the new API format
                # Use the legacy OpenAI API format for 0.28.1
                summarization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": enhanced_summary_prompt},
                    ],
                    temperature=0.2,
                )
            except (ImportError, Exception):
                # Try old OpenAI SDK style
                summarization_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": enhanced_summary_prompt},
                    ],
                    temperature=0.2,
                )

        # Process OpenAI response
        if hasattr(summarization_response, "choices"):
            # New OpenAI API format
            raw_response = summarization_response.choices[0].message.content
        else:
            # Old OpenAI API format
            raw_response = summarization_response["choices"][0]["message"]["content"]
            
        # Log the summarization response
        logger.info(f"Summarization response: {raw_response[:200]}..." if len(raw_response) > 200 else raw_response)
        
        # For long responses, also dump to a file for easier debugging
        if len(raw_response) > 1000:
            log_to_file(raw_response, prefix="summarization")

        # Parse the verbal and text answers
        verbal_answer = None
        text_answer = None

        # Extract verbal answer
        verbal_match = re.search(
            r"VERBAL_ANSWER:(.*?)(?=TEXT_ANSWER:|$)", raw_response, re.DOTALL
        )
        if verbal_match:
            verbal_answer = verbal_match.group(1).strip()
            # Clean the verbal answer for speech
            verbal_answer = clean_text_for_speech(verbal_answer)

        # Extract text answer
        text_match = re.search(r"TEXT_ANSWER:(.*?)$", raw_response, re.DOTALL)
        if text_match:
            text_answer = text_match.group(1).strip()

        # Create summary
        summary = text_answer or raw_response

        # Update flow tracking
        flow_steps["summarization"]["data"] = {"summary": summary}
        flow_steps["summarization"]["status"] = "completed"

        if callback_handler:
            callback_handler.on_text(f"\nResult: {summary}\n")

        # Update context with the new information
        updated_context = context or {}
        updated_context["last_sql_query"] = sql_query

        # Add the current query and response to conversation history
        conversation_entry = {"query": query, "response": summary, "sql": sql_query}

        if "conversation_history" not in updated_context:
            updated_context["conversation_history"] = []

        updated_context["conversation_history"].append(conversation_entry)

        # Update date filter cache
        if start_date and end_date:
            updated_context["date_filter"] = {
                "start_date": start_date,
                "end_date": end_date,
            }

        # Return results
        return {
            "success": True,
            "summary": summary,
            "verbal_answer": verbal_answer,
            "text_answer": text_answer,
            "sql_query": sql_query,
            "execution_result": execution_result,
            "categorization": json_response,
            "steps": flow_steps,
            "context": updated_context,
        }

    except Exception as e:
        # If anything fails, fall back to the LangChain agent
        if callback_handler:
            callback_handler.on_text(
                f"\nError in flow: {str(e)}\nFalling back to LangChain agent\n"
            )
            
        # Log the error
        logger.error(f"Error in AI flow: {str(e)}", exc_info=True)

        # Create or use existing agent
        if agent is None:
            agent = create_langchain_agent(
                tools=tools, verbose=True, callback_handler=callback_handler
            )

        try:
            # Run the agent with callbacks passed directly
            result = agent.run(query)
        except Exception as agent_error:
            result = f"Error running agent: {str(agent_error)}"

        # Return the result in a format compatible with the existing flow
        return {
            "success": True,
            "summary": result,
            "agent_result": result,
            "fallback": True,
            "error": str(e),
            "context": context or {},
        }


def clean_text_for_speech(text):
    """
    Clean and format text to be more appropriate for text-to-speech engines.
    This ensures dates, numbers, and other elements are properly formatted
    for clear verbal communication.
    
    Uses advanced NLP libraries:
    - textacy: For advanced text normalization
    - num2words: For converting numbers to words
    - unidecode: For handling special characters
    - re: For precise pattern matching with regular expressions
    """
    import re
    from num2words import num2words
    from unidecode import unidecode
    import textacy.preprocessing.normalize as tpn
    import textacy.preprocessing.replace as tpr
    
    if not text:
        return text
    
    # 1. BASIC CLEANUP
    
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    
    # Remove markdown formatting 
    text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)  # Remove ** and * (bold and italic)
    text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)  # Remove bullet points
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # Remove markdown headers
    
    # 2. NORMALIZE TEXT WITH TEXTACY
    
    # Normalize whitespace, quotation marks, dashes, etc.
    text = tpn.whitespace(text)
    text = tpn.hyphenated_words(text)
    text = tpn.quotation_marks(text)
    
    # 3. HANDLE EMAIL AND PHONE FORMATS
    
    # Handle email addresses
    text = re.sub(r'([\w.+-]+@[\w-]+\.[\w.-]+)', r' email address ', text)
    
    # Handle phone numbers more consistently
    text = re.sub(r'(?<!\w)(?:\+?1[-\s]?)?(?:\(?\d{3}\)?[-\s]?)?(?:\d{3}[-\s]?)\d{4}(?!\w)', ' phone number ', text)
    
    # 4. DATE FORMATTING
    
    # First remove any spaces in ordinal suffixes like "21 st" -> "21st"
    # This needs to run before any other date formatting
    text = re.sub(r'(\d+)\s+(st|nd|rd|th)\b', r'\1\2', text)
    
    # Get list of month names for pattern matching
    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 
        'August', 'September', 'October', 'November', 'December'
    ]
    month_pattern = r'\b(?:' + '|'.join(month_names) + r')\s+'
    
    # Step 1: Convert ordinal dates in the context of month names (like "January 21st")
    def convert_month_ordinal(match):
        month = match.group(1)
        day_num = int(match.group(2))
        suffix = match.group(3)
        year = match.group(4) if len(match.groups()) >= 4 and match.group(4) else ""
        
        # Convert day number to words
        day_words = num2words(day_num, ordinal=True)
        
        # Format with or without year
        if year:
            return f"{month} {day_words}, {year}"
        else:
            return f"{month} {day_words}"
    
    # Handle "Month DDst" and "Month DDst YYYY" formats
    month_ordinal_pattern = r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)(\d+)(st|nd|rd|th)\b(?:\s+(\d{4})\b)?'
    text = re.sub(month_ordinal_pattern, convert_month_ordinal, text)
    
    # Step 2: Flag parts that have already been processed to avoid double conversion
    # Create placeholders for already processed month-date combinations
    processed_month_dates = {}
    
    # Create a copy for processing other ordinal dates
    processed_text = text
    
    # Step 3: Convert other ordinal dates not attached to months
    def convert_other_ordinal(match):
        num = int(match.group(1))
        suffix = match.group(2)
        
        # Skip if this part is inside a month-date that was already processed
        # This is a simplified check - in a production system, you'd want more robust detection
        start_pos = match.start()
        for month in month_names:
            if month in processed_text[max(0, start_pos-20):start_pos]:
                return match.group(0)  # Return unchanged if part of a month name format
                
        # For all other cases, convert to ordinal words
        return num2words(num, ordinal=True)
    
    # Handle "the DDst" and other standalone ordinal cases
    # Process only numbers followed by ordinal suffixes that are not part of converted month patterns
    ordinal_pattern = r'(\d+)(st|nd|rd|th)\b'
    text = re.sub(ordinal_pattern, convert_other_ordinal, text)
    
    # Do NOT re-add spacing for ordinal suffixes to avoid TTS saying "saint" for "st"
    # text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1 \2', text)
    
    # Handle "Month DDst YYYY" -> "Month DDst, YYYY"
    text = re.sub(
        r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+(?:st|nd|rd|th)?)\s+(\d{4})\b',
        r'\1, \2',
        text
    )
    
    # Also handle without suffix
    text = re.sub(
        r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+)\s+(\d{4})\b',
        r'\1, \2',
        text
    )
    
    # Handle MM/DD/YYYY format: "01/15/2025" -> "01 15, 2025"
    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{4})\b', r'\1 \2, \3', text)
    
    # Handle ISO dates YYYY-MM-DD: "2025-03-10" -> "2025, March 10"
    months = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December',
        '1': 'January', '2': 'February', '3': 'March', '4': 'April', 
        '5': 'May', '6': 'June', '7': 'July', '8': 'August',
        '9': 'September'
    }
    
    def replace_iso_date(match):
        year = match.group(1)
        month = match.group(2)
        day = match.group(3).lstrip('0')  # Remove leading zero
        
        # Convert month number to name
        month_name = months.get(month, month)
        
        # Convert day to ordinal word form
        day_word = num2words(int(day), ordinal=True)
        
        return f"{year}, {month_name} {day_word}"
    
    text = re.sub(r'(\d{4})-(\d{2}|\d)-(\d{2}|\d)\b', replace_iso_date, text)
    
    # 5. NUMBER HANDLING
    
    # Handle common number ranges that shouldn't be expanded (like years)
    text = re.sub(r'(\d{4})-(\d{4})', r'\1 to \2', text)  # Convert "2023-2024" to "2023 to 2024"
    
    # Format dollar amounts for better speech
    # Add a trailing zero to ensure 2 decimal places: $25.5 -> $25.50
    def add_trailing_zero(match):
        dollars = match.group(1)
        cents = match.group(2)
        return f"${dollars}.{cents}0"
    
    text = re.sub(r'\$(\d+)\.(\d)(?!\d)', add_trailing_zero, text)
    
    # Convert "$25.50 - $30.75" to "$25.50 to $30.75"
    text = re.sub(r'\$(\d+\.\d{2})\s*-\s*\$(\d+\.\d{2})', r'$\1 to $\2', text)
    
    # 6. SELECTIVE NUMBER-TO-WORD CONVERSION
    # Convert small standalone numbers to words (but preserve larger numbers, years, etc.)
    def convert_small_numbers(match):
        number = int(match.group(0))
        if 0 <= number <= 20:  # Only convert small numbers
            return num2words(number)
        return match.group(0)
    
    # Convert small numbers that stand alone or at start of sentences
    text = re.sub(r'(?<!\d)(?<!\$)(?<![a-zA-Z])\b([0-9]|1[0-9]|20)\b(?![a-zA-Z]|%|\d)', convert_small_numbers, text)
    
    # 7. ABBREVIATION HANDLING
    
    # Replace common abbreviations with full words
    abbreviations = {
        'vs.': 'versus',
        'vs': 'versus',
        'etc.': 'etcetera',
        'e.g.': 'for example',
        'i.e.': 'that is',
        'approx.': 'approximately',
        'Dr.': 'Doctor',
        'Mr.': 'Mister',
        'Mrs.': 'Misses',
        'Ms.': 'Miss',
        'Sr.': 'Senior',
        'Jr.': 'Junior',
        'Prof.': 'Professor',
        'Dept.': 'Department',
        'St.': 'Street',
        'Ave.': 'Avenue',
        'Blvd.': 'Boulevard',
        'Co.': 'Company'
    }
    
    for abbr, full in abbreviations.items():
        # Ensure we match whole words with word boundaries
        text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, text)
    
    # Fix "vs" abbreviation when attached to numbers
    text = re.sub(r'(\$?\d+[\.\d]*)\s*vs\s*\.?\s*(\$?\d+[\.\d]*)', r'\1 versus \2', text)
    
    # 8. SPACING AND FORMATTING
    
    # Fix number-word combinations: "15items" -> "15 items"
    text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)
    
    # Replace special characters for better speech
    text = re.sub(r'&', 'and', text)
    text = re.sub(r'@', 'at', text)
    text = re.sub(r'#', 'number', text)
    
    # Ensure periods have spacing
    text = re.sub(r'\.([A-Za-z])', r'. \1', text)
    
    # 9. FINAL CLEANUP WITH UNIDECODE
    
    # Convert any remaining special characters to closest ASCII equivalent
    text = unidecode(text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def test_speech_cleaning():
    """Test the clean_text_for_speech function with various examples"""
    test_cases = [
        "Orders on February 21st 2025 were higher than expected.",
        "Orders on February 21 2025 were higher than expected.",
        "Orders on February 21 st 2025 were higher than expected.",  # Spaced suffix
        "Revenue for 01/15/2025 was $5000.",
        "Comparing data from 2025-03-10 to 2025-03-15 shows growth.",
        "Sales increased by 15% on March 3rd 2025.",
        "Sales increased by 15% on March 3 rd 2025.",  # Spaced suffix  
        "We sold 15items on Tuesday.",
        "The average order value was $25.5vs.$20.8 last week.",
        "Comparing December 15th 2024 to January 5th 2025, we see a 12% increase.",
        # New test cases
        "Visit https://example.com for more information!",
        "Contact us at +1 (555) 123-4567 or email@example.com",
        "The range 2023-2024 shows a 5-10% improvement.",
        "Our company, Dr. Smith & Co., will host an event.",
        "The temperature is approx. 72° today vs. 65° yesterday.",
        "For small numbers: 1 2 3 show as words, but 25, 100, 1000 stay as digits.",
        "The product costs $9.5 today, down from $10.5 yesterday.",
        # Ordinal date conversion test cases
        "The meeting is on the 21st of July.",
        "Please submit your report by January 3rd.",
        "The event will take place on October 22nd, 2025.",
        "He was born on the 15th of May, 1990.",
        "We'll celebrate the 1st, 2nd, and 3rd place winners.",
        "The 4th quarter results were impressive.",
        "May 5th and June 6th are important dates.",
        "The 31st of December is New Year's Eve."
    ]
    
    print("===== SPEECH CLEANING TEST =====")
    for case in test_cases:
        cleaned = clean_text_for_speech(case)
        print(f"\nOriginal: {case}")
        print(f"Cleaned:  {cleaned}")
    print("===============================")
    return "Test completed."

def get_current_session_id():
    """Return the current session ID for use in other parts of the application"""
    global current_session_id
    return current_session_id

def get_session_log_path():
    """Return the path to the current session's log file"""
    global current_session_id
    if current_session_id:
        return f"logs/session_{current_session_id}.log"
    return None

def log_to_file(content, filename=None, prefix="dump"):
    """
    Dumps content to a file in the logs directory for debugging
    
    Args:
        content: Content to dump (string, dict, or other object)
        filename: Optional filename, if None a timestamped name will be used
        prefix: Prefix for auto-generated filenames
        
    Returns:
        Path to the created file
    """
    global current_session_id
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if current_session_id:
            filename = f"{prefix}_{current_session_id}_{timestamp}.txt"
        else:
            filename = f"{prefix}_{timestamp}.txt"
    
    file_path = os.path.join("logs", filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        if isinstance(content, str):
            f.write(content)
        else:
            try:
                # Try to convert to JSON
                f.write(json.dumps(content, indent=2))
            except (TypeError, ValueError, OverflowError) as e:
                # Fallback to string representation with error note
                f.write(f"Error converting to JSON: {str(e)}\n\n")
                f.write(str(content))
    
    logger = logging.getLogger("ai_menu_updater")
    logger.info(f"Content dumped to {file_path}")
    
    return file_path

def log_session_end():
    """
    Log the end of the current session for easier log analysis
    """
    global current_session_id
    if current_session_id:
        logger = logging.getLogger("ai_menu_updater")
        logger.info(f"Session {current_session_id} ended")
        
        # Create a summary file with session statistics if needed
        # This is where you could add code to analyze the session logs and generate stats

def get_recent_logs(n_lines=20, session_specific=True):
    """
    Get the most recent log entries from either the session log or global log
    
    Args:
        n_lines: Number of lines to retrieve
        session_specific: If True, get logs from the current session only
        
    Returns:
        List of log lines
    """
    if session_specific and current_session_id:
        log_path = get_session_log_path()
    else:
        log_path = "logs/ai_interaction.log"
    
    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                # Read all lines and take the last n_lines
                lines = f.readlines()
                return lines[-n_lines:] if len(lines) > n_lines else lines
    except Exception as e:
        logger = logging.getLogger("ai_menu_updater")
        logger.error(f"Error reading log file: {str(e)}")
    
    return []

def cleanup_old_logs(days_to_keep=30):
    """
    Remove log files older than the specified number of days
    
    Args:
        days_to_keep: Number of days to keep logs for
        
    Returns:
        Number of files deleted
    """
    # Calculate the cutoff time
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_time.timestamp()
    
    # Get all log files
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return 0
    
    files_deleted = 0
    
    # Process each file
    for filename in os.listdir(log_dir):
        if filename.startswith("session_") and filename.endswith(".log"):
            file_path = os.path.join(log_dir, filename)
            
            # Skip the README.md file
            if filename == "README.md":
                continue
                
            # Skip the global log file
            if filename == "ai_interaction.log":
                continue
            
            # Check file modification time
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_timestamp:
                try:
                    os.remove(file_path)
                    files_deleted += 1
                except Exception as e:
                    logger = logging.getLogger("ai_menu_updater")
                    logger.error(f"Error deleting log file {file_path}: {str(e)}")
    
    return files_deleted
