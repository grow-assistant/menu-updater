"""Test operation pattern matching"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.operation_patterns import match_operation

def test_patterns():
    """Test all operation patterns"""
    test_queries = [
        # Single item price updates
        "update price for Cheeseburger to 9.99",
        "change price of French Fries to 4.50",
        "set price for Caesar Salad to 12.99",
        # Bulk price updates
        "update price for French Fries everywhere to 4.99",
        "change price of Side Salad everywhere to 3.99",
        # Option item price updates
        "update price for option Extra Cheese to 1.50",
        "change price of option Large Size to 2.00",
        
        # Time ranges
        "set time for Lunch Menu to 1100-1500",
        "update time for Breakfast to 0600-1100",
        "change hours for Dinner Menu to 1700-2200",
        
        # Enable/disable
        "disable French Fries",
        "enable Caesar Salad",
        "turn off Cheeseburger",
        "turn on Breakfast Menu",
        "activate Lunch Special",
        "deactivate Kids Menu",
        
        # Option copying
        "copy options from Classic Burger to Deluxe Burger",
        "duplicate options from Caesar Salad to Greek Salad",
        
        # Side item updates
        "update side items to French Fries, Sweet Potato Fries, Onion Rings",
        "change list of side items to Salad, Soup, Coleslaw",
        "set side items to Chips, Fruit Cup, Cottage Cheese",
        "add side items French Fries, Sweet Potato Fries, Onion Rings",
        "replace side items with Salad, Soup, Coleslaw"
    ]
    
    print("\nTesting Operation Patterns\n" + "="*50)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        if result := match_operation(query):
            print("✓ Matched Operation:")
            print(f"  Type: {result['type']}")
            print(f"  Operation: {result['operation']}")
            print(f"  Parameters: {result['params']}")
        else:
            print("✗ No match found")
    
    print("\nPattern Testing Complete")

if __name__ == "__main__":
    test_patterns()
