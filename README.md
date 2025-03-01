# Swoop AI Menu Updater

An AI-powered assistant for restaurant menu management and data analysis built with Streamlit and LangChain.

## Overview

This application provides a conversational AI interface for restaurant managers to:
- Query order history and analytics
- View and modify menu items
- Update prices
- Enable/disable menu items
- Analyze performance data

The application integrates with OpenAI's Large Language Models via LangChain to provide natural language processing and can respond with both text and speech.

## Features

- 🤖 Natural language interface using LangChain and OpenAI
- 🔊 Voice responses using ElevenLabs text-to-speech
- 🎤 Voice input using speech recognition
- 📊 SQL database integration for menu and order data
- 📱 Modern, responsive UI with Streamlit
- 🧠 Context-aware query processing

## Project Structure

The refactored project has the following structure:

```
ai-menu-updater/
├── app/                        # Main application package
│   ├── components/             # UI components
│   │   └── ui_components.py    # Reusable UI components
│   ├── services/               # Service modules
│   │   ├── langchain_service.py # LangChain integration
│   │   └── voice_service.py    # Voice processing
│   ├── utils/                  # Utility modules
│   │   ├── app_state.py        # State management
│   │   ├── database.py         # Database utilities
│   │   └── styling.py          # UI styling
│   ├── __init__.py             # Package initialization
│   └── main.py                 # Main application module
├── config/                     # Configuration
├── database/                   # Database files
├── logs/                       # Log files
├── prompts/                    # AI prompt templates
├── query_paths/                # Query path modules
├── tools/                      # LangChain tools
├── utils/                      # Legacy utilities
├── main_integration.py         # LangChain integration
├── main.py                     # Legacy entry point
└── run_app.py                  # New entry point
```

## Running the Application

To run the application, use:

```bash
streamlit run run_app.py
```

This will start the Streamlit server and open the application in your browser.

## Dependencies

The application requires:

- Python 3.8+
- Streamlit
- LangChain (compatible with version 0.0.150 or newer)
- OpenAI Python client
- psycopg2 (for PostgreSQL database connection)
- pytz (for timezone handling)
- python-dotenv (for environment variables)
- elevenlabs (for text-to-speech)
- pygame (for audio playback)
- SpeechRecognition (for voice input)
- PyAudio (for microphone access)

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DB_HOST=your_database_host
DB_PORT=your_database_port
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

## Notes

- The application will work in "mock" mode if the database is unavailable
- Voice features require an ElevenLabs API key
- LangChain integration provides fallback mechanisms if specific components fail

---

## System Overview

### Core Components

1. **Frontend (Streamlit)**
   - **Chat Interface:**  
     Users interact with the AI assistant via a chat interface. The assistant can:
     - Update menu item details (e.g., price updates or toggling status).
     - Query menu information.
     - Fetch order data (e.g., total sales, revenue comparisons, frequent order metrics, etc.).
   - **Sidebar Navigation:**  
     - Location selection: Users choose the active location (e.g., restaurant branch) from a dropdown.
     - Database Schema Explorer: Visualizes the schema of the database.
     - Theme support: Dark/light mode with custom CSS for tooltips and other UI components.

2. **Database (PostgreSQL)**
   - **Schema Structure:**
     - **Locations, Menus, Categories, Items, Options, Option Items, Orders, Order Items, Ratings & Feedback.**
     - Columns include totals, timestamps, soft deletion flags, and ordering (via `seq_num`).
   - **Operations:**  
     Structured SQL queries are used for menu updates and order queries. Examples include:
     - Calculating total sales revenue for a month.
     - Comparing current month sales to the same month last year.
     - Determining top-selling menu items over a quarter.
     - Measuring average order values and time between orders.
     
3. **AI Integration (OpenAI API)**
   - **Function Calling:**  
     A set of functions is defined in **function_calling_spec.py** for the OpenAI client. Among these:
     - `categorize_request`: Determines what kind of request the user is making.
     - `update_menu_item` and `toggle_menu_item`: Execute menu update operations.
     - `query_orders`: Executes order queries against the database.
   - **Chat Processing Flow:**  
     The app compiles recent conversation history (within token limits), sends it to the OpenAI API, and checks for function calls. For a `query_orders` request, the app:
     - Retrieves the user's selected location from the sidebar.
     - Builds a SQL query (using natural language parameters like time period).
     - Executes the query using shared helper functions (mirroring tests in **tests/test_orders_query.py**).
     - Returns and displays the query results in the conversation.

---

## Application Flow

