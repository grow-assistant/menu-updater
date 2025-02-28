"""
Example showing how to integrate LangChain with the existing demonstrate_complete_flow function.
This is a minimal example showing the concept - full integration would require more changes.
"""

import os
from typing import Dict, Any, Optional, List

# Import from the existing codebase
from integrate_app import (
    demonstrate_complete_flow,
    MockSessionState,
    get_clients,
    load_application_context,
)

# Import the LangChain integration
from utils.langchain_integration import (
    create_langchain_agent,
    create_sql_database_tool,
    create_menu_update_tool,
    integrate_with_existing_flow,
)

# Import LangChain components
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain.agents import Tool


def execute_sql_query(query: str) -> Dict[str, Any]:
    """Wrapper around the existing SQL execution functions"""
    from app import execute_menu_query, adjust_query_timezone

    # For this example, we'll use location ID 62
    location_id = 62

    # Adjust the query for timezone
    adjusted_query = adjust_query_timezone(query, location_id)

    # Execute the query
    result = execute_menu_query(adjusted_query)

    return result


def create_tools() -> List[Tool]:
    """Create tools for the LangChain agent"""
    # SQL database tool
    sql_tool = create_sql_database_tool(execute_query_func=execute_sql_query)

    # Menu update tool
    def execute_menu_update(update_spec):
        # Parse the update specification
        import json

        if isinstance(update_spec, str):
            spec = json.loads(update_spec)
        else:
            spec = update_spec

        item_name = spec.get("item_name")
        new_price = spec.get("new_price")
        disabled = spec.get("disabled")

        # For this example, we'll use location ID 62
        location_id = 62

        if new_price is not None:
            # Update price query
            query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        elif disabled is not None:
            # Enable/disable query
            query = f"UPDATE items SET disabled = {str(disabled).lower()} WHERE name ILIKE '%{item_name}%' AND location_id = {location_id} RETURNING *"
        else:
            return {"success": False, "error": "Invalid update specification"}

        return execute_sql_query(query)

    menu_tool = create_menu_update_tool(execute_update_func=execute_menu_update)

    return [sql_tool, menu_tool]


def demonstrate_flow_with_langchain(
    test_query: str = None,
    previous_context: Optional[Dict[str, Any]] = None,
    use_langchain: bool = True,
) -> Dict[str, Any]:
    """
    Demonstrates how to integrate LangChain with the existing flow.

    Args:
        test_query: User query to process
        previous_context: Context from previous queries
        use_langchain: Whether to use LangChain or the original flow

    Returns:
        dict: Results from processing the query
    """
    if not test_query:
        test_query = "How many orders were completed yesterday?"

    if not use_langchain:
        # Use the original flow
        print("Using original flow...")
        return demonstrate_complete_flow(
            test_query=test_query, previous_context=previous_context
        )

    # Use LangChain flow
    print("Using LangChain flow...")

    # Create a mock session state
    mock_session = MockSessionState()
    mock_session.selected_location_id = 62  # Default to Idle Hour

    # Create tools for the agent
    tools = create_tools()

    # Create or get memory
    memory = None
    if previous_context and "agent_memory" in previous_context:
        memory = previous_context["agent_memory"]

    if memory is None:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        # Add conversation history if available
        if previous_context and "conversation_history" in previous_context:
            for exchange in previous_context["conversation_history"]:
                user_msg, ai_msg = exchange
                memory.chat_memory.add_message(HumanMessage(content=user_msg))
                if ai_msg:
                    memory.chat_memory.add_message(AIMessage(content=ai_msg))

    # Create the agent
    agent = create_langchain_agent(
        tools=tools,
        memory=memory,
        verbose=True,
        model_name="gpt-4-turbo",
        temperature=0.3,
        streaming=True,
    )

    # Create context
    context = previous_context or {}
    if "context" not in context:
        context["context"] = {}

    # Load application context
    app_context = load_application_context()
    if app_context:
        context["business_rules"] = app_context.get("business_rules", "")
        context["database_schema"] = app_context.get("database_schema", "")

    # Process the query with LangChain
    result = integrate_with_existing_flow(
        query=test_query, tools=tools, context=context, agent=agent
    )

    # Store the memory for next time
    result["agent_memory"] = memory

    return result


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the demo with LangChain integration"
    )
    parser.add_argument("--query", type=str, help="Query to process", default=None)
    parser.add_argument(
        "--original", action="store_true", help="Use original flow instead of LangChain"
    )
    args = parser.parse_args()

    # Process the query
    result = demonstrate_flow_with_langchain(
        test_query=args.query, use_langchain=not args.original
    )

    # Print the result
    print("\n" + "=" * 50)
    print("QUERY RESULT:")
    print("=" * 50)
    print(f"Success: {result.get('success', False)}")
    print(f"Summary: {result.get('summary', 'No summary available')}")
    print("=" * 50)
