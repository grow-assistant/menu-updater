"""
Unit tests for the enhanced GeminiSQLGenerator.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import time

from services.sql_generator.gemini_sql_generator import GeminiSQLGenerator
from services.utils.service_registry import ServiceRegistry

@pytest.fixture
def mock_config():
    """Fixture for mock configuration."""
    return {
        "api": {
            "gemini": {
                "api_key": "test_api_key",
                "model": "gemini-2.0-flash",
                "temperature": 0.2,
                "max_tokens": 1024
            }
        },
        "services": {
            "sql_generator": {
                "prompt_template": "resources/prompts/sql_generator.txt",
                "validation_prompt": "resources/prompts/sql_validator.txt",
                "optimization_prompt": "resources/prompts/sql_optimizer.txt",
                "enable_validation": True,
                "enable_optimization": True,
                "max_retries": 2
            }
        }
    }

@pytest.fixture
def mock_rules_service():
    """Fixture for mock RulesService."""
    rules_service = MagicMock()
    
    # Mock schema
    rules_service.get_schema_for_type.return_value = {
        "menu_items": {
            "columns": ["id", "name", "price", "category"]
        },
        "orders": {
            "columns": ["id", "customer_id", "order_date", "total"]
        }
    }
    
    # Mock patterns
    rules_service.get_sql_patterns.return_value = {
        "rules": {"max_rows": 100},
        "patterns": {
            "get_menu_items": "SELECT * FROM menu_items",
            "get_item_by_id": "SELECT * FROM menu_items WHERE id = {id}"
        }
    }
    
    # Mock format_rules_for_prompt
    rules.format_rules_for_prompt.return_value = "MAX_ROWS:\n- 100"
    
    return rules_service

@pytest.fixture
def mock_genai():
    """Fixture for mock Google GenerativeAI."""
    with patch("google.generativeai") as mock_genai:
        # Mock GenerativeModel
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock generate_content
        mock_response = MagicMock()
        mock_response.text = "SELECT * FROM menu_items WHERE category = 'Appetizers'"
        mock_model.generate_content.return_value = mock_response
        
        yield mock_genai

@pytest.fixture
def sql_generator(mock_config, mock_rules_service, mock_genai):
    """Fixture for GeminiSQLGenerator with mocked dependencies."""
    # Mock open for reading prompt templates
    with patch("builtins.open", mock_open(read_data="Test prompt template {query} {examples} {schema} {rules} {patterns}")):
        # Mock ServiceRegistry
        with patch.object(ServiceRegistry, "get_service") as mock_get_service:
            mock_get_service.return_value = mock_rules_service
            
            generator = GeminiSQLGenerator(mock_config)
            return generator

class TestEnhancedSQLGenerator:
    """Tests for the enhanced GeminiSQLGenerator."""
    
    def test_initialization(self, sql_generator, mock_config):
        """Test service initialization."""
        assert sql_generator.model == mock_config["api"]["gemini"]["model"]
        assert sql_generator.temperature == mock_config["api"]["gemini"]["temperature"]
        assert sql_generator.max_tokens == mock_config["api"]["gemini"]["max_tokens"]
        assert sql_generator.enable_validation == mock_config["services"]["sql_generator"]["enable_validation"]
        assert sql_generator.enable_optimization == mock_config["services"]["sql_generator"]["enable_optimization"]
    
    def test_build_prompt(self, sql_generator, mock_rules_service):
        """Test building the enhanced prompt."""
        query = "Show me all appetizers"
        examples = [{"query": "Show me all desserts", "sql": "SELECT * FROM menu_items WHERE category = 'Desserts'"}]
        context = {"query_type": "menu"}
        
        prompt = sql_generator._build_prompt(query, examples, context)
        
        # Check that the prompt contains all the expected elements
        assert query in prompt
        assert "Show me all desserts" in prompt
        assert "SELECT * FROM menu_items WHERE category = 'Desserts'" in prompt
        assert "menu_items" in prompt
        
        # Verify that the rules service was called
        mock_rules.get_schema_for_type.assert_called_with(context["query_type"])
        mock_rules.get_sql_patterns.assert_called_with(context["query_type"])
    
    def test_generate_sql_success(self, sql_generator, mock_genai):
        """Test successful SQL generation."""
        query = "Show me all appetizers"
        examples = [{"query": "Show me all desserts", "sql": "SELECT * FROM menu_items WHERE category = 'Desserts'"}]
        context = {"query_type": "menu"}
        
        # Mock validation and optimization to return the same SQL
        with patch.object(sql_generator, "_validate_sql") as mock_validate:
            mock_validate.return_value = (True, [], "SELECT * FROM menu_items WHERE category = 'Appetizers'")
            
            with patch.object(sql_generator, "_optimize_sql") as mock_optimize:
                mock_optimize.return_value = "SELECT * FROM menu_items WHERE category = 'Appetizers'"
                
                result = sql_generator.generate_sql(query, examples, context)
                
                # Check the result structure
                assert "sql" in result
                assert "generation_time" in result
                assert "attempts" in result
                assert "model" in result
                assert "timestamp" in result
                
                # Check the SQL
                assert result["sql"] == "SELECT * FROM menu_items WHERE category = 'Appetizers'"
                assert result["attempts"] == 1
                assert result["model"] == "gemini-2.0-flash"
    
    def test_generate_sql_with_validation_failure(self, sql_generator, mock_genai):
        """Test SQL generation with validation failure and retry."""
        query = "Show me all appetizers"
        examples = []
        context = {"query_type": "menu"}
        
        # Mock validation to fail on first attempt, succeed on second
        validation_results = [
            (False, ["Invalid table name"], "Invalid SQL"),
            (True, [], "SELECT * FROM menu_items WHERE category = 'Appetizers'")
        ]
        
        with patch.object(sql_generator, "_validate_sql", side_effect=validation_results):
            with patch.object(sql_generator, "_optimize_sql") as mock_optimize:
                mock_optimize.return_value = "SELECT * FROM menu_items WHERE category = 'Appetizers'"
                
                result = sql_generator.generate_sql(query, examples, context)
                
                # Check that we got the corrected SQL
                assert result["sql"] == "SELECT * FROM menu_items WHERE category = 'Appetizers'"
                assert result["attempts"] == 2
    
    def test_extract_sql_from_code_block(self, sql_generator):
        """Test extracting SQL from code blocks."""
        text = """Here's the SQL query:

