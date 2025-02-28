"""
Test script to verify the LangChain agent with tools works correctly.
"""

import os
from dotenv import load_dotenv
from langchain.tools import BaseTool
from utils.langchain_integration import create_langchain_agent

# Load environment variables
load_dotenv()

def main():
    # Check if OPENAI_API_KEY is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in your .env file or environment.")
        return
    
    try:
        print("Creating example tools...")
        
        # Create a simple calculator tool
        class CalculatorTool(BaseTool):
            name = "Calculator"
            description = "Useful for performing mathematical calculations."
            
            def _run(self, query: str) -> str:
                try:
                    result = eval(query)
                    return f"Result: {result}"
                except Exception as e:
                    return f"Error: {str(e)}"
            
            def _arun(self, query: str):
                # This tool doesn't support async
                raise NotImplementedError("This tool does not support async")
        
        # Create tools list
        tools = [CalculatorTool()]
        
        print("Creating a LangChain agent with tools...")
        agent = create_langchain_agent(
            model_name="gpt-3.5-turbo",  # Using a cheaper model for testing
            temperature=0.7,
            streaming=False,  # Disable streaming for simpler testing
            tools=tools,
            verbose=True
        )
        
        # Test the agent with a simple query
        print("\nSending a test query to the agent...")
        response = agent.run("What is 123 * 456?")
        print("\nAgent response:")
        print(response)
        print("\nAgent test successful!")
        
    except Exception as e:
        print(f"\nError during agent test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 