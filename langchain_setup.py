"""
LangChain agent setup for the AI Menu Updater application.
Contains functions to create and configure LangChain agents.
"""

import os
import logging
from typing import List, Dict, Any, Optional

# LangChain imports - make backward compatible
try:
    # Try newer LangChain versions
    from langchain_core.tools import BaseTool as Tool
    from langchain.chains import ConversationChain
    from langchain.agents import AgentType, initialize_agent, AgentExecutor
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    from langchain_core.agents import AgentAction, AgentFinish
except ImportError:
    # Fallback to older LangChain 
    from langchain.chains import ConversationChain
    from langchain.agents import AgentType, initialize_agent, Tool, AgentExecutor
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate
    from langchain.chat_models import ChatOpenAI
    from langchain.schema import AgentAction, AgentFinish, LLMResult
    from langchain.callbacks.base import BaseCallbackHandler

from config.settings import OPENAI_API_KEY, DEFAULT_LLM_MODEL, LLM_TEMPERATURE

# Configure logger
logger = logging.getLogger("ai_menu_updater")

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
            with self.container.status(f"Using tool: {tool_name}", state="running"):
                self.container.write(f"Input: {input_str[:100]}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends - show completion in UI"""
        if self.tool_used:
            with self.container:
                self.container.success(f"Tool '{self.tool_used}' completed")
        self.tool_used = ""

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called on tool error"""
        self.container.error(f"Tool error: {error}")
        self.tool_used = ""

    def on_agent_action(self, action: AgentAction, **kwargs) -> Any:
        """Run when agent takes action - display nicely"""
        with self.container:
            self.container.info(
                f"**Action**: {action.tool}\n**Input**: {action.tool_input[:150]}..."
            )

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Run when agent finishes"""
        self.is_thinking = False


def create_langchain_agent(
    openai_api_key: str = None,
    model_name: str = None,
    temperature: float = None,
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
    # Use provided values or defaults from settings
    api_key = openai_api_key or OPENAI_API_KEY
    model = model_name or DEFAULT_LLM_MODEL
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment")

    # Create the LLM
    llm_kwargs = {
        "model_name": model,
        "temperature": temp,
        "openai_api_key": api_key,
    }

    # Only add streaming if supported and requested
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
        # For LangChain 0.0.150, initialize the agent with the callbacks
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


def create_simple_chain(
    openai_api_key: str = None,
    model_name: str = None,
    temperature: float = None,
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
    # Use provided values or defaults from settings
    api_key = openai_api_key or OPENAI_API_KEY
    model = model_name or DEFAULT_LLM_MODEL
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment")

    # Create the LLM
    llm_kwargs = {
        "model_name": model,
        "temperature": temp,
        "openai_api_key": api_key,
    }

    # Only add streaming if supported
    if streaming:
        llm_kwargs["streaming"] = True

    # Create the LLM instance
    llm = ChatOpenAI(**llm_kwargs)

    # Prepare callbacks for chain initialization
    callbacks = None
    if callback_handler:
        callbacks = [callback_handler]

    # Create memory
    memory = ConversationBufferMemory(return_messages=True)

    # Create chain arguments
    chain_kwargs = {"llm": llm, "memory": memory, "verbose": True}

    # Add callbacks to chain initialization if they exist
    if callbacks:
        chain_kwargs["callbacks"] = callbacks

    # Add prompt template if provided
    if prompt_template:
        prompt = PromptTemplate(
            input_variables=["history", "input"], template=prompt_template
        )
        chain_kwargs["prompt"] = prompt

    # Create the chain
    chain = ConversationChain(**chain_kwargs)

    return chain 