```sql
SELECT * 
FROM menu_items 
WHERE category = 'Appetizers'
```

This query will return all appetizers from the menu."""

        sql = sql_generator._extract_sql(text)
        assert sql == "SELECT * \nFROM menu_items \nWHERE category = 'Appetizers'"
    
    def test_extract_sql_from_plain_text(self, sql_generator):
        """Test extracting SQL from plain text."""
        text = """SELECT * 
FROM menu_items 
WHERE category = 'Appetizers'"""

        sql = sql_generator._extract_sql(text)
        assert sql == text
    
    def test_extract_sql_adds_location_id(self, sql_generator):
        """Test that _extract_sql adds location_id filter when missing."""
        # SQL without location_id filter
        sql_without_location = """
        SELECT COUNT(*) as order_count
        FROM orders o
        WHERE o.status = 7
        """
        
        # Patch the business_rules.DEFAULT_LOCATION_ID
        with patch('services.rules.business_rules.DEFAULT_LOCATION_ID', 62):
            result = sql_generator._extract_sql(sql_without_location)
            
            # Check that the location ID filter was added
            assert "o.location_id = 62" in result
            
    def test_extract_sql_with_table_alias(self, sql_generator):
        """Test that _extract_sql adds location_id filter with correct table alias."""
        # SQL with alias but without location_id filter
        sql_with_alias = """
        SELECT COUNT(*) as order_count
        FROM orders as ord
        WHERE ord.status = 7
        """
        
        # Patch the business_rules.DEFAULT_LOCATION_ID
        with patch('services.rules.business_rules.DEFAULT_LOCATION_ID', 62):
            result = sql_generator._extract_sql(sql_with_alias)
            
            # Check that the location ID filter was added with the correct alias
            assert "ord.location_id = 62" in result
    
    def test_validate_sql(self, sql_generator, mock_genai):
        """Test SQL validation."""
        sql = "SELECT * FROM menu_items WHERE category = 'Appetizers'"
        context = {"query_type": "menu"}
        
        # Mock the validation response
        mock_model = mock_genai.GenerativeModel.return_value
        mock_response = MagicMock()
        mock_response.text = """
        - Valid: Yes
        - Issues: None
        - Corrected SQL: N/A
        """
        mock_model.generate_content.return_value = mock_response
        
        is_valid, issues, corrected_sql = sql_generator._validate_sql(sql, context)
        
        assert is_valid is True
        assert len(issues) == 0
        assert corrected_sql == sql
    
    def test_validate_sql_location_id(self, sql_generator):
        """Test that _validate_sql identifies missing location_id and adds it."""
        # SQL missing location_id filter
        sql_missing_location = """
        SELECT COUNT(*) FROM orders WHERE status = 7
        """
        
        # Patch the business_rules.DEFAULT_LOCATION_ID
        with patch('services.rules.business_rules.DEFAULT_LOCATION_ID', 62):
            is_valid, issues, corrected_sql = sql_generator._validate_sql(sql_missing_location, {})
            
            # Should add location filter but flag it as an issue
            assert "CRITICAL SECURITY ISSUE" in str(issues)
            assert "location_id = 62" in corrected_sql
            
    def test_validate_sql_with_location_id(self, sql_generator):
        """Test that _validate_sql accepts SQL with proper location_id filtering."""
        # SQL with location_id filter
        sql_with_location = """
        SELECT COUNT(*) FROM orders WHERE location_id = 62 AND status = 7
        """
        
        is_valid, issues, corrected_sql = sql_generator._validate_sql(sql_with_location, {})
        
        # Should not find any issues with location filtering
        location_issues = [issue for issue in issues if "location" in issue.lower()]
        assert len(location_issues) == 0
    
    def test_optimize_sql(self, sql_generator, mock_genai):
        """Test SQL optimization."""
        sql = "SELECT * FROM menu_items WHERE category = 'Appetizers'"
        context = {"query_type": "menu"}
        
        # Mock the optimization response
        mock_model = mock_genai.GenerativeModel.return_value
        mock_response = MagicMock()
        mock_response.text = """
        Here's the optimized query:
        
        ```sql
        SELECT id, name, price, category 
        FROM menu_items 
        WHERE category = 'Appetizers'
        ```
        
        This optimization explicitly selects only the needed columns instead of using *.
        """
        mock_model.generate_content.return_value = mock_response
        
        optimized_sql = sql_generator._optimize_sql(sql, context)
        
        assert "SELECT id, name, price, category" in optimized_sql
        assert "FROM menu_items" in optimized_sql
        assert "WHERE category = 'Appetizers'" in optimized_sql
    
    def test_health_check_success(self, sql_generator, mock_genai):
        """Test health check success."""
        mock_model = mock_genai.GenerativeModel.return_value
        mock_response = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        result = sql_generator.health_check()
        assert result is True
    
    def test_health_check_failure(self, sql_generator, mock_genai):
        """Test health check failure."""
        mock_model = mock_genai.GenerativeModel.return_value
        mock_model.generate_content.side_effect = Exception("API error")
        
        result = sql_generator.health_check()
        assert result is False 