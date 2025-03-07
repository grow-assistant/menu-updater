# Swoop AI - Restaurant Management Assistant

A powerful AI assistant for restaurant managers to analyze data, manage menus, and answer business questions through a conversational interface.

## Features

- **Natural Language Queries**: Ask questions about your restaurant data in plain English
- **Menu Management**: Update menu items, prices, and availability through conversation
- **Performance Analysis**: Get insights into sales, popular items, and customer preferences
- **Voice Interaction**: Interact with the assistant through both text and voice
- **Multiple Locations**: Support for managing multiple restaurant locations
- **Customizable Personas**: Choose from different assistant personalities

## Architecture

This application uses a microservices architecture with the following components:

- **Classification Service**: Determines the type and intent of user queries
- **Rules Service**: Manages business rules and constraints
- **SQL Generator**: Creates optimized SQL queries based on natural language
- **Execution Service**: Runs SQL against the database and processes results
- **Response Service**: Generates natural language responses from query results
- **Orchestrator**: Coordinates the flow between services
- **Frontend**: Streamlit-based user interface

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL database with restaurant data
- API keys for OpenAI, Google Gemini, and ElevenLabs (optional for voice)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-username/swoop-ai.git
   cd swoop-ai
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration:
   ```
   # API Keys
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_gemini_key
   ELEVENLABS_API_KEY=your_elevenlabs_key

   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=restaurant_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   # Default Settings
   DEFAULT_LOCATION_ID=62
   DEFAULT_PERSONA=casual
   ```

## Usage

### Running the Application

Start the Streamlit application:

```
streamlit run main.py
```

Or run directly with Python:

```
python main.py
```

The application will be available at http://localhost:8501 in your web browser.

### Using the Assistant

1. **Select a restaurant location** from the dropdown in the sidebar
2. **Choose a persona** for the AI assistant's tone and personality
3. **Enable or disable voice** responses as needed
4. **Type your question** in the input box and press Enter

Example queries:
- "What were our top 5 selling items last month?"
- "Change the price of the Caesar Salad to $12.99"
- "Show me the revenue from the last two weeks"
- "Disable the Spicy Chicken Sandwich"
- "What's the average order value in January?"

## Development

### Project Structure

```
swoop-ai/
├── config/                  # Configuration settings
├── frontend/                # Streamlit UI components
├── orchestrator/            # Service coordination
├── resources/               # SQL examples, patterns, UI resources
├── services/                # Core services
│   ├── classification_service/
│   ├── execution_service/
│   ├── response_service/
│   ├── rules_service/
│   ├── sql_generator/
│   └── utils/
├── logs/                    # Application logs
├── tests/                   # Test cases
├── .env                     # Environment variables
├── main.py                  # Application entry point
└── requirements.txt         # Python dependencies
```

### Running Tests

Run the test suite with pytest:

```
pytest
```

Or run specific tests:

```
pytest tests/test_classification_service.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project was built as a more maintainable and efficient alternative to the LangChain-based implementation.
- Thanks to the OpenAI, Google Gemini, and ElevenLabs teams for their powerful APIs.
