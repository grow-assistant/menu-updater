"""
Swoop AI Conversational Query Flow - Client Example

This script demonstrates how to use the Swoop AI Conversational Query Flow system
to process natural language queries.
"""
import argparse
import logging
import os
import uuid
from typing import Dict, Any, Optional

# Import the orchestrator
from services.orchestrator.query_orchestrator import QueryOrchestrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SwoopConversationClient:
    """
    Simple client for interacting with the Swoop Conversational Query Flow system.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the client with an orchestrator.
        
        Args:
            model_path: Optional path to the classification model
        """
        self.orchestrator = QueryOrchestrator(model_path)
        self.session_id = str(uuid.uuid4())
        logger.info(f"Initialized client with session ID: {self.session_id}")
    
    def process_query(self, query_text: str) -> Dict[str, Any]:
        """
        Process a query using the orchestrator.
        
        Args:
            query_text: The raw query text
            
        Returns:
            The orchestrator's response
        """
        response = self.orchestrator.process_query(query_text, self.session_id)
        return response
    
    def run_interactive_session(self):
        """
        Run an interactive console session.
        """
        print("\nWelcome to Swoop AI Conversational Query Flow!")
        print("----------------------------------------------")
        print("You can ask questions about your order history, menu items, or request")
        print("actions like updating prices or enabling/disabling items.")
        print("\nType 'exit' or 'quit' to end the session.\n")
        
        while True:
            query = input("\nYou: ")
            
            if query.lower() in ['exit', 'quit']:
                print("\nThank you for using Swoop AI. Goodbye!")
                break
            
            try:
                response_data = self.process_query(query)
                response_text = response_data.get('response', '')
                response_type = response_data.get('response_type', 'answer')
                
                # Format the response based on type
                if response_type == 'error':
                    print(f"\nError: {response_text}")
                else:
                    print(f"\nSwoop AI: {response_text}")
                    
                    # If there are actions being performed, show them
                    actions = response_data.get('actions', [])
                    if actions:
                        print("\nActions performed:")
                        for i, action in enumerate(actions, 1):
                            action_type = action.get('type', '')
                            field = action.get('field', '')
                            entity = action.get('entity_name', '')
                            value = action.get('value', '')
                            print(f"  {i}. {action_type.capitalize()} {field} of {entity} to {value}")
                
            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                print("\nSorry, an error occurred while processing your request.")


def main():
    """Main entry point for the client script."""
    parser = argparse.ArgumentParser(description='Swoop AI Conversational Query Flow Client')
    parser.add_argument('--model', help='Path to the classification model')
    args = parser.parse_args()
    
    # Create and run the client
    client = SwoopConversationClient(args.model)
    client.run_interactive_session()


if __name__ == '__main__':
    main() 