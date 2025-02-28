"""
Test script to verify LangChain imports.
This script will try to import the same modules used in the main application.
"""

try:
    print("Importing LangChain modules (0.0.150 style)...")
    
    # Try importing the modules from langchain (0.0.150 style)
    from langchain.chains import ConversationChain
    from langchain.agents import AgentType, initialize_agent, Tool, AgentExecutor
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate
    from langchain.chat_models import ChatOpenAI
    from langchain.schema import SystemMessage, HumanMessage
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish, LLMResult
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    from langchain.chains.llm import LLMChain
    
    print("All 0.0.150 style imports successful!")
    
    # Print LangChain version
    import langchain
    print(f"LangChain version: {langchain.__version__}")
    
    print("\nTrying newer LangChain (0.1.0+) style imports...")
    
    try:
        # Try importing from langchain_community
        from langchain_community.agents import AgentType, initialize_agent, Tool
        print("langchain_community imports worked! This is unexpected for version 0.0.150")
    except ImportError as e:
        print(f"Expected import error for langchain_community: {str(e)}")
    
    try:
        # Try importing from langchain_core
        from langchain_core.memory import ConversationBufferMemory
        print("langchain_core imports worked! This is unexpected for version 0.0.150")
    except ImportError as e:
        print(f"Expected import error for langchain_core: {str(e)}")
    
    try:
        # Try importing from langchain_openai
        from langchain_openai import ChatOpenAI
        print("langchain_openai imports worked! This is unexpected for version 0.0.150")
    except ImportError as e:
        print(f"Expected import error for langchain_openai: {str(e)}")
    
except Exception as e:
    print(f"Error importing: {str(e)}")
    import traceback
    traceback.print_exc() 