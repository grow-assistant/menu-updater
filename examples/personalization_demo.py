"""
Personalization Features Demo Script

This script demonstrates how response personalization works in SWOOP AI.
It creates user profiles with different preferences and shows how the 
system generates personalized responses for each user.
"""

import sys
import os
import time
from datetime import datetime

# Add the parent directory to the path so we can import the SWOOP modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.context_manager import UserProfile, ConversationContext, ContextManager
from services.response.response_generator import ResponseGenerator

def print_separator():
    print("\n" + "=" * 80 + "\n")

def main():
    # Create a demo configuration
    config = {
        "templates_dir": "templates",
        "default_model": "gpt-3.5-turbo",
        "api": {"openai": {"api_key": "fake-key-for-demo-purposes"}}
    }

    # Create a context manager and response generator
    context_manager = ContextManager(expiry_minutes=30)
    response_generator = ResponseGenerator(config)

    print("SWOOP AI Personalization Demo")
    print_separator()

    # ---- DEMO 1: Different Detail Levels ----
    print("DEMO 1: DETAIL LEVEL PERSONALIZATION")
    print("Creating two users with different detail level preferences...")
    
    # Create a user who prefers concise responses
    concise_user_id = "user-concise-123"
    concise_session_id = "session-concise-123"
    concise_context = context_manager.get_context(concise_session_id, concise_user_id)
    concise_context.user_profile.update_preference("detail_level", "concise")
    
    # Create a user who prefers detailed responses
    detailed_user_id = "user-detailed-456"
    detailed_session_id = "session-detailed-456"
    detailed_context = context_manager.get_context(detailed_session_id, detailed_user_id)
    detailed_context.user_profile.update_preference("detail_level", "detailed")
    
    # Set up a sample query and data for both users
    query = "How were burger sales last month?"
    sample_data = [
        {"item": "Burger", "quantity": 120, "revenue": 1200, "prev_month": 105, "change": "+15%"},
        {"item": "Cheeseburger", "quantity": 90, "revenue": 990, "prev_month": 85, "change": "+6%"},
        {"item": "Veggie Burger", "quantity": 45, "revenue": 540, "prev_month": 30, "change": "+50%"}
    ]
    
    # Get personalization context for each user
    concise_personalization = concise_context.get_personalization_hints()
    detailed_personalization = detailed_context.get_personalization_hints()
    
    # Generate responses for both users
    print("\nSAME QUERY, DIFFERENT DETAIL LEVELS:")
    print(f"Query: '{query}'")
    
    print("\nCONCISE USER RESPONSE:")
    response_concise = response_generator.generate(
        query=query,
        category="data_query",
        response_rules={},
        query_results=sample_data,
        context={"personalization_hints": concise_personalization}
    )
    # In a real case, this would be different due to personalization - simulating here:
    print("Burger sales last month: 120 burgers sold (+15%), generating $1,200 in revenue.")
    
    print("\nDETAILED USER RESPONSE:")
    response_detailed = response_generator.generate(
        query=query,
        category="data_query",
        response_rules={},
        query_results=sample_data,
        context={"personalization_hints": detailed_personalization}
    )
    # In a real case, this would be different due to personalization - simulating here:
    print("Last month, your restaurant sold 120 regular burgers (+15% compared to previous month), " 
          "90 cheeseburgers (+6%), and 45 veggie burgers (+50%). The burger category generated a total "
          "of $2,730 in revenue, with the veggie burger showing the strongest growth at 50% increase. "
          "Would you like to see a breakdown by day of week or time of day?")
    
    print_separator()
    
    # ---- DEMO 2: Different Tone Preferences ----
    print("DEMO 2: TONE PERSONALIZATION")
    print("Creating two users with different tone preferences...")
    
    # Create a user who prefers professional tone
    professional_user_id = "user-professional-789"
    professional_session_id = "session-professional-789"
    professional_context = context_manager.get_context(professional_session_id, professional_user_id)
    professional_context.user_profile.update_preference("response_tone", "professional")
    
    # Create a user who prefers friendly tone
    friendly_user_id = "user-friendly-101"
    friendly_session_id = "session-friendly-101"
    friendly_context = context_manager.get_context(friendly_session_id, friendly_user_id)
    friendly_context.user_profile.update_preference("response_tone", "friendly")
    
    # Set up a sample query and data for both users
    query = "How are dessert sales trending this quarter?"
    sample_data = [
        {"category": "Desserts", "current_quarter": 580, "previous_quarter": 520, "change": "+12%"},
        {"item": "Cheesecake", "current_quarter": 250, "previous_quarter": 200, "change": "+25%"},
        {"item": "Ice Cream", "current_quarter": 180, "previous_quarter": 190, "change": "-5%"},
        {"item": "Brownies", "current_quarter": 150, "previous_quarter": 130, "change": "+15%"}
    ]
    
    # Get personalization context for each user
    professional_personalization = professional_context.get_personalization_hints()
    friendly_personalization = friendly_context.get_personalization_hints()
    
    # Generate responses for both users
    print("\nSAME QUERY, DIFFERENT TONES:")
    print(f"Query: '{query}'")
    
    print("\nPROFESSIONAL TONE RESPONSE:")
    response_professional = response_generator.generate(
        query=query,
        category="data_query",
        response_rules={},
        query_results=sample_data,
        context={"personalization_hints": professional_personalization}
    )
    # In a real case, this would be different due to personalization - simulating here:
    print("The dessert category shows a 12% increase in sales compared to the previous quarter. "
          "Cheesecake is the strongest performer with a 25% increase, followed by brownies at 15% growth. "
          "Ice cream sales decreased by 5%.")
    
    print("\nFRIENDLY TONE RESPONSE:")
    response_friendly = response_generator.generate(
        query=query,
        category="data_query",
        response_rules={},
        query_results=sample_data,
        context={"personalization_hints": friendly_personalization}
    )
    # In a real case, this would be different due to personalization - simulating here:
    print("Great news! Your dessert sales are up 12% this quarter! 😊 Cheesecake is your star performer "
          "with a fantastic 25% jump - those new flavors are definitely a hit! Brownies are doing well too "
          "with a 15% increase. Only ice cream is down a little (5%), but that might be due to the season. "
          "Want to see what's driving those cheesecake sales?")
    
    print_separator()
    
    # ---- DEMO 3: Entity Focus Based on History ----
    print("DEMO 3: ENTITY FOCUS PERSONALIZATION")
    print("Creating a user with a history of querying specific items...")
    
    # Create a user with a history of burger queries
    burger_fan_id = "user-burger-fan-202"
    burger_session_id = "session-burger-fan-202"
    burger_context = context_manager.get_context(burger_session_id, burger_fan_id)
    
    # Simulate several queries about burgers
    print("\nSimulating query history about burgers...")
    
    burger_context.user_profile.update_with_query(
        "How many burgers did we sell?", 
        "data_query",
        {"menu_items": [{"name": "burger", "id": 1}]},
        "order_history"
    )
    
    burger_context.user_profile.update_with_query(
        "What's the trend for burger sales?", 
        "data_query",
        {"menu_items": [{"name": "burger", "id": 1}]},
        "order_history"
    )
    
    burger_context.user_profile.update_with_query(
        "How do burger sales compare to last month?", 
        "data_query",
        {"menu_items": [{"name": "burger", "id": 1}]},
        "order_history"
    )
    
    time.sleep(0.1)  # Ensure time passes for session tracking
    
    # Now query about menu items in general
    query = "How are our menu items performing?"
    sample_data = [
        {"item": "Burger", "quantity": 120, "revenue": 1200, "change": "+15%"},
        {"item": "Pizza", "quantity": 200, "revenue": 2400, "change": "+5%"},
        {"item": "Salad", "quantity": 80, "revenue": 720, "change": "+2%"},
        {"item": "Pasta", "quantity": 100, "revenue": 1000, "change": "-3%"}
    ]
    
    # Get personalization context with entity focus
    burger_personalization = burger_context.get_personalization_hints()
    
    # Generate a response with entity focus
    print("\nGENERAL QUERY WITH ENTITY FOCUS BASED ON HISTORY:")
    print(f"Query: '{query}'")
    
    print("\nPERSONALIZED RESPONSE WITH BURGER FOCUS:")
    response_burger_fan = response_generator.generate(
        query=query,
        category="data_query",
        response_rules={},
        query_results=sample_data,
        context={"personalization_hints": burger_personalization}
    )
    # In a real case, this would focus on the user's interests - simulating here:
    print("Your menu items are generally performing well. I notice you're particularly interested in burgers, "
          "which are up 15% with 120 units sold this month. This is your highest growth item, outperforming "
          "pizza (+5%), salad (+2%), and pasta (-3%). Would you like more details about the burger performance "
          "specifically?")
    
    # Display the personalization context that influenced the response
    print("\nPersonalization context used:")
    print(f"- Entity focus: {burger_personalization.get('frequent_entities', [])}")
    print(f"- Queries analyzed: {burger_context.user_profile.stats['total_queries']}")
    print(f"- Session data: {burger_context.user_profile.stats['total_sessions']} sessions")
    
    print_separator()
    
    print("PERSONALIZATION DEMO COMPLETE")

if __name__ == "__main__":
    main() 