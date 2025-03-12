"""
General Question Rules

Contains rules specific to general restaurant-related queries.
"""

def get_rules():
    """Return rules specific to general questions."""
    return {
        "enable_follow_up": True,
        "enable_clarification": True,
        "provide_location_info": True,
        "provide_hours": True,
        "provide_contact_info": True,
        "use_conversational_tone": True
    }

def apply_rules(query, context):
    """Apply general question rules to the given query and context."""
    # This is a simple implementation that just returns the rules
    rules = get_rules()
    
    # Special handling for specific terms
    if "location" in query.lower() or "where" in query.lower() or "address" in query.lower():
        rules["focus_on_location"] = True
    
    if "open" in query.lower() or "close" in query.lower() or "hours" in query.lower():
        rules["focus_on_hours"] = True
    
    if "contact" in query.lower() or "phone" in query.lower() or "email" in query.lower():
        rules["focus_on_contact"] = True
    
    return rules 