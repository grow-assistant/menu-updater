# Restaurant Assistant

A smart AI-powered restaurant assistant that provides accurate and validated responses to customer queries.

## Features

- **Ambiguous Request Handling**: Gracefully handles ambiguous customer requests by providing clarification and guiding options
- **Typo Handling**: Intelligently recognizes and corrects typos in customer queries without explicitly pointing them out
- **Progressive Order Tracking**: Maintains context in multi-message ordering sequences
- **SQL Response Validation**: Ensures AI responses are factually accurate by validating them against SQL query results
- **Rich Media Formatting**: Formats responses with clear, readable presentation
- **Persona Support**: Adjusts tone and style based on configurable personas

## Project Structure

```
restaurant-assistant/
├── app.py                          # Main application entry point
├── config/
│   └── config.yaml                 # Application configuration
├── resources/
│   └── prompts/
│       └── templates/              # Response templates
│           ├── ambiguous_request.txt
│           ├── typo_handling.txt
│           └── progressive_order.txt
├── services/
│   ├── database/                   # Database connection services
│   ├── response/                   # Response generation services
│   │   └── response_generator.py
│   ├── utils/                      # Utility services
│   │   ├── service_registry.py     # Service locator implementation
│   │   └── service_initializer.py  # Service setup utilities
│   └── validation/                 # Validation services
│       ├── __init__.py
│       ├── sql_response_validator.py
│       └── sql_validation_service.py
└── logs/                           # Application logs
```

## SQL Validation Process

The SQL Validation Service ensures that AI-generated responses accurately reflect the data returned by SQL queries:

1. SQL query executes and returns database results
2. Response generator produces a natural language response
3. Validation service compares facts in the response against SQL results
4. Validation metrics are logged and attached to the response
5. Response is only delivered if validation passes or meets a threshold

### Validation Process Details

- **Fact Extraction**: The validator extracts factual claims from responses and maps them to SQL results
- **Matching**: Each claim is compared against the SQL data for accuracy
- **Metrics**: Match percentage, matched/missing/mismatched data points are recorded
- **Remediation**: Failed validations are logged for analysis and improvement

## Service Registry Pattern

The application uses a Service Registry pattern to manage dependencies:

1. Services register themselves with the registry
2. Components request services from the registry when needed
3. The registry handles initialization and provides a central access point

## Configuration

Configuration is stored in YAML format and supports environment variable injection:

```yaml
# Example: Override API key through environment variables
api:
  openai:
    api_key: ${OPENAI_API_KEY}
```

## Response Templates

Response templates provide structured guidance for different types of interactions:

- **Ambiguous Request**: Guide users to clarify their ambiguous queries
- **Typo Handling**: Gracefully handle and correct typos without highlighting them
- **Progressive Order**: Track context across multi-message ordering sequences

## Getting Started

1. Clone the repository
2. Set up environment variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   DB_CONNECTION_STRING=your_db_connection_string
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   python app.py
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project was built as a more maintainable and efficient alternative to the LangChain-based implementation.
- Thanks to the OpenAI, Google Gemini, and ElevenLabs teams for their powerful APIs.