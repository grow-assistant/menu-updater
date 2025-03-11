"""
Follow-up query enhancement rules.

This module provides supplementary rules for handling follow-up queries,
which can be combined with rules from the original query category.
"""

import logging
from typing import Dict, Any, List
from services.rules.business_rules import DEFAULT_LOCATION_ID

logger = logging.getLogger(__name__)

def get_follow_up_rules() -> Dict[str, Any]:
    """
    Get supplementary rules for handling follow-up queries.
    
    These rules should be applied alongside the rules from the original query category.
    
    Returns:
        Dictionary of rules for follow-up queries
    """
    return {
        "maintain_time_period": "Maintain the same time period from the previous query unless explicitly changed",
        "maintain_filters": "Maintain filters from the previous query unless explicitly changed",
        "maintain_location": f"Always include location_id = {DEFAULT_LOCATION_ID} in queries",
        "orders_customer_id": "When joining orders to users, use orders.customer_id = users.id for customer information",
        "use_order_id": "When counting orders, use orders.id as the primary key",
        "schema_adherence": "Always use field names that match the database schema exactly"
    }

def enhance_rules_for_followup(original_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance the rules from the original query category with follow-up specific rules.
    
    Args:
        original_rules: Rules from the original query category
        
    Returns:
        Enhanced rules dictionary with follow-up specific rules added
    """
    followup_rules = get_follow_up_rules()
    
    # Create a copy of the original rules
    enhanced_rules = original_rules.copy() if original_rules else {}
    
    # Add follow-up specific rules
    for key, value in followup_rules.items():
        if key not in enhanced_rules:
            enhanced_rules[key] = value
    
    return enhanced_rules

def get_sql_examples() -> List[Dict[str, Any]]:
    """
    These examples are no longer needed as the system will now use 
    examples from the original query category.
    
    This function is kept for backward compatibility.
    
    Returns:
        Empty list as examples should come from the original category
    """
    logger.info("Follow-up examples are now obtained from the original query category")
    return [] 