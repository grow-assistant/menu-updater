"""
Settings for the AI Menu Updater application.
Centralizes configuration from environment variables and default settings.
"""

import os
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and access
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
XAI_TOKEN = os.getenv("XAI_TOKEN")
XAI_API_URL = os.getenv("XAI_API_URL")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-2-1212")

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "swoop"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Timezone Constants
USER_TIMEZONE = pytz.timezone("America/Phoenix")  # Arizona (no DST)
CUSTOMER_DEFAULT_TIMEZONE = pytz.timezone("America/New_York")  # EST
DB_TIMEZONE = pytz.timezone("UTC")

# LangChain settings
DEFAULT_LLM_MODEL = "gpt-3.5-turbo"
LLM_TEMPERATURE = 0.3
LLM_STREAMING = True

# Query paths settings
DEFAULT_LOCATION_ID = 62  # Default to Idle Hour Country Club
CLUB_LOCATIONS = {
    "Idle Hour Country Club": {"locations": [62], "default": 62},
    "Pinetree Country Club": {"locations": [61, 66], "default": 61},
    "East Lake Golf Club": {"locations": [16], "default": 16},
}

# Voice settings
DEFAULT_VOICE_PERSONA = "casual"
AUTO_LISTEN_ENABLED = False
AUTO_LISTEN_TIMEOUT = 5

# Application paths
LOG_DIR = "logs"

# Mock data for testing
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