# Menu Updater

An AI-powered tool for Swoop customers to manage their restaurant menus through natural language queries and updates.

## System Overview

### Core Components

1. **Frontend (Streamlit)**
   - Interactive web interface with sidebar navigation
   - Common operations quick-access panel
   - Operation history display (last 5 operations)
   - Dark/light theme support
   - Real-time chat interface for natural language interactions

2. **Database (PostgreSQL)**
   - Hierarchical menu structure:
     ```
     Location
     └── Menu
         └── Category (with time ranges)
             └── Item
                 └── Option Group
                     └── Option Items
     ```
   - All entities include:
     - Timestamps (created_at, updated_at, deleted_at)
     - Soft deletion via 'disabled' flag
     - Sequential ordering (seq_num) where applicable

3. **AI Integration (OpenAI)**
   - Natural language understanding for menu queries
   - Context-aware responses using operation history
   - Function calling for structured operations
   - Token management and conversation history

4. **Operation Management**
   - Location-specific operation storage
   - Common queries and updates
   - Operation history tracking (50 entries)
   - Template-based query generation

### Key Features

1. **Menu Structure**
   - Multi-location support
   - Time-based menu categories
   - Hierarchical item organization
   - Flexible option configurations
   - Price and availability management

2. **Operation Types**
   - View all active menu items
   - Search items by name/category
   - View time-based menu items
   - Update item prices
   - Enable/disable items
   - Modify descriptions
   - Manage option configurations

3. **Data Storage**
   - Location Settings (JSON)
     ```json
     {
       "common_operations": {
         "queries": [...],
         "updates": [...]
       },
       "operation_history": [
         {
           "timestamp": "2025-02-20T22:07:06Z",
           "operation_type": "query",
           "operation_name": "View Menu Items",
           "query_template": "SELECT ...",
           "result_summary": "Found 15 items"
         }
       ]
     }
     ```

4. **Validation Rules**
   - Non-negative prices
   - Valid time ranges (0-2359)
   - Required relationships maintained
   - Soft deletion preferred
   - Option constraints enforced

## Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/grow-assistant/menu-updater.git
   cd menu-updater
   ```

2. **Set Up Python Environment:**
   - Use Python 3.8 or higher
   - Create and activate a virtual environment (recommended)

3. **Set Up PostgreSQL:**
   - Install PostgreSQL
   - Create a new database for the project

4. **Configure Environment Variables:**
   Create a `.env` file with:
   ```
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
   The app will be available at http://localhost:8501

## Database Schema

### Key Tables

1. **locations**
   - id, name, description, timezone
   - settings (JSON for operations/history)
   - tax_rate, active/disabled flags

2. **menus**
   - id, name, description, location_id
   - disabled flag

3. **categories**
   - id, name, description, menu_id
   - start_time/end_time for availability
   - seq_num for ordering
   - disabled flag

4. **items**
   - id, name, description, price
   - category_id, seq_num
   - disabled flag

5. **options**
   - id, name, description
   - min/max selections
   - item_id, disabled flag

6. **option_items**
   - id, name, description, price
   - option_id, disabled flag

---

