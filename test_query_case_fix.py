from services.orchestrator.orchestrator import OrchestratorService
from ai_agent.utils.config_loader import load_config
import logging
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_test_scenario(scenario_file):
    """Load test scenario from JSON file"""
    scenario_path = os.path.join('ai_agent', 'test_scenarios', scenario_file)
    logger.info(f"Loading test scenario from {scenario_path}")
    with open(scenario_path, 'r') as f:
        return json.load(f)

# Monkey patch the OpenAI create method to force lowercase model names
# This is a hack to work around the case sensitivity issue
try:
    import openai
    original_create = openai.chat.completions.create
    
    def patched_create(*args, **kwargs):
        if 'model' in kwargs and isinstance(kwargs['model'], str):
            # Convert model name to lowercase
            original_model = kwargs['model']
            kwargs['model'] = kwargs['model'].lower()
            logger.info(f"MODEL FIX: Changed model name from '{original_model}' to '{kwargs['model']}'")
        return original_create(*args, **kwargs)
    
    # Apply the monkey patch
    openai.chat.completions.create = patched_create
    logger.info("Applied monkey patch for OpenAI model name case sensitivity")
except Exception as e:
    logger.warning(f"Could not apply OpenAI monkey patch: {str(e)}")

def main():
    # Load test scenario
    scenario = load_test_scenario('followup_order_details.json')
    logger.info(f"Running test scenario: {scenario['name']}")
    
    # Load config and initialize orchestrator
    logger.info("Initializing orchestrator...")
    config = load_config()
    
    # Ensure we're using the real services for SQL execution and generation
    if "services" not in config:
        config["services"] = {}
    
    # Configure to use real services
    config["services"]["execution"] = {
        "use_real_service": True
    }
    config["services"]["sql_generator"] = {
        "use_real_service": True
    }
    
    # Enable SQL validation service
    config["services"]["validation"] = {
        "sql_validation": {
            "enabled": True,
            "match_threshold": 90,
            "strict_mode": True
        }
    }
    
    # Fix: Explicitly set the model name with correct format (lowercase)
    if "response" not in config["services"]:
        config["services"]["response"] = {}
    
    # Using gpt-3.5-turbo as a fallback that's more likely to work
    config["services"]["response"]["model"] = "gpt-3.5-turbo"
    logger.info(f"Using OpenAI model: {config['services']['response']['model']}")
    
    # Initialize the orchestrator with our config
    orchestrator = OrchestratorService(config)
    
    # Get test steps from scenario
    test_steps = scenario['test_steps']
    
    # First query - from test step 1
    first_query = test_steps[0]['input']
    logger.info(f"Processing first query: {first_query}")
    
    # Creating a context that ensures this runs against actual database
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
    
    # Store time period from first query for debugging
    time_period = orchestrator.query_context.get("time_period_clause")
    print(f"\nDetected Time Period: {time_period}")
    
    # Second query - from test step 2
    second_query = test_steps[1]['input']
    logger.info(f"Processing follow-up query: {second_query}")
    
    # Update context to include session history for better follow-up handling
    # Only provide session history, let the services figure out the context
    context["session_history"] = [{
        "query": first_query,
        "category": first_result.get("category"),
        "response": first_result.get("response")
    }]
    
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
    
    # Get verification requirements from the test scenario
    verification_checks = scenario.get('verification_checks', {})
    expected_count = verification_checks.get('completed_orders_count', 0)
    expected_customer = verification_checks.get('should_include_customer', '')
    
    # Verify expected customer is in the results
    found_customer = False
    if query_results:
        for result in query_results:
            if result.get("customer_name") == expected_customer or result.get("customer") == expected_customer:
                found_customer = True
                break
    
    # Analysis
    print("\n----- ANALYSIS -----")
    print("First Query Performance:")
    print(f"Execution time: {first_result.get('execution_time', 0):.2f} seconds")
    
    print("\nSecond Query Performance:")
    print(f"Execution time: {second_result.get('execution_time', 0):.2f} seconds")
    
    print("\nVerification:")
    print(f"Found {expected_count} completed orders: {'Yes' if len(query_results or []) == expected_count else 'No, found ' + str(len(query_results or []))}")
    print(f"Found {expected_customer}: {'Yes' if found_customer else 'No'}")

if __name__ == "__main__":
    main() 