from prototype import demonstrate_complete_flow

# Test with a clear order history query to trigger Path 1
print("\n🔍 TESTING PATH 1: Enhanced Gemini prompt with full business context")
print("Running with order history query: 'How many orders did we complete yesterday?'")

# Execute the flow with an order history query
result = demonstrate_complete_flow("How many orders did we complete yesterday?")

# Check if Path 1 was used by examining the output
if result.get('success'):
    print("\n✅ TEST SUCCESSFUL!")
    
    # Extract information about which path was used
    sql_generation_data = result.get('steps', {}).get('sql_generation', {})
    
    # Print detailed results
    print("\nDETAILS:")
    print(f"- Status: {sql_generation_data.get('status', 'unknown')}")
    print(f"- SQL Query: {sql_generation_data.get('data', {}).get('sql_query', 'No SQL query found')[:100]}...")
    
    # Check if we got results
    execution_data = result.get('steps', {}).get('execution', {})
    execution_results = execution_data.get('data', {}).get('results', [])
    
    if execution_results:
        print(f"- Result: {execution_results[0]}")
    
    # Show the final answer
    print(f"- Answer: {result.get('summary', 'No summary found')}")
else:
    print("\n⚠️ TEST FAILED:", result.get('error', 'Unknown error')) 