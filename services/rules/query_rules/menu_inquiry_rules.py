"""
Menu Inquiry Rules

Contains rules specific to menu-related queries.
"""

def get_rules():
    """Return rules specific to menu inquiries."""
    return {
        "max_menu_items": 20,
        "include_prices": True,
        "include_descriptions": True,
        "enable_follow_up": True,
        "enable_clarification": True,
        "show_categories": True,
        "prioritize_popular_items": True
    }

def apply_rules(query, context):
    """Apply menu inquiry rules to the given query and context."""
    # This is a simple implementation that just returns the rules
    rules = get_rules()
    
    # Special handling for specific terms
    if "price" in query.lower() or "cost" in query.lower() or "how much" in query.lower():
        rules["focus_on_prices"] = True
    
    if "vegetarian" in query.lower() or "vegan" in query.lower():
        rules["dietary_filter"] = "vegetarian"
    
    return rules
