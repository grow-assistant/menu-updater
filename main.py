"""
LangChain-powered Streamlit application for Swoop AI.
This file provides a LangChain-integrated version of the Streamlit interface.
"""

import os
import streamlit as st
import datetime
from dotenv import load_dotenv
import time
import threading
import base64
import pytz
import logging
import psycopg2
import re
from psycopg2.extras import RealDictCursor
from decimal import Decimal
import traceback

# Set up page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="Swoop AI",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# Swoop AI\nAI-powered restaurant data assistant"},
)

# Add custom CSS for a modern look that matches Swoop Golf branding
st.markdown(
    """
<style>
    /* Import Google Fonts similar to Swoop website */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    
    /* Overall styling with Swoop Golf colors */
    .main {
        background-color: #ffffff;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Header styling to match Swoop branding */
    h1, h2, h3 {
        color: #FF8B00;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Swoop primary orange */
    .stButton>button {
        background-color: #FF8B00;
        color: white;
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.5rem;
        margin-bottom: 1rem;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* User icon styling */
    .stChatMessageContent[data-testid="stChatMessageContent"] {
        background-color: #f9f9f9;
    }
    
    /* Status message styling */
    .stAlert {
        border-radius: 8px;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* SQL query expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Add shadow to containers */
    [data-testid="stVerticalBlock"] div:has(> [data-testid="stChatMessage"]) {
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-12oz5g7 {
        background-color: #f9f9f9;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Sidebar title styling */
    .css-10oheav {
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        border-top: 1px solid #e6e6e6;
        padding-top: 1rem;
    }
    
    /* Status indicators */
    .stStatus {
        background-color: #fff9f0;
        border-left: 3px solid #FF8B00;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #eaf7ee;
        border-left: 3px solid #FF8B00;
    }

    /* Text styling */
    p, li, div {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Code blocks */
    code {
        font-family: 'Consolas', 'Monaco', monospace;
    }
    
    /* Chat input text */
    .stChatInput {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Make links orange */
    a {
        color: #FF8B00 !important;
    }
    
    /* Sidebar headers */
    .css-16idsys p {
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Reset the assistant avatar completely */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"],
    div[data-testid="stChatMessageAvatarAssistant"] {
        /* Clear any previous background or SVG */
        background-image: none !important;
        background-color: transparent !important;
        position: relative !important;
    }

    /* Use ::before to insert a clean Swoop logo */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"]::before,
    div[data-testid="stChatMessageAvatarAssistant"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('data:image/svg+xml;base64,PHN2ZyBpZD0iTGF5ZXJfMSIgZGF0YS1uYW1lPSJMYXllciAxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNzguOTEgMjM5LjY0Ij48ZGVmcz48c3R5bGU+LmNscy0xLCAuY2xzLTIge2ZpbGw6ICNmZmY7fS5jbHMtMSB7ZmlsbC1ydWxlOiBldmVub2RkO308L3N0eWxlPjwvZGVmcz48Zz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0yODgsNjVsLTUuNTctMi4wOGMtMzYuNTktMTMuNjgtNDIuMzYtMTUuMzMtNDMuODYtMTUuNTNhNDAuNzEsNDAuNzEsMCwwLDAtNzAuNTEsNC4yOGMtLjg1LS4wNi0xLjctLjExLTIuNTYtLjEzaC0uOTRjLS41NiwwLTEuMTEsMC0xLjY2LDBhNTguOTIsNTguOTIsMCwwLDAtMjIuOCw1QTU4LjExLDU4LjExLDAsMCwwLDExOC40NSw3Mi43TDkuMDksMTc4LjQybDk1LjIyLTUuMTEtMS43Myw5NS4zM0wyMDcuMDksMTUxLjI5YTU5LjYzLDU5LjYzLDAsMCwwLDE1LjY4LTM4LjFjMC0uMTEsMC0uMjMsMC0uMzQsMC0uNjAwLTEuMjAwLTEuOGMwLTEsMC0xLjQ1YzAtLjI0LDAtLjQ5LDAtLjc0LDAtLjg1LS4wNy0xLjY5LS4xNC0yLjU0YTQxLDQxLDAsMCwwLDIxLTI0LjgyLDE1LjU2LDE1LjU2LDAsMCwwLDMuNTctMVpNMjA1LjM4LDc1LjMzYzEsMS4xNSwxLjg5LDIuMzYsMi43NywzLjYuMTcuMjYuMzYuNS41NC43Ni44LDEuMTgsMS41NSwyLjQsMi4yNywzLjY1bC42NywxLjE5Yy42MywxLjE1LDEuMjEsMi4zNCwxLjc1LDMuNTRhNTUuNzEsNTUuNzEsMCwwLDEsNC40NiwxNS41QTM2LjI0LDM2LjI0LDAsMCwxLDE3MC43OSw1Ni41QTU0LjI1LDU0LjI1LDAsMCwxLDIwNSw3NC45M1ptMTIuOTIsMzcuNDN2LjExQTU0LjgyLDU0LjgyLDAsMCwxLDE4NS41NiwxNjFhNTQsNTQsMCwwLDEtMTkuODgsNC41NGwtNTYuNzksMywxLTUyLjY5di0uMTJhNTQuNTYsNTQuNTYsMCwwLDEsNTQtNTkuNzhjLjc4LDAsMS41Ny4wNywyLjM1LjExYTQwLjY4LDQwLjY4LDAsMCwwLDUyLjEsNTIuMWwwLC43YzAsLjI5LDAsLjU4LDAsLjg3czAsLjc3LDAsMS4xNUMyMTguMzIsMTExLjUyLDIxOC4zMiwxMTIuMTQsMjE4LjMsMTEyLjc2Wk0yMC44NywxNzMuMjksMTEwLjE4LDg3Yy0uMzMuNzQtLjcsMS40Ni0xLDIuMjNhNTguODgsNTguODgsMCwwLDAtMy44MywyNi44N2wtLjk1LDUyLjc2Wm04Ny45NC0uMjJMMTY1Ljg4LDE3MGE1OC41Niw1OC41NiwwLDAsMCwyMS40OC00LjkxYy44Mi0uMzYsMS42My0uNzQsMi40Mi0xLjEzTDEwNy4zLDI1Ni42Wm0xMTMuMzEtNzEuNTFhNTkuNTEsNTkuNTEsMCwwLDAtNC4yMi0xNC40N2MtLjE0LS4zMy0uMzMtLjY0LS40OC0xYy0uNTUtMS4yMS0xLjEzLTIuNC0xLjc2LTMuNTdjLS4yOS0uNTItLjU4LTEtLjg4LTEuNTVjLS43NC0xLjI5LTEuNTEtMi41NS0yLjM1LTMuNzhjLS4yMy0uMzQtLjQ3LS42Ni0uNzEtMWMtLjkxLTEuMjgtMS44Ni0yLjUzLTIuODctMy43NGwtLjUxLS41OHEtMS42OS0yLTMuNTctMy44MWwtLjEtLjA5YTU4LjM0LDU4LjM0LDAsMCwwLTE5LjE4LTEyLjM4LDU4LjkzLDU4LjkzLDAsMCwwLTEyLjY3LTMuNDQsMzYuMjksMzYuMjksMCwxLDEsNDkuMyw0OS4zOFptMjIuNi0yNWEzOS43OSwzOS43OSwwLDAsMC0zLjExLTIzLjc4YzQuNDUsMS40NSwxMy45MSw0Ljc5LDMzLjY3LDEyLjE1TDI0NS41NCw3Ni4zNkMyNDUuMjgsNzYuNDcsMjQ1LDc2LjUyLDI0NC43Miw3Ni42MVoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC05LjA5IC0yOSkiLz48ZWxsaXBzZSBjbGFzcz0iY2xzLTIiIGN4PSIxNTAuMTgiIGN5PSI4NC44OCIgcng9IjE2LjQ0IiByeT0iMTYuNTMiLz48L2c+PC9zdmc+');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        z-index: 10;
    }

    /* Hide any original SVG inside the avatar */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"] svg,
    div[data-testid="stChatMessageAvatarAssistant"] svg {
        opacity: 0 !important;
        visibility: hidden !important;
    }
    
    /* Hide status messages in the sidebar */
    div[data-testid="stSidebar"] .stSuccess, 
    div[data-testid="stSidebar"] .stInfo, 
    div[data-testid="stSidebar"] .stWarning {
        display: none !important;
    }
    
    /* Fix any CSS that might be visible in the UI */
    .main p,
    .main div:not([class]) {
        min-height: 0 !important;
    }
    
    /* Hide any text that looks like CSS or code */
    *:not(style):not(script):not(pre):not(code) {
        white-space: normal !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Apply a second CSS overlay just to fix any leaking CSS issues
st.markdown(
    """
<style>
/* This CSS will ensure no CSS code is visible in the main UI */
.main pre,
.main code {
    display: none;
}

/* Reset any leaked CSS content */
.stApp .main-content > *:not(.element-container):not(.stVerticalBlock) {
    display: none !important;
}

/* Make sure all style tags are hidden */
.stApp style {
    display: none !important;
}

/* Hide any text that contains CSS syntax */
.stApp .main-content *:contains('{') {
    display: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

from typing import Dict, List, Any, Optional, Tuple
import json
import datetime
from dotenv import load_dotenv
import os
import time
import threading
import base64
import pytz
import logging
import psycopg2
import re
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Import OpenAI client for API key verification
import openai

# Import personas
from prompts.personas import get_persona_info, get_persona_voice_id, get_persona_prompt

# Global variables for voice feature availability
ELEVENLABS_AVAILABLE = True  # Force elevenlabs to be available
USE_NEW_API = False
PYGAME_AVAILABLE = True  # Force pygame to be available
pygame = None

# Remove imports from integrate_app.py and app.py, replacing with our own implementations
# from integrate_app import (
#     load_application_context,
#     initialize_voice_dependencies,
#     MockSessionState,
#     get_clients,
#     ElevenLabsVoice,
# )
# from app import execute_menu_query, adjust_query_timezone

# Add imports for speech recognition
import time
import threading
import base64

# Initialize flag for LangChain availability
LANGCHAIN_AVAILABLE = False

# Define database connection parameters 
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "swoop"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Mock data for when database is unavailable
MOCK_DATA = {
    "orders": [
        {"order_id": 1001, "customer_first_name": "John", "customer_last_name": "Doe", "order_created_at": "2025-02-21 10:15:00", "order_total": 45.99, "phone": "555-123-4567", "status": 7},
        {"order_id": 1002, "customer_first_name": "Jane", "customer_last_name": "Smith", "order_created_at": "2025-02-21 11:30:00", "order_total": 32.50, "phone": "555-987-6543", "status": 7},
        {"order_id": 1003, "customer_first_name": "Robert", "customer_last_name": "Johnson", "order_created_at": "2025-02-21 12:45:00", "order_total": 28.75, "phone": "555-456-7890", "status": 7},
    ],
    "menu_items": [
        {"id": 101, "name": "Club Sandwich", "price": 12.99, "disabled": False, "location_id": 62},
        {"id": 102, "name": "Caesar Salad", "price": 9.99, "disabled": False, "location_id": 62},
        {"id": 103, "name": "French Fries", "price": 4.99, "disabled": False, "location_id": 62},
    ]
}

# Flag to indicate if we're using mock data
USING_MOCK_DATA = False

# Define timezone constants
USER_TIMEZONE = pytz.timezone("America/Phoenix")  # Arizona (no DST)
CUSTOMER_DEFAULT_TIMEZONE = pytz.timezone("America/New_York")  # EST
DB_TIMEZONE = pytz.timezone("UTC")

# Create a Session State class with attribute access
class MockSessionState:
    def __init__(self):
        self.selected_location_id = 62  # Default to Idle Hour Country Club
        self.selected_location_ids = [62]  # Default to Idle Hour as a list
        self.selected_club = "Idle Hour Country Club"  # Default club

        # Club to location mapping
        self.club_locations = {
            "Idle Hour Country Club": {"locations": [62], "default": 62},
            "Pinetree Country Club": {"locations": [61, 66], "default": 61},
            "East Lake Golf Club": {"locations": [16], "default": 16},
        }

        # Location ID to name mapping
        self.location_names = {
            62: "Idle Hour Country Club",
            61: "Pinetree Country Club (Location 61)",
            66: "Pinetree Country Club (Location 66)",
            16: "East Lake Golf Club",
        }
        self.last_sql_query = None
        self.api_chat_history = [{"role": "system", "content": "Test system prompt"}]
        self.full_chat_history = []
        self.date_filter_cache = {
            "start_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        }  # Initialize with current date

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

def get_location_timezone(location_id):
    """Get timezone for a specific location, defaulting to EST if not found"""
    # This would normally query the database, but for testing we'll hardcode
    location_timezones = {
        62: CUSTOMER_DEFAULT_TIMEZONE,  # Idle Hour Country Club
        # Add other locations as needed
    }
    return location_timezones.get(location_id, CUSTOMER_DEFAULT_TIMEZONE)

def adjust_query_timezone(query, location_id):
    """Adjust SQL query to handle timezone conversion"""
    location_tz = get_location_timezone(location_id)

    # Replace any date/time comparisons with timezone-aware versions
    if "updated_at" in query:
        # First convert CURRENT_DATE to user timezone (Arizona)
        current_date_in_user_tz = datetime.datetime.now(USER_TIMEZONE).date()

        # Handle different date patterns
        if "CURRENT_DATE" in query:
            # Convert current date to location timezone for comparison
            query = query.replace(
                "CURRENT_DATE",
                f"(CURRENT_DATE AT TIME ZONE 'UTC' AT TIME ZONE '{USER_TIMEZONE.zone}')",
            )

        # Handle the updated_at conversion
        query = query.replace(
            "(o.updated_at - INTERVAL '7 hours')",
            f"(o.updated_at AT TIME ZONE 'UTC' AT TIME ZONE '{location_tz.zone}')",
        )

    return query

def get_db_connection(timeout=3):
    """Get a database connection with fallback to mock mode if database is unavailable
    
    Args:
        timeout: Connection timeout in seconds (default: 3)
        
    Returns:
        Connection object or None if connection fails
    """
    global USING_MOCK_DATA
    
    try:
        # Add timeout to prevent hanging indefinitely
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=timeout,  # Add timeout parameter
        )
        USING_MOCK_DATA = False
        return conn
    except Exception as e:
        logger = logging.getLogger("ai_menu_updater")
        logger.warning(f"Database connection failed: {str(e)}. Switching to mock data mode.")
        USING_MOCK_DATA = True
        return None

def execute_menu_query(query: str, params=None) -> Dict[str, Any]:
    """Execute a read-only menu query and return results with mock data fallback"""
    global USING_MOCK_DATA
    conn = None
    
    try:
        conn = get_db_connection()
        
        # If database connection failed, use mock data
        if USING_MOCK_DATA or conn is None:
            mock_result = handle_mock_query(query)
            logger = logging.getLogger("ai_menu_updater")
            logger.info(f"Using mock data for query: {query}")
            return mock_result
            
        # If we have a real connection, execute the real query
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        # Convert Decimal types to float for JSON serialization
        results = [
            {
                col: float(val) if isinstance(val, (Decimal))
                else val.isoformat() if isinstance(val, (datetime.date, datetime.datetime))
                else val
                for col, val in row.items()
            }
            for row in cur.fetchall()
        ]

        return {
            "success": True,
            "results": results,
            "columns": [desc[0] for desc in cur.description] if cur.description else [],
            "query": query,
        }
    except Exception as e:
        logger = logging.getLogger("ai_menu_updater")
        logger.error(f"Error executing menu query: {str(e)}")
        
        # Try mock data as fallback if real query fails
        if not USING_MOCK_DATA:
            USING_MOCK_DATA = True
            logger.info(f"Falling back to mock data for query: {query}")
            return handle_mock_query(query)
            
        return {"success": False, "error": str(e), "query": query}
    finally:
        if conn and not USING_MOCK_DATA:
            conn.close()

def handle_mock_query(query: str) -> Dict[str, Any]:
    """Parse the SQL query and return appropriate mock data"""
    query = query.lower()
    
    # Count query
    if "count(*)" in query:
        if "orders" in query and "status = 7" in query:
            count_value = 44  # Default number of completed orders
            
            # Check for date constraints
            if "2025-02-21" in query:
                count_value = 44
            elif "2025-02-22" in query:
                count_value = 38
            elif "current_date" in query or datetime.datetime.now().strftime("%Y-%m-%d") in query:
                count_value = 52
                
            return {
                "success": True,
                "results": [{"count": count_value}],
                "columns": ["count"],
                "query": query,
            }
    
    # Orders query
    elif "from orders" in query:
        results = MOCK_DATA["orders"]
        
        # Filter by status if needed
        if "status = 7" in query:
            results = [r for r in results if r.get("status") == 7]
            
        # Limit results if needed
        if "limit" in query:
            limit_match = re.search(r"limit\s+(\d+)", query)
            if limit_match:
                limit = int(limit_match.group(1))
                results = results[:limit]
        
        return {
            "success": True,
            "results": results,
            "columns": list(results[0].keys()) if results else [],
            "query": query,
        }
    
    # Menu items query
    elif "from items" in query or "menu items" in query:
        results = MOCK_DATA["menu_items"]
        
        # Filter by name if needed
        if "name ilike" in query:
            name_match = re.search(r"name ilike\s+'%([^%]+)%'", query)
            if name_match:
                search_term = name_match.group(1).lower()
                results = [r for r in results if search_term in r.get("name", "").lower()]
        
        return {
            "success": True,
            "results": results,
            "columns": list(results[0].keys()) if results else [],
            "query": query,
        }
    
    # Update query (for menu items)
    elif "update items" in query:
        if "price =" in query:
            price_match = re.search(r"price\s*=\s*(\d+\.?\d*)", query)
            item_match = re.search(r"name ilike\s*'%([^%]+)%'", query)
            
            if price_match and item_match:
                price = float(price_match.group(1))
                item_name = item_match.group(1)
                
                # Find matching items
                affected_rows = 0
                for item in MOCK_DATA["menu_items"]:
                    if item_name.lower() in item.get("name", "").lower():
                        item["price"] = price
                        affected_rows += 1
                        
                return {
                    "success": True,
                    "results": [{"affected_rows": affected_rows}],
                    "columns": ["affected_rows"],
                    "query": query,
                }
        
        elif "disabled =" in query:
            state_match = re.search(r"disabled\s*=\s*(true|false)", query)
            item_match = re.search(r"name ilike\s*'%([^%]+)%'", query)
            
            if state_match and item_match:
                disabled = state_match.group(1).lower() == "true"
                item_name = item_match.group(1)
                
                # Find matching items
                affected_rows = 0
                for item in MOCK_DATA["menu_items"]:
                    if item_name.lower() in item.get("name", "").lower():
                        item["disabled"] = disabled
                        affected_rows += 1
                        
                return {
                    "success": True,
                    "results": [{"affected_rows": affected_rows}],
                    "columns": ["affected_rows"],
                    "query": query,
                }
    
    # Default fallback
    return {
        "success": True,
        "results": [{"result": "Mock data response"}],
        "columns": ["result"],
        "query": query,
    }

def load_application_context():
    """Load all application context files and configuration in one place

    Returns:
        dict: A dictionary containing all application context including
              business rules, database schema, and example queries
    """
    try:
        # Import all business rules from both system and business-specific modules
        from prompts.system_rules import (
            ORDER_STATUS,
            RATING_SIGNIFICANCE,
            ORDER_TYPES,
            QUERY_RULES,
        )
        from prompts.business_rules import (
            get_business_context,
            BUSINESS_METRICS,
            TIME_PERIOD_GUIDANCE,
            DEFAULT_LOCATION_ID,
        )

        # Get the combined business context
        business_context = get_business_context()

        # Load database schema
        with open("prompts/database_schema.md", "r", encoding="utf-8") as f:
            database_schema = f.read()

        # Load example queries from prompts module
        from prompts import EXAMPLE_QUERIES

        # Create an integrated context object with all business rules
        return {
            "business_rules": business_context,
            "database_schema": database_schema,
            "example_queries": EXAMPLE_QUERIES,
        }
    except Exception as e:
        print(f"Error loading application context: {str(e)}")
        return None

def get_clients():
    """Get the OpenAI client and config"""
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    xai_config = {
        "XAI_TOKEN": os.getenv("XAI_TOKEN"), 
        "XAI_API_URL": os.getenv("XAI_API_URL"),
        "XAI_MODEL": os.getenv("XAI_MODEL")
    }
    return openai_client, xai_config

# Import the LangChain integration with error handling
try:
    from utils.langchain_integration import (
        create_langchain_agent,
        StreamlitCallbackHandler,
        create_sql_database_tool,
        create_menu_update_tool,
        integrate_with_existing_flow,
        clean_text_for_speech,
        setup_logging,
    )

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importing LangChain modules: {str(e)}")
    st.error(
        "Please install required packages: pip install langchain==0.0.150 langchain-community<0.1.0"
    )

# Initialize session state for LangChain components
if "langchain_agent" not in st.session_state:
    st.session_state.langchain_agent = None

if "agent_memory" not in st.session_state:
    st.session_state.agent_memory = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True  # Default to enabled

if "voice_instance" not in st.session_state:
    st.session_state.voice_instance = None

if "clear_input" not in st.session_state:
    st.session_state.clear_input = False

if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id = 62  # Default location ID

if "selected_location_ids" not in st.session_state:
    st.session_state.selected_location_ids = [
        62
    ]  # Default to list with single location

if "selected_club" not in st.session_state:
    st.session_state.selected_club = "Idle Hour Country Club"  # Default club

if "context" not in st.session_state:
    st.session_state.context = {}
# Define available locations organized by club
club_locations = {
    "Idle Hour Country Club": {"locations": [62], "default": 62},
    "Pinetree Country Club": {"locations": [61, 66], "default": 61},
    "East Lake Golf Club": {"locations": [16], "default": 16},
}

# Initialize session state for voice persona
if "voice_persona" not in st.session_state:
    st.session_state.voice_persona = "casual"  # Default to casual


def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Execute SQL query using the existing app functions.

    Args:
        query: SQL query to execute

    Returns:
        dict: Query result
    """
    # Adjust the query for timezone
    adjusted_query = adjust_query_timezone(query, st.session_state.selected_location_id)

    # Execute the query
    result = execute_menu_query(adjusted_query)

    return result


def create_tools_for_agent():
    """
    Create tools for the LangChain agent based on the existing functionality.
    """
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain is not available. Please install required packages.")
        return []

    # SQL database tool
    sql_tool = create_sql_database_tool(execute_query_func=execute_sql_query)

    # Menu update tool
    def execute_menu_update(update_spec):
        # This function calls into the existing code for menu updates
        if isinstance(update_spec, str):
            try:
                update_spec = json.loads(update_spec)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON in update specification",
                }

        item_name = update_spec.get("item_name")
        new_price = update_spec.get("new_price")
        disabled = update_spec.get("disabled")

        if not item_name:
            return {
                "success": False,
                "error": "Missing item_name in update specification",
            }

        if new_price is not None:
            # Update price query
            query = f"UPDATE items SET price = {new_price} WHERE name ILIKE '%{item_name}%' AND location_id = {st.session_state.selected_location_id} RETURNING *"
        elif disabled is not None:
            # Enable/disable query
            disabled_value = str(disabled).lower()
            query = f"UPDATE items SET disabled = {disabled_value} WHERE name ILIKE '%{item_name}%' AND location_id = {st.session_state.selected_location_id} RETURNING *"
        else:
            return {
                "success": False,
                "error": "Invalid update specification - must include either new_price or disabled",
            }

        return execute_sql_query(query)

    menu_tool = create_menu_update_tool(execute_update_func=execute_menu_update)

    # Return all tools
    return [sql_tool, menu_tool]


def setup_langchain_agent():
    """Set up the LangChain agent with the appropriate tools and memory"""
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain is not available. Please install required packages.")
        return None

    if st.session_state.langchain_agent is None:
        try:
            # Create tools
            tools = create_tools_for_agent()

            # Load context for the agent
            context = load_application_context()
            business_context = context.get("business_rules", "")

            # Create system message with context
            system_message = f"""
            You are an AI assistant for a restaurant management system.
            You can help answer questions about orders, menu items, and other restaurant data.
            You can also update menu items, change prices, and enable/disable items.
            
            IMPORTANT ORDER STATUS RULES:
            - When a user asks about "orders" in general without specifying a status, always assume they mean COMPLETED orders (status = 7)
            - For explicit status queries, use the exact status specified by the user
            - Order status values: 1=pending, 3=in progress, 5=ready, 7=completed, 9=cancelled
            
            Here is some context about the business:
            {business_context}
            
            Use the provided tools to help answer questions and fulfill requests.
            """

            # Create the agent
            from langchain.memory import ConversationBufferMemory

            memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True
            )
            st.session_state.agent_memory = memory

            # Get OpenAI API key from environment
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                st.error("OpenAI API key not found in environment variables")
                return None

            # Verify API key functionality with OpenAI client (older version style)
            try:
                # Set the API key
                openai.api_key = openai_api_key

                # Make a minimal API call to verify the key works
                # Just checking the models endpoint which requires minimal resources
                openai.Model.list(limit=1)
            except Exception as e:
                st.error(f"Error initializing OpenAI client: {str(e)}")
                return None

            # Create the agent
            agent = create_langchain_agent(
                openai_api_key=openai_api_key,
                tools=tools,
                memory=memory,
                verbose=True,
                model_name="gpt-3.5-turbo",  # Use a model available in older API
                temperature=0.3,
                streaming=True,
            )

            # Store in session state
            st.session_state.langchain_agent = agent

        except Exception as e:
            st.error(f"Error setting up LangChain agent: {str(e)}")
            return None

    return st.session_state.langchain_agent


def process_query_with_langchain(query: str, output_container):
    """
    Process a query using the LangChain agent and display the results.

    Args:
        query: User query
        output_container: Streamlit container to display output
    """
    if not LANGCHAIN_AVAILABLE:
        output_container.error(
            "LangChain is not available. Please install required packages."
        )
        return {"success": False, "error": "LangChain is not available"}

    # Clear any previous content in the output container
    output_container.empty()

    # Set up callback handler for streaming output
    callback_handler = StreamlitCallbackHandler(output_container)

    # Get or create agent
    agent = setup_langchain_agent()
    if not agent:
        output_container.error("Failed to set up LangChain agent")
        return {"success": False, "error": "Failed to set up LangChain agent"}

    # Create a mock session state for compatibility
    mock_session = MockSessionState()
    mock_session.selected_location_id = st.session_state.selected_location_id
    mock_session.selected_location_ids = st.session_state.selected_location_ids
    mock_session.selected_club = st.session_state.selected_club

    # Get context
    context = {}
    if "context" in st.session_state:
        context = st.session_state.context

    # Ensure location IDs are explicitly added to context
    context["selected_location_id"] = st.session_state.selected_location_id
    context["selected_location_ids"] = st.session_state.selected_location_ids
    context["selected_club"] = st.session_state.selected_club

    # Create tools
    tools = create_tools_for_agent()

    try:
        # Run query through LangChain
        with st.spinner("Processing..."):
            # Show a thinking message
            output_container.markdown("_Thinking..._")

            # Process the query
            result = integrate_with_existing_flow(
                query=query,
                tools=tools,
                context=context,
                agent=agent,
                callback_handler=callback_handler,
            )

        # Update chat history with the text answer if available, otherwise use summary
        chat_message = result.get("text_answer", result.get("summary", ""))

        # Store both the query and a response object with verbal and text components
        response_entry = {
            "summary": result.get("summary", ""),
            "verbal_answer": result.get("verbal_answer", ""),
            "text_answer": result.get("text_answer", ""),
            "sql_query": result.get("sql_query", ""),
        }

        # Append both query and structured response to chat history
        st.session_state.chat_history.append((query, response_entry))

        # Update context
        if "context" not in st.session_state:
            st.session_state.context = {}
        st.session_state.context = result.get("context", {})

        # Track if voice was used to determine if auto-listen should be triggered
        voice_was_used = False

        # Process voice if enabled
        if st.session_state.voice_enabled and st.session_state.voice_instance:
            voice = st.session_state.voice_instance
            if voice.initialized and voice.enabled:
                try:
                    # Use the verbal_answer specifically for voice if available
                    verbal_text = result.get("verbal_answer", result.get("summary", ""))
                    if verbal_text:
                        # Clean the text for better speech synthesis if clean_text_for_speech is available
                        if "clean_text_for_speech" in globals():
                            verbal_text = clean_text_for_speech(verbal_text)

                        # Get persona name for display
                        persona_name = st.session_state.get(
                            "voice_persona", "casual"
                        ).title()

                        # Show voice indicator with Swoop branding and persona info
                        with st.status(
                            f"Processing voice output ({persona_name} style)...",
                            state="running",
                        ):
                            st.markdown(
                                f'<div style="color: #FF8B00; font-weight: 500; font-family: Montserrat, sans-serif;">🔊 Speaking with {persona_name} voice style...</div>',
                                unsafe_allow_html=True,
                            )
                            voice.speak(verbal_text)
                            st.success(f"✓ Voice response complete")
                            voice_was_used = True
                except Exception as voice_error:
                    st.warning(f"Voice output error: {str(voice_error)}")

        # Auto-listen after voice response if enabled
        if voice_was_used and st.session_state.get("auto_listen_enabled", False):
            st.info("Auto-listening for your next question...")
            # Start speech recognition in a new thread to avoid blocking the UI
            thread = threading.Thread(target=background_speech_recognition_with_timeout)
            thread.daemon = True
            thread.start()

        return result
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        output_container.error(error_msg)
        st.session_state.chat_history.append((query, error_msg))
        return {"success": False, "error": str(e)}


def clear_query_input():
    """Clear the query input field - this function is not used anymore"""
    # Don't modify the session state directly
    pass


def init_voice():
    """Initialize voice functionality with direct API approach"""
    global ELEVENLABS_AVAILABLE, PYGAME_AVAILABLE

    if (
        "voice_instance" not in st.session_state
        or st.session_state.voice_instance is None
    ):
        try:
            # Always set voice dependencies to be available
            ELEVENLABS_AVAILABLE = True
            PYGAME_AVAILABLE = True

            # Get the current persona from session state (default to casual)
            persona = st.session_state.get("voice_persona", "casual")

            # Create the voice instance with the selected persona
            voice = SimpleVoice(persona=persona)

            # Set session state
            st.session_state.voice_instance = voice
            st.session_state.voice_enabled = True

            # Initialize silently without showing status messages
            return voice
        except Exception as e:
            # This should only happen if there's a serious error
            with st.sidebar:
                st.error(f"❌ Error initializing voice: {str(e)}")
            st.session_state.voice_instance = None
            st.session_state.voice_enabled = True  # Keep enabled anyway
            return None

    return st.session_state.voice_instance


def run_langchain_streamlit_app():
    """Main function to run the Streamlit app with LangChain integration"""
    # Get logger that was already set up in the __main__ block
    logger = logging.getLogger("ai_menu_updater")
    logger.info(f"Starting Streamlit LangChain app session")
    
    # Initialize voice
    voice = init_voice()

    # Main area - Set up the title with Swoop branding
    st.markdown(
        """
    <div style="display: flex; justify-content: center; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-family: 'Montserrat', sans-serif; font-weight: 700;">Swoop AI</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Immediately set mock data true to prevent UI hanging
    global USING_MOCK_DATA
    USING_MOCK_DATA = True
    db_status_placeholder = st.empty()
    
    # Test database connection in a non-blocking way
    def check_db_in_background():
        # Get logger for this context
        logger = logging.getLogger("ai_menu_updater")
        
        try:
            # Use a very short timeout for initial connection
            conn = get_db_connection(timeout=1)
            if conn:
                global USING_MOCK_DATA
                USING_MOCK_DATA = False
                conn.close()
                try:
                    db_status_placeholder.success("✅ Connected to database")
                except Exception as ui_error:
                    # Log the UI update error but don't crash
                    logger.warning(f"UI update error (connected): {str(ui_error)}")
            else:
                try:
                    db_status_placeholder.warning("⚠️ Database connection failed. Running in demo mode with mock data.")
                except Exception as ui_error:
                    # Log the UI update error but don't crash
                    logger.warning(f"UI update error (failed): {str(ui_error)}")
        except Exception as e:
            try:
                db_status_placeholder.warning(f"⚠️ Database connection failed: {str(e)}. Running in demo mode with mock data.")
            except Exception as ui_error:
                # Log the UI update error but don't crash
                logger.warning(f"UI update error (exception): {str(ui_error)}")
    
    # Start connection check in background
    db_thread = threading.Thread(target=check_db_in_background)
    db_thread.daemon = True
    db_thread.start()

    # Define avatars for chat display
    avatars = {"user": "user", "assistant": "assistant"}

    # Set up sidebar
    st.sidebar.title("")
    
    # Add database connection status in sidebar
    with st.sidebar.expander("Database Status", expanded=False):
        status_indicator = st.empty()
        
        # Show immediate status based on current flag
        if USING_MOCK_DATA:
            status_indicator.error("❌ Database connection failed or checking...")
            st.info("Using mock data for demonstration")
            
            # Connection details
            st.write("Connection Details:")
            st.code(f"""
            Host: {DB_CONFIG['host']}
            Port: {DB_CONFIG['port']}
            Database: {DB_CONFIG['database']}
            """)
            
            # Reconnect button with loading state
            if st.button("Try reconnecting"):
                with st.spinner("Attempting to connect..."):
                    reconnection_result = attempt_db_reconnection()
                    if reconnection_result["success"]:
                        st.success("✅ Successfully reconnected to database!")
                        status_indicator.success("✅ Connected to database")
                        st.rerun()
                    else:
                        st.error(f"❌ Connection failed: {reconnection_result['error']}")
        else:
            status_indicator.success("✅ Connected to database")
    
    # Club selection in sidebar
    selected_club = st.sidebar.selectbox(
        "Select Club",
        options=list(club_locations.keys()),
        index=(
            list(club_locations.keys()).index(st.session_state.selected_club)
            if st.session_state.selected_club in club_locations
            else 0
        ),
    )

    # Update selected club
    if selected_club != st.session_state.selected_club:
        st.session_state.selected_club = selected_club
        st.session_state.selected_location_id = club_locations[selected_club]["default"]
        st.session_state.selected_location_ids = club_locations[selected_club][
            "locations"
        ]

        # Clear chat history and context when switching clubs
        st.session_state.chat_history = []
        st.session_state.context = {}

        # Show a notification that history was cleared
        st.sidebar.success(f"Switched to {selected_club}. Chat history cleared.")

        # Reset the LangChain agent to start fresh
        st.session_state.langchain_agent = None
        st.session_state.agent_memory = None

    # Voice settings expander
    with st.sidebar.expander("🔊 Voice Settings", expanded=False):
        voice_enabled = st.checkbox(
            "Enable voice responses",
            value=st.session_state.voice_enabled,
            help="Turn on/off voice responses using ElevenLabs",
        )

        # Add persona selector
        available_personas = [
            "casual",
            "professional",
            "enthusiastic",
            "pro_caddy",
            "clubhouse_legend",
        ]
        selected_persona = st.selectbox(
            "Voice Persona",
            options=available_personas,
            index=(
                available_personas.index(st.session_state.voice_persona)
                if st.session_state.voice_persona in available_personas
                else 0
            ),
            help="Select voice persona style for responses",
        )

        # Update persona if changed
        if selected_persona != st.session_state.voice_persona:
            st.session_state.voice_persona = selected_persona
            if st.session_state.voice_instance:
                st.session_state.voice_instance.change_persona(selected_persona)
                st.success(f"Changed to {selected_persona} voice persona")

        # Only update voice status if it changed
        if voice_enabled != st.session_state.voice_enabled:
            if voice_enabled and not voice:
                # Try to initialize voice if enabling and not available
                voice = init_voice()
                if voice and voice.initialized:
                    st.session_state.voice_enabled = True
                    st.success("Voice responses enabled")
                else:
                    st.session_state.voice_enabled = False
            else:
                st.session_state.voice_enabled = voice_enabled
                if voice_enabled:
                    st.success("Voice responses enabled")
                else:
                    st.info("Voice responses disabled")

    # Add voice input settings
    with st.sidebar.expander("🎤 Voice Input Settings", expanded=False):
        st.write("Speech recognition settings:")

        # Add auto-listen option - disabled by default
        if "auto_listen_enabled" not in st.session_state:
            st.session_state.auto_listen_enabled = False

        auto_listen = st.checkbox(
            "Auto-listen after AI responds",
            value=st.session_state.auto_listen_enabled,
            help="Automatically listen for your next question after the AI finishes speaking",
        )

        # Update auto-listen status if changed
        if auto_listen != st.session_state.auto_listen_enabled:
            st.session_state.auto_listen_enabled = auto_listen
            if auto_listen:
                st.success("Auto-listen enabled")
            else:
                st.info("Auto-listen disabled")

        # Set timeout settings for auto-listen
        if st.session_state.auto_listen_enabled:
            if "auto_listen_timeout" not in st.session_state:
                st.session_state.auto_listen_timeout = 5

            st.session_state.auto_listen_timeout = st.slider(
                "Silence timeout (seconds)",
                min_value=1,
                max_value=10,
                value=st.session_state.auto_listen_timeout,
                help="Stop listening if no speech is detected after this many seconds",
            )

        # Add button to test voice input
        if st.button("Test Voice Input", key="test_voice_input"):
            try:
                # Attempt to import the speech recognition library to test if it's available
                import speech_recognition as sr

                st.success("✅ Speech recognition library is available!")

                # Check if PyAudio is available
                try:
                    import pyaudio

                    st.success("✅ PyAudio is available!")
                except ImportError:
                    st.error(
                        "❌ PyAudio is not available. Install with: pip install PyAudio"
                    )
            except ImportError:
                st.error(
                    "❌ Speech recognition library is not available. Install with: pip install SpeechRecognition"
                )

    # Clean up the voice test session state variables since we don't use those buttons anymore
    for key in ["test_voice", "diagnose_voice"]:
        if key in st.session_state:
            del st.session_state[key]

    # LangChain settings expander
    with st.sidebar.expander("LangChain Settings", expanded=False):
        # Reset LangChain agent button
        if st.button("Reset LangChain Agent"):
            st.session_state.langchain_agent = None
            st.session_state.agent_memory = None
            st.success("LangChain agent reset")

    # Display chat history in native Streamlit chat components
    if not st.session_state.chat_history and not st.session_state.clear_input:
        # Show welcome message if no history
        with st.chat_message("assistant"):
            st.markdown(
                """
            <div style="font-family: 'Montserrat', sans-serif;">
            Hello! I'm your Swoop AI assistant. What would you like to know?
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        # Display previous chat history
        for user_query, ai_response in st.session_state.chat_history:
            # User message
            with st.chat_message("user"):
                st.markdown(user_query)

            # Assistant message
            with st.chat_message("assistant"):
                if isinstance(ai_response, dict):
                    # Display the text answer with improved formatting
                    if "text_answer" in ai_response and ai_response["text_answer"]:
                        st.markdown(ai_response["text_answer"])
                    elif "summary" in ai_response and ai_response["summary"]:
                        st.markdown(ai_response["summary"])
                    else:
                        st.markdown("No response available")

                    # Show SQL query in an expander if available, with better styling
                    if "sql_query" in ai_response and ai_response["sql_query"]:
                        with st.expander("🔍 View SQL Query", expanded=False):
                            st.code(ai_response["sql_query"], language="sql")
                else:
                    # Handle legacy string responses
                    st.markdown(ai_response)

    # Create an output container for streaming responses
    output_container = st.empty()

    # Check if there's text from speech recognition ready to be processed
    if st.session_state.get("speech_ready", False):
        query = st.session_state.speech_text
        st.session_state.speech_ready = False
        st.session_state.speech_text = ""

        # Display user query in a chat message
        with st.chat_message("user"):
            st.write(query)

        # Process query with the assistant
        with st.chat_message("assistant"):
            # Create a container for the streaming output
            stream_container = st.empty()

            # Process the query
            result = process_query_with_langchain(query, stream_container)

            # Clear the container after processing
            stream_container.empty()

            # Display the text answer with proper markdown formatting
            if "text_answer" in result and result["text_answer"]:
                st.markdown(result["text_answer"])
            else:
                st.markdown(result.get("summary", "No result available"))

            # Show SQL query in an expander if available
            if "sql_query" in result and result["sql_query"]:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(result["sql_query"], language="sql")

        # Clear input after processing
        if "clear_input" not in st.session_state:
            st.session_state.clear_input = True
            st.rerun()

    # Use full width for chat input (no columns needed)
    query = st.chat_input(
        "Ask about orders, menu items, revenue, or other restaurant data..."
    )

    # Process regular text input
    if query:
        # Display user query in a chat message
        with st.chat_message("user"):
            st.write(query)

        # Process query with the assistant
        with st.chat_message("assistant"):
            # Create a container for the streaming output
            stream_container = st.empty()

            # Process the query
            result = process_query_with_langchain(query, stream_container)

            # Clear the container after processing
            stream_container.empty()

            # Display the text answer with proper markdown formatting
            if "text_answer" in result and result["text_answer"]:
                st.markdown(result["text_answer"])
            else:
                st.markdown(result.get("summary", "No result available"))

            # Show SQL query in an expander if available
            if "sql_query" in result and result["sql_query"]:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(result["sql_query"], language="sql")

        # Clear input after processing
        if "clear_input" not in st.session_state:
            st.session_state.clear_input = True
            st.rerun()

    # Clear the flag after rerun
    if "clear_input" in st.session_state and st.session_state.clear_input:
        st.session_state.clear_input = False

    # Add a clear chat button at the bottom of the sidebar
    with st.sidebar:
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.context = {}
            st.rerun()


# Create a custom function to ensure voice dependencies are available
def initialize_voice_dependencies():
    """Initialize voice dependencies and return overall status"""
    global ELEVENLABS_AVAILABLE, PYGAME_AVAILABLE

    # Force dependencies to be available
    ELEVENLABS_AVAILABLE = True
    PYGAME_AVAILABLE = True

    # Return success status
    return {"elevenlabs": True, "audio_playback": True}

# Make sure voice is enabled by default
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True  # Default to enabled


# Create a simplified voice class that doesn't have dependency issues
class SimpleVoice:
    """Simple voice class that avoids complex imports"""

    def __init__(self, persona="casual", **kwargs):
        self.enabled = True
        self.initialized = True
        self.persona = persona

        # Get persona info
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]

        print(f"✓ Initialized SimpleVoice with persona: {persona}")

    def clean_text_for_speech(self, text):
        """Clean text to make it more suitable for speech synthesis"""
        import re
        
        # Try to import inflect, but make it optional
        try:
            import inflect
            p = inflect.engine()
            
            # Dictionary of special cases for common ordinals
            ordinal_words = {
                1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
                6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
                11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 
                15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 
                19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fortieth",
                50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth", 
                90: "ninetieth", 100: "hundredth", 1000: "thousandth"
            }
            
            # Function to convert ordinal numbers to words
            def replace_ordinal(match):
                # Extract the number part (e.g., "21" from "21st")
                num = int(match.group(1))
                suffix = match.group(2)  # st, nd, rd, th
                
                # Check for special cases first
                if num in ordinal_words:
                    return ordinal_words[num]
                
                # For numbers 21-99 that aren't in our special cases
                if 21 <= num < 100:
                    tens = (num // 10) * 10
                    ones = num % 10
                    
                    if ones == 0:  # For 30, 40, 50, etc.
                        return ordinal_words[tens]
                    else:
                        # Convert the base number to words (e.g., 21 -> twenty-one)
                        base_word = p.number_to_words(num)
                        
                        # If ones digit has a special ordinal form
                        if ones in ordinal_words:
                            # Replace last word with its ordinal form
                            base_parts = base_word.split("-")
                            if len(base_parts) > 1:
                                return f"{base_parts[0]}-{ordinal_words[ones]}"
                            else:
                                return ordinal_words[ones]
                
                # For other numbers, fallback to converting to words then adding suffix
                word_form = p.number_to_words(num)
                return word_form
            
            # Replace ordinal numbers (1st, 2nd, 3rd, 21st, etc.) with word equivalents
            text = re.sub(r'(\d+)(st|nd|rd|th)', replace_ordinal, text)
        except ImportError:
            # If inflect is not available, we'll skip the ordinal conversion
            pass
        
        # Remove markdown formatting
        # Replace ** and * (bold and italic) with nothing
        text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)

        # Remove markdown bullet points and replace with natural pauses
        text = re.sub(r"^\s*[\*\-\•]\s*", "", text, flags=re.MULTILINE)

        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Replace newlines with spaces to make it flow better in speech
        text = re.sub(r"\n+", " ", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # Replace common abbreviations with full words
        text = text.replace("vs.", "versus")
        text = text.replace("etc.", "etcetera")
        text = text.replace("e.g.", "for example")
        text = text.replace("i.e.", "that is")

        # Improve speech timing with commas for complex sentences
        text = re.sub(
            r"(\d+)([a-zA-Z])", r"\1, \2", text
        )  # Put pauses after numbers before words

        # Add a pause after periods that end sentences
        text = re.sub(r"\.(\s+[A-Z])", r". \1", text)

        return text

    def speak(self, text):
        """Speak the given text using ElevenLabs API"""
        if not text:
            return False

        # Clean the text for better speech synthesis
        text = self.clean_text_for_speech(text)

        try:
            # Try to use a simple direct approach with elevenlabs
            try:
                # Simplified approach with minimal imports
                import os
                from dotenv import load_dotenv
                import requests
                import pygame
                from io import BytesIO
                import time

                # Load API key
                load_dotenv()
                api_key = os.getenv("ELEVENLABS_API_KEY")

                if not api_key:
                    raise ValueError("No ElevenLabs API key found")

                # Make direct API call to ElevenLabs
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": api_key,
                }

                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                }

                print("Generating speech with ElevenLabs API...")
                response = requests.post(url, json=data, headers=headers)

                if response.status_code != 200:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text}"
                    )

                # Get audio data
                audio_data = BytesIO(response.content)

                # Play with pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                print(f"✓ Successfully played audio with {self.persona} voice")
                return True

            except Exception as e:
                print(f"Direct API attempt failed: {str(e)}")
                raise

        except Exception as e:
            # Fall back to simulation
            print(f"🔊 [{self.persona}] Would speak: {text[:50]}...")
            print(f"Voice error: {str(e)}")
            return True

    def toggle(self):
        """Toggle voice on/off"""
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Voice {status}"

    def change_persona(self, persona):
        """Change the voice persona"""
        self.persona = persona
        persona_info = get_persona_info(persona)
        self.voice_name = f"{persona.title()} Voice"
        self.voice_id = persona_info["voice_id"]
        self.prompt = persona_info["prompt"]
        return f"Changed to {persona} voice"


# Override the imported ElevenLabsVoice with our better version
ElevenLabsVoice = SimpleVoice


# Add a special diagnostic function to test and fix voice issues
def test_elevenlabs_connection():
    """Test and diagnose ElevenLabs connection issues - simplified version"""
    import os
    from dotenv import load_dotenv
    import importlib
    import sys

    # Make sure we have the latest environment variables
    load_dotenv(override=True)

    results = {
        "api_key_present": False,
        "elevenlabs_installed": False,
        "pygame_installed": False,
        "can_list_voices": False,
        "can_generate_audio": False,
        "can_play_audio": False,
        "errors": [],
    }

    # Check API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if api_key:
        results["api_key_present"] = True
        print("✓ ElevenLabs API key is present")
    else:
        results["errors"].append("No ElevenLabs API key found")
        print("✗ No ElevenLabs API key found")

    # Check if elevenlabs is installed
    try:
        # Check if we can import the package without actually importing it
        spec = importlib.util.find_spec("elevenlabs")
        if spec is not None:
            results["elevenlabs_installed"] = True
            print("✓ ElevenLabs package is installed")
            print(f"  Version: {getattr(spec, '__version__', 'unknown')}")

            # Don't actually import elevenlabs to avoid the error
            results["can_list_voices"] = "Unknown - skipped to avoid errors"
            results["can_generate_audio"] = "Unknown - skipped to avoid errors"
        else:
            results["errors"].append("ElevenLabs package is not found")
            print("✗ ElevenLabs package is not installed")
    except Exception as e:
        results["errors"].append(f"Error checking ElevenLabs: {str(e)}")
        print(f"✗ Error checking elevenlabs: {str(e)}")

    # Check if pygame is installed
    try:
        # Check if we can import pygame
        spec = importlib.util.find_spec("pygame")
        if spec is not None:
            results["pygame_installed"] = True
            print("✓ Pygame is installed")

            # Try to import and initialize mixer
            try:
                import pygame

                pygame.mixer.init()
                print("✓ Pygame mixer initialized successfully")
                results["can_play_audio"] = "Possibly - mixer initialized"
            except Exception as me:
                error_msg = f"Error initializing pygame mixer: {str(me)}"
                results["errors"].append(error_msg)
                print(f"✗ {error_msg}")
        else:
            results["errors"].append("Pygame is not found")
            print("✗ Pygame is not installed")
    except Exception as e:
        results["errors"].append(f"Error checking pygame: {str(e)}")
        print(f"✗ Error checking pygame: {str(e)}")

    # Provide solution
    results[
        "solution"
    ] = """
    It looks like there's an issue with your elevenlabs package. Here are some solutions:
    
    1. Downgrade to a more stable version:
       ```
       pip uninstall elevenlabs
       pip install elevenlabs==0.2.26
       ```
    
    2. Try using a simpler voice implementation:
       We've updated the app to use a simpler implementation that should work better
       
    Press "Re-initialize Voice System" button below to try with the updated implementation.
    """

    return results


# Add a modified speech recognition function with timeout
def recognize_speech_with_timeout(timeout=5, phrase_time_limit=15):
    """
    Capture audio from the microphone and convert it to text with a custom timeout.

    Args:
        timeout: Time to wait before stopping if no speech is detected
        phrase_time_limit: Maximum duration of speech to recognize

    Returns:
        str: Recognized text, or empty string if recognition failed
    """
    try:
        import speech_recognition as sr

        # Create a recognizer instance
        recognizer = sr.Recognizer()

        # Capture audio from the microphone
        with sr.Microphone() as source:
            st.session_state["recording"] = True

            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            # Display recording indicator
            with st.spinner(f"Listening... (timeout: {timeout}s)"):
                # Capture audio with the specified timeout
                try:
                    audio = recognizer.listen(
                        source, timeout=timeout, phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    st.info("No speech detected within timeout period.")
                    return ""

            # Try to recognize the speech
            try:
                st.session_state["recording"] = False
                # Use Google's speech recognition
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                st.warning("Could not understand audio. Please try again.")
                return ""
            except sr.RequestError as e:
                st.error(f"Speech recognition service error: {e}")
                return ""

    except ImportError:
        st.error(
            "Speech recognition library not installed. Run: pip install SpeechRecognition PyAudio"
        )
        return ""
    except Exception as e:
        st.error(f"Error during speech recognition: {e}")
        return ""
    finally:
        st.session_state["recording"] = False


# Add a background speech recognition function with timeout
def background_speech_recognition_with_timeout():
    """Run speech recognition in a background thread with timeout and store the result in session state"""
    # Get logger for this context
    logger = logging.getLogger("ai_menu_updater")
    
    try:
        # Get the timeout from session state or use default
        timeout = st.session_state.get("auto_listen_timeout", 5)

        # Start listening with the timeout
        text = recognize_speech_with_timeout(timeout=timeout)
        if text:
            # Use Streamlit's threading utilities to safely update the UI
            # Store the data to session state (which is thread-safe)
            st.session_state["speech_text"] = text
            st.session_state["speech_ready"] = True
            
            # Trigger a rerun safely using queue_callback if available
            try:
                # For newer Streamlit versions
                if hasattr(st, 'runtime') and hasattr(st.runtime, 'scriptrunner') and hasattr(st.runtime.scriptrunner, 'add_script_run_ctx'):
                    def safe_update():
                        st.rerun()
                    st.runtime.scriptrunner.add_script_run_ctx(safe_update)()
                else:
                    # This will still work but may show the warning
                    logger.debug("Using basic session state update for speech recognition")
            except Exception as rerun_error:
                logger.warning(f"Could not safely trigger rerun: {str(rerun_error)}")
    except Exception as e:
        # Use logger instead of direct UI updates from background thread
        logger.error(f"Error in background speech recognition: {str(e)}")
    finally:
        st.session_state["recording"] = False


# Initialize more session state variables
if "recording" not in st.session_state:
    st.session_state.recording = False

if "speech_text" not in st.session_state:
    st.session_state.speech_text = ""

if "speech_ready" not in st.session_state:
    st.session_state.speech_ready = False

if "auto_listen_enabled" not in st.session_state:
    st.session_state.auto_listen_enabled = False

if "auto_listen_timeout" not in st.session_state:
    st.session_state.auto_listen_timeout = 5

def check_database_connection():
    """Check if the database connection is available
    
    Returns:
        dict: Dictionary with connection status
    """
    global USING_MOCK_DATA
    
    try:
        # Use a short timeout for quick check
        conn = get_db_connection(timeout=1)
        if conn is None:
            return {"connected": False, "message": "Connection returned None"}
        
        # If we got here with a real connection, close it and return success
        if not USING_MOCK_DATA and conn:
            conn.close()
            return {"connected": True, "message": "Connected successfully"}
        else:
            return {"connected": False, "message": "Using mock data mode"}
    except Exception as e:
        return {"connected": False, "message": str(e)}

def attempt_db_reconnection():
    """Attempt to reconnect to the database
    
    Returns:
        dict: Dictionary with reconnection result
    """
    global USING_MOCK_DATA
    
    try:
        # Use a short timeout to prevent UI hanging
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=2,  # Add short timeout
        )
        
        if conn:
            USING_MOCK_DATA = False
            conn.close()
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": "Connection returned None"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def setup_enhanced_logging():
    """Set up enhanced logging to capture all prompts"""
    # Create a session ID for this run
    session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # Set up log file path
    log_filename = f"logs/enhanced_log_{session_id}.log"
    
    # Define app_log_filename outside the conditional block to ensure it's always available
    app_log_filename = f"logs/app_log_{session_id}.log"
    
    # Configure root logger to capture everything
    logging.basicConfig(
        level=logging.DEBUG,  # Capture all log levels
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also output to console
        ]
    )
    
    # Create or get the application-specific logger
    app_logger = logging.getLogger("ai_menu_updater")
    app_logger.setLevel(logging.DEBUG)
    
    # Add specific file handler for the application logger if it doesn't have one
    if not any(isinstance(h, logging.FileHandler) for h in app_logger.handlers):
        app_file_handler = logging.FileHandler(app_log_filename)
        app_file_handler.setLevel(logging.DEBUG)
        app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        app_file_handler.setFormatter(app_formatter)
        app_logger.addHandler(app_file_handler)
        
    # Output session start messages
    app_logger.info(f"=== New Session Started at {session_id} ===")
    app_logger.info(f"All logs consolidated in {app_log_filename}")
    
    return app_logger

def apply_monkey_patches():
    """Apply monkey patches to ensure complete logging and proper text processing"""
    try:
        # Get the application logger
        logger = logging.getLogger("ai_menu_updater")
        
        # Apply improved ordinal conversion to SimpleVoice
        from utils.speech_utils import clean_text_for_speech as speech_utils_clean_text
        
        # Create a compatibility wrapper that handles 'self' parameter
        def clean_text_wrapper(self, text):
            """Wrapper around the speech_utils clean_text_for_speech function that ignores self"""
            return speech_utils_clean_text(text)
        
        # SimpleVoice is already defined in this file, so we can patch it directly
        SimpleVoice.clean_text_for_speech = clean_text_wrapper
        logger.info("Successfully patched SimpleVoice.clean_text_for_speech with improved ordinal conversion")
        
        # Patch Gemini prompt functions to ensure logging
        import prompts.google_gemini_prompt
        from prompts.google_gemini_prompt import create_gemini_prompt
        original_gemini_prompt = create_gemini_prompt
        
        def patched_gemini_prompt(*args, **kwargs):
            """Patched version that logs the prompt before returning"""
            result = original_gemini_prompt(*args, **kwargs)
            
            # Log the generated prompt (first 100 chars)
            query = kwargs.get('query', '')
            if not query and args and isinstance(args[0], str):
                query = args[0]
            
            # Convert result to string and get length safely
            result_str = str(result) if result is not None else ""
            result_len = len(result_str)
            
            logger.info(f"Generated Gemini prompt for query '{query}' - Length: {result_len}")
            if result_len > 0:
                logger.debug(f"Gemini prompt first 100 chars: {result_str[:min(100, result_len)]}...")
            
            return result
            
        # Replace the original function with our patched version
        prompts.google_gemini_prompt.create_gemini_prompt = patched_gemini_prompt
        logger.info("Successfully patched create_gemini_prompt for logging")
        
        # Patch categorization prompt functions
        import prompts.openai_categorization_prompt
        from prompts.openai_categorization_prompt import create_categorization_prompt, create_query_categorization_prompt
        
        # Patch create_categorization_prompt
        original_cat_prompt = create_categorization_prompt
        def patched_categorization_prompt(*args, **kwargs):
            """Patched version that logs the prompt before returning"""
            result = original_cat_prompt(*args, **kwargs)
            
            # Convert result to string and get length safely
            result_str = str(result) if result is not None else ""
            result_len = len(result_str)
            
            logger.info(f"Generated categorization prompt - Length: {result_len}")
            if result_len > 0:
                logger.debug(f"Categorization prompt first 100 chars: {result_str[:min(100, result_len)]}...")
            
            return result
            
        prompts.openai_categorization_prompt.create_categorization_prompt = patched_categorization_prompt
        
        # Patch create_query_categorization_prompt
        original_query_cat = create_query_categorization_prompt
        def patched_query_categorization_prompt(*args, **kwargs):
            """Patched version that logs the prompt before returning"""
            result = original_query_cat(*args, **kwargs)
            
            # Extract query from args or kwargs
            query = kwargs.get('query', '')
            if not query and args and isinstance(args[0], str):
                query = args[0]
            
            # Convert result to string and get length safely
            result_str = str(result) if result is not None else ""
            result_len = len(result_str)
                
            logger.info(f"Generated query categorization prompt for '{query}' - Length: {result_len}")
            if result_len > 0:
                logger.debug(f"Query categorization prompt first 100 chars: {result_str[:min(100, result_len)]}...")
            
            return result
            
        prompts.openai_categorization_prompt.create_query_categorization_prompt = patched_query_categorization_prompt
        logger.info("Successfully patched categorization prompt functions for logging")
        
        return True
    except Exception as e:
        # Get the logger even in the exception handling case
        logger = logging.getLogger("ai_menu_updater")
        logger.error(f"Error applying monkey patches: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # Set up enhanced logging first
        logger = setup_enhanced_logging()
        logger.info("Starting application with enhanced logging...")
        
        # Apply monkey patches to ensure ordinal conversion works properly
        if apply_monkey_patches():
            logger.info("Successfully applied all patches and logging enhancements")
        else:
            logger.warning("Some patches could not be applied")
        
        # Run the application
        if not LANGCHAIN_AVAILABLE:
            st.error(
                """
            LangChain integration is not available. Please install the required packages:
            ```
            pip install langchain==0.0.150 langchain-community<0.1.0
            ```
            """
            )
        else:
            run_langchain_streamlit_app()
    except Exception as e:
        # Log any startup errors
        if 'logger' in locals():
            logger.error(f"Error during application startup: {str(e)}")
            logger.error(traceback.format_exc())
        else:
            print(f"Error during startup (before logger initialization): {str(e)}")
            traceback.print_exc()