1. **Session Initialization (in app.py):**
   - **Session State Setup:**  
     Initializes the conversation history with system and assistant welcome messages.
   - **Location Selection:**  
     A sidebar dropdown loads available locations from the `locations` table. The default location (e.g., ID 62) is selected based on your configuration.
     
2. **User Interaction via Chat:**
   - A user types a query (e.g., "What was our total sales revenue for the past month?") in the chat interface.
   - The user's message is stored in the session state. All messages (user and assistant) are displayed in a Streamlit chat layout.

3. **Processing with the AI Assistant:**
   - The recent messages (filtered by token limits) are sent to the OpenAI API via the `run_chat_sequence()` function in **chat_functions.py**.
   - The OpenAI API, using the function calling specification declared in **function_calling_spec.py**, categorizes the request.
   - For order-related queries (`request_type == "query_orders"`), the assistant builds a corresponding SQL query:
     - Example: It constructs a query to calculate total revenue and order count using a date filter (e.g., today, this month, last month) and the selected `location_id`.
   - The SQL query is executed using a helper function (e.g., `execute_order_query()`), and the JSON results are returned to the chat.

4. **Displaying the Result:**
   - The assistant's response (including query results, status updates, etc.) is appended to the session state and displayed in the chat.
   - Token usage is tracked and displayed so that older messages are trimmed when necessary.

5. **Additional Operations:**
   - Menu update operations (e.g., updating prices, toggling an item's status) follow a similar flow and are executed via corresponding functions (`update_menu_item` or `toggle_menu_item`).
   - Other custom queries (mirroring those in **tests/test_orders_query.py**) can be integrated similarly by extending the function calling logic.

---

## Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/grow-assistant/menu-updater.git
   cd menu-updater
   ```

2. **Set Up Python Environment:**
   - Use Python 3.8 or higher.
   - Create and activate a virtual environment (recommended).

3. **Set Up PostgreSQL:**
   - Install PostgreSQL.
   - Create a new database for the project.
   - Run any supplied SQL scripts to create the necessary tables.

4. **Configure Environment Variables:**
   Create a `.env` file with:
   ```ini
   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_SERVER=localhost
   OPENAI_API_KEY=your_openai_key
   ```

5. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the App:**
   ```bash
   streamlit run app.py
   ```
   The app will open in your browser (typically at http://localhost:8501).

---

## Testing Order Queries

A dedicated test file (**tests/test_orders_query.py**) contains SQL queries that are used to validate various order-related operations. These queries include:
- Total sales revenue for the past month.
- Sales comparison (this month vs. same month last year).
- Top menu items by revenue.
- Average order value over time.
- Average time between a customer's first two orders.
- Customer repeat order metrics and lifetime value.

These queries leverage the same database helper functions and SQL logic that are used when handling natural language queries in the chat interface.

---

## Conclusion

By following this flow:
- **User's queries** are processed through a natural language chat interface.
- **OpenAI function calling** allows for dynamic determination of request type.
- **Database helper functions** ensure consistency between test queries and production code.
- **Streamlit's UI** provides a sleek interface for both entering queries and visualizing results.

This integration ensures that all queries—from menu updates to comprehensive order analytics—are executed accurately, providing a seamless user experience with the full flow of the application.

---

Happy Managing!

## Code Organization

The AI Menu Updater codebase is organized into a modular, service-oriented architecture for better maintainability and testability:

### Core Modules

- `app/` - Contains the Streamlit application code and core services
  - `app/components/` - UI components
  - `app/services/` - Service modules (database, prompt generation, queries)
  - `app/utils/` - Application-specific utilities

- `core/` - Core domain logic
  - Query paths and menu operations

- `utils/` - Shared utility functions
  - Database connections
  - Text processing
  - Logging utilities

- `prompts/` - Prompt templates and examples
  - OpenAI prompt templates
  - Google Gemini prompt templates
  - Example queries

### Key Service Modules

- **Prompt Service** (`app/services/prompt_service.py`): Centralizes all prompt generation for different LLM providers
- **Query Service** (`app/services/query_service.py`): Handles query categorization and routing to the appropriate processing path
- **Database Service** (`app/services/database.py`): Manages database connections and query execution
- **LangChain Service** (`app/services/langchain_service.py`): Provides LangChain integration for complex queries

### Entry Points

- `run_app.py` - Main entry point for running the Streamlit application
- `test_integration.py` - Integration test for verifying full application functionality

### Testing Structure

- `tests/` - Test modules
  - Unit tests for individual components
  - Integration tests for full application flows

## Deployment

