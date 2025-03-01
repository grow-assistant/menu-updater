"""
Main integration module for the AI Menu Updater application.
Connects query paths with the LangChain agent and provides the main flow.
"""

import os
import json
import logging
import datetime
import re
from typing import Dict, List, Any, Optional, Tuple

# LangChain imports - make backward compatible
try:
    # Try newer LangChain versions - try multiple potential import paths
    try:
        from langchain_core.tools import BaseTool as Tool
    except ImportError:
        from langchain.tools import Tool
    
    # For AgentExecutor
    try:
        from langchain.agents import AgentExecutor
    except ImportError:
        from langchain.agents.agent import AgentExecutor
except Exception as e:
    # Last resort fallback
    from langchain.tools import BaseTool as Tool
    from langchain.agents import AgentExecutor
    logging.warning(f"Using fallback imports for LangChain: {str(e)}")

# Import local modules
from config.settings import OPENAI_API_KEY
from query_paths import get_query_path
from tools.tool_factory import create_tools_for_agent
from langchain_setup import create_langchain_agent, StreamlitCallbackHandler

# Configure logger
logger = logging.getLogger("ai_menu_updater")

# Try importing our new service modules if available
try:
    from app.services.prompt_service import prompt_service
    from app.services.query_service import query_service
    # Use service modules if available
    SERVICES_AVAILABLE = True
    logger.info("Using modular service architecture")
except ImportError:
    # Fall back to direct module imports if services aren't available
    import openai
    SERVICES_AVAILABLE = False
    logger.info("Using legacy direct module architecture")

def categorize_query(query: str, openai_client=None) -> Dict[str, Any]:
    """
    Categorize a user query to determine the appropriate path.
    
    Args:
        query: User query
        openai_client: OpenAI client (optional)
        
    Returns:
        Dictionary with categorization results including request_type and other parameters
    """
    # Use the query service if available, otherwise use direct implementation
    if SERVICES_AVAILABLE:
        return query_service.categorize_query(query, openai_client)
    
    # Legacy implementation (unchanged)
    logger.info(f"Categorizing query: {query}")
    
    if not query.strip():
        logger.warning("Empty query received, returning default categorization")
        return {"request_type": "unknown"}
    
    # Setup OpenAI client
    client = openai_client
    if client is None:
        import openai
        client = openai
        client.api_key = OPENAI_API_KEY
    
    try:
        # Import here to avoid circular imports
        from prompts.openai_categorization_prompt import create_query_categorization_prompt
        
        # Get the categorization prompt
        categorization_prompt = create_query_categorization_prompt(user_query=query)
        
        # Call OpenAI for categorization
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": categorization_prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        # Extract and parse the response
        result_content = response.choices[0].message.content
        
        # Extract JSON from response text
        pattern = r'```json\s*(.*?)\s*```'
        match = re.search(pattern, result_content, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            result = json.loads(json_str)
        else:
            # Try to load the entire response as JSON
            try:
                result = json.loads(result_content)
            except json.JSONDecodeError:
                logger.error("Could not parse JSON from categorization response")
                result = {"request_type": "unknown"}
        
        # Ensure all expected fields have default values
        # Default all potential fields that might not be included
        defaults = {
            "time_period": None,
            "item_name": None,
            "new_price": None,
            "start_date": None,
            "end_date": None
        }
        
        # Merge with defaults
        full_result = {**defaults, **result}
        logger.info(f"Categorization result: {result}")
        
        return full_result
        
    except Exception as e:
        logger.error(f"Error during query categorization: {str(e)}")
        # Return a basic response on error
        return {"request_type": "unknown"}

def integrate_with_existing_flow(
    user_query: str,
    tools: List[Tool] = None,
    callback_handler=None,
    context: Dict[str, Any] = None,
    location_id: int = 62
) -> Dict[str, Any]:
    """
    Integrate with existing query flow for order history and menu updates.
    
    This function first categorizes the user query, then either:
    1. Processes the query with the appropriate query path, or
    2. Delegates to LangChain for more complex queries
    
    Args:
        user_query: The user's query
        tools: LangChain tools to use
        callback_handler: StreamlitCallbackHandler for progress updates
        context: Context data for the query
        location_id: Location ID to filter data by
        
    Returns:
        Dict containing query results
    """
    logger.info(f"Received user query: '{user_query}'")
    
    # Initialize default context if not provided
    if context is None:
        context = {}
    
    # First, categorize the query to determine what to do with it
    query_category = categorize_query(user_query)
    
    # Get the request type
    request_type = query_category.get("request_type", "unknown")
    
    # Process the query with the appropriate path
    if request_type in ["order_history", "update_price", "disable_item", "enable_item", 
                       "query_menu", "query_performance", "query_ratings"]:
        
        # Process using specific query paths
        if SERVICES_AVAILABLE:
            # Use the query service
            result = query_service.process_query_with_path(
                user_query, 
                query_category,
                location_id
            )
        else:
            # Legacy approach - process with query path
            query_path_factory = get_query_path(request_type)
            if query_path_factory:
                query_path = query_path_factory(location_id=location_id)
                result = query_path.process(user_query, query_category)
            else:
                logger.warning(f"No query path found for type: {request_type}")
                result = {
                    "success": False,
                    "verbal_answer": "I'm not sure how to process that type of request.",
                    "text_answer": "Unknown query type",
                    "sql_query": ""
                }
        
        # If the query processing succeeded, return the result
        if result.get("success", False):
            # If we have a callback handler, provide progress updates
            if callback_handler:
                try:
                    callback_handler.on_text(result.get("verbal_answer", ""))
                except Exception as e:
                    logger.error(f"Error calling callback handler: {str(e)}")
            
            logger.info(f"Integration successful for query type: {request_type}")
            return result
    
    # If we reached here, we couldn't process with a specific path,
    # so delegate to LangChain for more general handling
    logger.info("No specific query path matched, delegating to LangChain")
    try:
        from langchain_setup import process_with_langchain
        
        return process_with_langchain(
            user_query, 
            tools=tools, 
            callback_handler=callback_handler,
            location_id=location_id
        )
    except Exception as e:
        logger.error(f"Error processing with LangChain: {str(e)}")
        return {
            "success": False,
            "verbal_answer": "Sorry, I encountered an error processing your request with LangChain.",
            "text_answer": f"Error: {str(e)}",
            "sql_query": ""
        } 