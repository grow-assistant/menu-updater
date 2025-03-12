"""
SQL Response Validator service.

This service validates AI-generated responses against SQL query results
to ensure factual accuracy and consistency.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class SQLResponseValidator:
    """Service to validate AI responses against SQL result data."""
    
    def __init__(self, db_connection):
        """
        Initialize the validator with a database connection.
        
        Args:
            db_connection: Database connection for validation logging
        """
        self.db_connection = db_connection
        self.logger = logging.getLogger(__name__)
        
    def validate_response(self, sql_query: str, sql_results: List[Dict[str, Any]], 
                          response_text: str) -> Dict[str, Any]:
        """
        Validate that a response accurately reflects the SQL results.
        
        Args:
            sql_query: The SQL query that was executed
            sql_results: The data returned from the SQL query
            response_text: The generated response to validate
            
        Returns:
            Dict containing validation results and details
        """
        validation_id = str(uuid.uuid4())
        
        # Extract facts from SQL results
        sql_facts = self._extract_facts_from_sql_results(sql_results)
        
        # Extract claims from response
        response_claims = self._extract_claims_from_response(response_text)
        
        # Map claims to facts
        matches, mismatches = self._map_claims_to_facts(response_claims, sql_facts)
        
        # Calculate match percentage
        total_claims = len(response_claims) if response_claims else 1
        match_percentage = len(matches) / total_claims * 100
        
        # Determine if validation passed
        validation_passed = match_percentage >= 90 and len(mismatches) == 0
        
        # Create validation record
        validation_record = {
            "validation_id": validation_id,
            "timestamp": datetime.now().isoformat(),
            "sql_query": sql_query,
            "sql_results": sql_results,
            "response_text": response_text,
            "validation_status": validation_passed,
            "validation_details": {
                "matched_data_points": len(matches),
                "missing_data_points": total_claims - len(matches),
                "mismatched_data_points": len(mismatches),
                "match_percentage": match_percentage,
                "data_point_matches": matches,
                "data_point_mismatches": mismatches
            }
        }
        
        # Store validation results
        self._store_validation_record(validation_record)
        
        # Log validation results
        self._log_validation_results(validation_record)
        
        return validation_record
    
    def _extract_facts_from_sql_results(self, sql_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract factual data points from SQL results."""
        facts = []
        
        if not sql_results or not isinstance(sql_results, list):
            return facts
            
        for row in sql_results:
            for column, value in row.items():
                facts.append({
                    "type": "sql_fact",
                    "column": column,
                    "value": value,
                    "source_row": row
                })
                
        return facts
    
    def _extract_claims_from_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract factual claims from response text using NLP."""
        claims = []
        
        # Simple extraction logic
        # In a real implementation, this would use more sophisticated NLP techniques
        sentences = response_text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Identify claims with numerical values
            if "$" in sentence or "%" in sentence or any(char.isdigit() for char in sentence):
                claims.append({
                    "type": "numerical_claim",
                    "text": sentence,
                    "contains_number": True
                })
            # Identify claims about menu items or orders
            elif any(word in sentence.lower() for word in ["menu", "item", "order", "price", "burger", "salad", "pizza"]):
                claims.append({
                    "type": "factual_claim",
                    "text": sentence,
                    "domain": "menu_or_order"
                })
            # General claims
            elif len(sentence.split()) > 3:  # Only consider substantial sentences
                claims.append({
                    "type": "general_claim",
                    "text": sentence
                })
                
        return claims
    
    def _map_claims_to_facts(self, claims: List[Dict[str, Any]], 
                             facts: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Map response claims to SQL facts.
        
        Args:
            claims: List of claims extracted from the response
            facts: List of facts extracted from SQL results
            
        Returns:
            Tuple of (matches, mismatches)
        """
        matches = []
        mismatches = []
        
        for claim in claims:
            claim_text = claim["text"].lower()
            matched = False
            
            for fact in facts:
                fact_value = str(fact["value"]).lower()
                if fact_value in claim_text:
                    matches.append({
                        "response_fragment": claim["text"],
                        "sql_data": fact,
                        "matched": True
                    })
                    matched = True
                    break
                    
            if not matched:
                mismatches.append({
                    "response_fragment": claim["text"],
                    "matched": False,
                    "reason": "No matching fact found in SQL results"
                })
                
        return matches, mismatches
    
    def _store_validation_record(self, validation_record: Dict[str, Any]) -> None:
        """
        Store validation record in database.
        
        Args:
            validation_record: The validation record to store
        """
        try:
            # Create tables if they don't exist
            self._ensure_tables_exist()
            
            # Store query log
            query_log_id = self._store_query_log(validation_record)
            
            # Store validation metrics
            self._store_validation_metrics(validation_record, query_log_id)
            
            # Store validation issues
            if validation_record["validation_details"]["data_point_mismatches"]:
                self._store_validation_issues(validation_record)
                
        except Exception as e:
            self.logger.error(f"Error storing validation record: {e}")
            # Don't re-raise the exception to avoid disrupting the main application flow
    
    def _ensure_tables_exist(self) -> None:
        """Create validation tables if they don't exist."""
        try:
            create_tables_sql = """
            CREATE TABLE IF NOT EXISTS sql_query_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(64) NOT NULL,
                query_text TEXT NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                result_count INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT
            );
            
            CREATE TABLE IF NOT EXISTS sql_query_results (
                id SERIAL PRIMARY KEY,
                query_log_id INTEGER REFERENCES sql_query_log(id),
                result_data JSONB NOT NULL,
                response_text TEXT NOT NULL,
                validation_status BOOLEAN NOT NULL,
                validation_details TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_query_log_session ON sql_query_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_query_log_timestamp ON sql_query_log(timestamp);
            
            CREATE TABLE IF NOT EXISTS sql_validation_metrics (
                validation_id VARCHAR(64) PRIMARY KEY,
                query_log_id INTEGER REFERENCES sql_query_log(id),
                response_id VARCHAR(64) NOT NULL,
                match_percentage DECIMAL(5,2) NOT NULL,
                validation_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                validation_pass BOOLEAN NOT NULL,
                critical_fields_match BOOLEAN NOT NULL,
                validator_version VARCHAR(32) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS sql_validation_issues (
                id SERIAL PRIMARY KEY,
                validation_id VARCHAR(64) REFERENCES sql_validation_metrics(validation_id),
                issue_type VARCHAR(32) NOT NULL,
                expected_value TEXT NOT NULL,
                actual_value TEXT NOT NULL,
                field_name VARCHAR(128) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                remediation_status VARCHAR(32) DEFAULT 'OPEN',
                resolved_timestamp TIMESTAMP
            );
            """
            
            # Execute the SQL to create tables
            with self.db_connection.cursor() as cursor:
                cursor.execute(create_tables_sql)
                
            self.db_connection.commit()
            self.logger.info("Validation tables created or verified")
            
        except Exception as e:
            self.logger.error(f"Error creating validation tables: {e}")
            self.db_connection.rollback()
    
    def _store_query_log(self, validation_record: Dict[str, Any]) -> int:
        """
        Store the SQL query log and return the ID.
        
        Args:
            validation_record: The validation record containing query information
            
        Returns:
            The ID of the inserted query log record
        """
        try:
            sql = """
            INSERT INTO sql_query_log 
                (timestamp, session_id, query_text, execution_time_ms, result_count, success, error_message) 
            VALUES 
                (NOW(), %s, %s, %s, %s, %s, %s)
            RETURNING id
            """
            
            # Get values from validation record
            session_id = str(uuid.uuid4())  # Generate a session ID if not available
            query_text = validation_record["sql_query"]
            execution_time_ms = int(validation_record.get("execution_time", 0) * 1000)
            result_count = len(validation_record["sql_results"])
            success = True  # Assume success since we have results
            error_message = None
            
            with self.db_connection.cursor() as cursor:
                cursor.execute(sql, (
                    session_id,
                    query_text,
                    execution_time_ms,
                    result_count,
                    success,
                    error_message
                ))
                
                # Get the ID of the inserted record
                query_log_id = cursor.fetchone()[0]
                
            self.db_connection.commit()
            return query_log_id
            
        except Exception as e:
            self.logger.error(f"Error storing query log: {e}")
            self.db_connection.rollback()
            return -1  # Return an invalid ID
    
    def _store_validation_metrics(self, validation_record: Dict[str, Any], query_log_id: int) -> None:
        """
        Store validation metrics in the database.
        
        Args:
            validation_record: The validation record containing metrics
            query_log_id: The ID of the related query log record
        """
        try:
            sql = """
            INSERT INTO sql_validation_metrics 
                (validation_id, query_log_id, response_id, match_percentage, validation_pass, critical_fields_match, validator_version) 
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Generate a response ID if not available
            response_id = str(uuid.uuid4())
            
            with self.db_connection.cursor() as cursor:
                cursor.execute(sql, (
                    validation_record["validation_id"],
                    query_log_id,
                    response_id,
                    validation_record["validation_details"]["match_percentage"],
                    validation_record["validation_status"],
                    True,  # critical_fields_match (simplified for this implementation)
                    "1.0"  # validator_version
                ))
                
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error storing validation metrics: {e}")
            self.db_connection.rollback()
    
    def _store_validation_issues(self, validation_record: Dict[str, Any]) -> None:
        """
        Store validation issues in the database.
        
        Args:
            validation_record: The validation record containing issues
        """
        try:
            sql = """
            INSERT INTO sql_validation_issues
                (validation_id, issue_type, expected_value, actual_value, field_name, severity)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            """
            
            # Insert each mismatch as an issue
            with self.db_connection.cursor() as cursor:
                for mismatch in validation_record["validation_details"]["data_point_mismatches"]:
                    cursor.execute(sql, (
                        validation_record["validation_id"],
                        "mismatch",
                        "expected_value_placeholder",  # Would extract from mismatch in a real implementation
                        mismatch["response_fragment"],
                        "field_name_placeholder",      # Would extract from mismatch in a real implementation
                        "HIGH"                         # Default severity
                    ))
                    
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error storing validation issues: {e}")
            self.db_connection.rollback()
    
    def _log_validation_results(self, validation_record: Dict[str, Any]) -> None:
        """
        Log validation results.
        
        Args:
            validation_record: The validation record to log
        """
        match_percentage = validation_record["validation_details"]["match_percentage"]
        matched_points = validation_record["validation_details"]["matched_data_points"]
        missing_points = validation_record["validation_details"]["missing_data_points"]
        mismatched_points = validation_record["validation_details"]["mismatched_data_points"]
        
        if validation_record["validation_status"]:
            self.logger.info(
                f"Validation PASSED: {match_percentage:.2f}% match "
                f"({matched_points} matched, {missing_points} missing)"
            )
        else:
            self.logger.warning(
                f"Validation FAILED: {match_percentage:.2f}% match "
                f"({matched_points} matched, {missing_points} missing, "
                f"{mismatched_points} mismatched)"
            ) 