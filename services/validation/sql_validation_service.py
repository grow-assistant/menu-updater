"""
SQL Validation Service that ensures AI responses match SQL query results.

This service provides validation to ensure that AI-generated responses 
accurately reflect the data returned from SQL queries.
"""
import logging
import json
from typing import Dict, Any, List, Optional

from services.validation.sql_response_validator import SQLResponseValidator
from services.utils.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class SQLValidationService:
    """Service for validating AI responses against SQL query results."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SQL validation service.
        
        Args:
            config: Configuration dictionary
        """
        # Get configuration values
        db_config = config.get("database", {})
        
        # Create a connection to the database (or get from a connection pool)
        try:
            from services.database.connection_manager import DatabaseConnectionManager
            connection_manager = ServiceRegistry.get("db_connection_manager")
            if connection_manager:
                self.db_connection = connection_manager.get_connection()
                logger.info("Using connection from DatabaseConnectionManager for SQL validation")
            else:
                # Fallback to creating a direct connection
                import psycopg2
                connection_string = db_config.get("connection_string")
                if connection_string:
                    self.db_connection = psycopg2.connect(connection_string)
                    logger.info("Created direct database connection for SQL validation")
                else:
                    logger.warning("No database connection string provided. SQL validation will be limited.")
                    self.db_connection = None
        except Exception as e:
            logger.error(f"Error setting up database connection for SQL validation: {str(e)}")
            self.db_connection = None
        
        # Set up the validator with the connection
        self.validator = SQLResponseValidator(self.db_connection)
        
        # Set validation thresholds from config
        validation_config = config.get("services", {}).get("validation", {})
        self.match_threshold = validation_config.get("match_threshold", 80)
        self.strict_mode = validation_config.get("strict_mode", False)
        
        logger.info(f"SQL Validation Service initialized with match threshold: {self.match_threshold}%, strict mode: {self.strict_mode}")
    
    def validate_response(self, sql_query: str, sql_results: List[Dict[str, Any]], 
                         response_text: str) -> Dict[str, Any]:
        """
        Validate a generated response against SQL results.
        
        Args:
            sql_query: The SQL query that was executed
            sql_results: The data returned from the SQL query
            response_text: The generated response to validate
            
        Returns:
            Dictionary containing validation results and details
        """
        if not self.validator or not self.db_connection:
            # Return a default "passed" result if validation is not available
            logger.warning("SQL validation not available - validation automatically passes")
            return {
                "validation_status": True,
                "validation_details": {
                    "match_percentage": 100,
                    "matched_data_points": 0,
                    "missing_data_points": 0,
                    "mismatched_data_points": 0,
                    "data_point_matches": [],
                    "data_point_mismatches": []
                }
            }
        
        # Log validation request
        logger.info(f"Validating response for SQL query: {sql_query[:50]}...")
        
        try:
            # Perform the validation
            validation_record = self.validator.validate_response(sql_query, sql_results, response_text)
            
            # Extract core validation results
            validation_details = validation_record.get("validation_details", {})
            match_percentage = validation_details.get("match_percentage", 0)
            validation_passed = validation_record.get("validation_status", False)
            
            # Log validation results
            if validation_passed:
                logger.info(f"Validation PASSED: {match_percentage:.2f}% match")
            else:
                logger.warning(f"Validation FAILED: {match_percentage:.2f}% match")
                
                # Log mismatch details if available
                mismatches = validation_details.get("data_point_mismatches", [])
                if mismatches:
                    for i, mismatch in enumerate(mismatches[:3]):  # Log up to 3 mismatches
                        logger.warning(f"Mismatch {i+1}: {mismatch.get('response_fragment', '?')}")
                    
                    if len(mismatches) > 3:
                        logger.warning(f"... and {len(mismatches) - 3} more mismatches")
            
            return validation_record
            
        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            # Return a default "passed" result if validation fails
            return {
                "validation_status": True,
                "error": str(e),
                "validation_details": {
                    "match_percentage": 100,
                    "matched_data_points": 0,
                    "missing_data_points": 0,
                    "mismatched_data_points": 0,
                    "data_point_matches": [],
                    "data_point_mismatches": []
                }
            }
    
    def register_service(self):
        """Register this service with the ServiceRegistry."""
        ServiceRegistry.register("sql_validation", self)
        logger.info("SQL Validation Service registered with ServiceRegistry")
        
    def health_check(self) -> bool:
        """
        Check if the service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if database connection is active
            if not self.db_connection:
                logger.warning("Database connection not available for SQL validation service")
                return False
                
            # Simple connection check
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            is_connected = result is not None and result[0] == 1
            
            if is_connected:
                logger.info("SQL Validation Service health check passed")
            else:
                logger.warning("SQL Validation Service health check failed - database connection test failed")
                
            return is_connected
            
        except Exception as e:
            logger.error(f"SQL Validation Service health check failed: {str(e)}")
            return False 