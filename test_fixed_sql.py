from services.orchestrator.orchestrator import OrchestratorService
from ai_agent.utils.config_loader import load_config
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load config and initialize orchestrator
    logger.info("Initializing orchestrator...")
    config = load_config()
    
    # Ensure we're using the real services
    if "services" not in config:
        config["services"] = {}
    
    # Configure to use real services
    config["services"]["execution"] = {
        "use_real_service": True
    }
    config["services"]["sql_generator"] = {
        "use_real_service": True
    }
    
    # Initialize the orchestrator with our config
    orchestrator = OrchestratorService(config)
    
    # First query - this query was previously working fine
    first_query = "How many orders were completed on 2/21/2025?"
    logger.info(f"Processing first query: {first_query}")
    
    # Creating a context
    context = {
        "use_real_services": True,
        "enable_verbal": False,
        "fast_mode": True
    }
    
    first_result = orchestrator.process_query(first_query, context=context)
    
    print("\n----- FIRST QUERY RESULTS -----")
    print(f"Query: {first_query}")
    print(f"Response: {first_result.get('response')}")
    
    # Print SQL results formatted for readability
    query_results = first_result.get('query_results')
    print(f"\nSQL Generated: {orchestrator.query_context.get('previous_sql')}")
    if query_results:
        print("\nSQL Results:")
        print(json.dumps(query_results, indent=2))
    
    # Second query - should work now with our fixes
    second_query = "How many orders did each customer place in that time period?"
    logger.info(f"Processing follow-up query: {second_query}")
    
    # Update context to include session history for better follow-up handling
    context["session_history"] = [{
        "query": first_query,
        "category": first_result.get("category"),
        "response": first_result.get("response")
    }]
    
    # Set the is_followup flag explicitly
    context["is_followup"] = True
    
    second_result = orchestrator.process_query(second_query, context=context)
    
    print("\n----- SECOND QUERY RESULTS -----")
    print(f"Query: {second_query}")
    print(f"Response: {second_result.get('response')}")
    
    # Print the SQL that was generated for the second query
    print(f"\nSQL Generated: {orchestrator.query_context.get('previous_sql')}")
    
    # Print SQL results formatted for readability
    query_results = second_result.get('query_results')
    if query_results:
        print("\nSQL Results:")
        print(json.dumps(query_results, indent=2))
    else:
        print("\nNo results returned from SQL query.")

if __name__ == "__main__":
    main() 