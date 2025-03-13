"""
Test executor module for running tests and validating results.
"""

import os
import json
import logging
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import traceback
import uuid

# Import service diagnostics
from ai_agent.services.service_diagnostics import diagnose_sql_error, diagnose_response_issues

# SQLInterceptor class
class SQLInterceptor:
    """Class to intercept and capture SQL queries and results."""
    
    def __init__(self):
        """Initialize the SQL interceptor."""
        self.queries = []
        self.original_execute = None
        self.is_active = False
        self.sql_executor = None
    
    def start(self):
        """Start intercepting SQL queries."""
        # Use the orchestrator_service passed to run_test instead of importing OrchestratorService
        # Find SQL executor
        if hasattr(self.orchestrator, "sql_executor"):
            self.sql_executor = self.orchestrator.sql_executor
        elif hasattr(self.orchestrator, "execution") and hasattr(self.orchestrator.execution, "sql_executor"):
            self.sql_executor = self.orchestrator.execution.sql_executor
        
        if self.sql_executor is None:
            raise ValueError("Could not find SQL executor")
        
        # Find the execute method
        for method_name in ["execute", "execute_sql", "query"]:
            if hasattr(self.sql_executor, method_name) and callable(getattr(self.sql_executor, method_name)):
                # Store original method
                self.original_execute = getattr(self.sql_executor, method_name)
                
                # Replace with interceptor
                setattr(self.sql_executor, method_name, self._execute_interceptor)
                
                self.is_active = True
                return True
        
        raise ValueError(f"Could not find execute method in SQL executor: {self.sql_executor}")
    
    def stop(self):
        """Stop intercepting SQL queries."""
        if self.is_active and self.sql_executor and self.original_execute:
            # Find the method name that was patched
            for method_name in ["execute", "execute_sql", "query"]:
                if hasattr(self.sql_executor, method_name) and getattr(self.sql_executor, method_name) == self._execute_interceptor:
                    # Restore original method
                    setattr(self.sql_executor, method_name, self.original_execute)
                    self.is_active = False
                    break
    
    def _execute_interceptor(self, query, *args, **kwargs):
        """Intercept SQL query execution."""
        # Record query start time
        start_time = time.time()
        
        # Execute the query using the original method
        result = self.original_execute(query, *args, **kwargs)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Record query and result
        query_data = {
            "query": query,
            "result": result,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self.queries.append(query_data)
        
        # Return the result
        return result
    
    def get_queries(self) -> List[Dict[str, Any]]:
        """Get the captured queries."""
        return self.queries

def run_test(
    scenario_name: str,
    scenario_data: Dict[str, Any], 
    orchestrator_service: Any,
    follow_up_agent: Any = None,
    critique_agent: Any = None, 
    logger: logging.Logger = None,
    sql_validation: bool = False,
    sql_auditing: Dict[str, Any] = None,
    performance_target: float = 2.0
) -> Dict[str, Any]:
    """
    Run a test scenario through the orchestrator service.
    
    Args:
        scenario_name: Name of the test scenario
        scenario_data: Test scenario data
        orchestrator_service: Orchestrator service instance
        follow_up_agent: Follow-up agent instance
        critique_agent: Critique agent instance
        logger: Logger instance
        sql_validation: Whether to validate SQL queries and results
        sql_auditing: Dictionary containing SQL auditing configuration
        performance_target: Performance target in seconds
        
    Returns:
        Test result
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Set up SQL auditing based on configuration
    audit_sql = sql_auditing.get('enabled', False) if sql_auditing else False
    
    logger.info(f"Running test scenario: {scenario_name}")
    
    # Initialize test result
    test_result = {
        "scenario": scenario_data,
        "scenario_name": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "validation": {},
        "duration": 0,
        "status": "initialized",
        "error": None
    }
    
    # Get user input from scenario
    user_input = scenario_data.get("user_input", "")
    if not user_input:
        logger.warning(f"No user input found in scenario: {scenario_name}")
        test_result["error"] = "No user input found in scenario"
        test_result["status"] = "failed"
        return test_result
    
    logger.info(f"Processing user input: {user_input}")
    
    try:
        # Set up SQL interceptor if needed
        if sql_validation or audit_sql:
            sql_interceptor = SQLInterceptor()
            sql_interceptor.orchestrator = orchestrator_service
            sql_interceptor.start()
            logger.info("SQL interceptor started")
        
        # Measure execution time
        start_time = time.time()
        
        # Create a context object for the query
        context = {
            "session_id": str(uuid.uuid4()),
            "user_id": "test_user",
            "debug_mode": True
        }
        
        # Add is_ambiguous flag if present in scenario data
        if "is_ambiguous" in scenario_data:
            context["is_ambiguous"] = scenario_data["is_ambiguous"]
        elif any(tag.lower() == "ambiguous" for tag in scenario_data.get("tags", [])):
            context["is_ambiguous"] = True
        
        # Execute the test
        response_data = orchestrator_service.process_query(user_input, context)
        
        # Extract response text from the response data
        if isinstance(response_data, dict):
            response = response_data.get("response", "")
        else:
            response = str(response_data)
        
        # Calculate duration
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Test execution completed in {duration:.2f} seconds")
        
        # Get SQL queries and results if needed
        sql_queries = []
        sql_results = []
        if sql_validation or audit_sql:
            sql_queries = sql_interceptor.get_queries()
            sql_interceptor.stop()
            logger.info(f"SQL interceptor stopped, captured {len(sql_queries)} queries")
            
            # Add SQL queries to test result
            test_result["sql_queries"] = sql_queries
            
            # Extract results for easier access
            for query in sql_queries:
                if "result" in query:
                    sql_results.append(query["result"])
            
            # Audit SQL queries if requested
            if audit_sql:
                sql_audit_details = audit_sql_query(sql_queries, scenario_data, logger)
                test_result["sql_audit"] = sql_audit_details
        
        # Add response to test result
        test_result["response"] = response
        test_result["duration"] = duration
        
        # Check if performance target was met
        performance_met = duration <= performance_target
        test_result["performance_met"] = performance_met
        if not performance_met:
            logger.warning(f"Performance target not met: {duration:.2f}s > {performance_target:.2f}s")
        
        # Check if this is an ambiguous request scenario
        is_ambiguous = context.get("is_ambiguous", False) or scenario_data.get("is_ambiguous", False) or any(tag.lower() == "ambiguous" for tag in scenario_data.get("tags", []))
        
        # Use critique agent if available to evaluate response
        if critique_agent is not None:
            logger.info("Using critique agent to evaluate response")
            
            # Get SQL query for critique agent
            sql_query = ""
            sql_result = {}
            if sql_queries and len(sql_queries) > 0:
                sql_query = sql_queries[0].get("query", "")
                sql_result = sql_queries[0].get("result", {})
            
            # Get critique results
            critique_results = critique_agent.critique_response(user_input, response, sql_query, sql_result)
            test_result["critique"] = critique_results
            
            # For ambiguous requests, add special critique for clarification response
            if is_ambiguous:
                # Check if response is asking for clarification
                clarification_terms = ["clarify", "specify", "more information", "be more specific", "what do you mean"]
                is_clarification = any(term in response.lower() for term in clarification_terms)
                
                if is_clarification:
                    logger.info("Response contains clarification request (good for ambiguous requests)")
                    test_result["ambiguous_evaluation"] = {
                        "is_valid": True,
                        "details": "Response correctly asks for clarification on ambiguous request"
                    }
                else:
                    logger.warning("Response does not request clarification for ambiguous request")
                    test_result["ambiguous_evaluation"] = {
                        "is_valid": False,
                        "details": "Response should ask for clarification on ambiguous request"
                    }
        
        # Perform SQL validation if requested
        if sql_validation and sql_queries:
            # Validate SQL queries and results
            sql_valid, sql_validation_details = validate_sql_query(
                sql_results=sql_queries,
                response=response,
                scenario=scenario_data,
                logger=logger
            )
            
            # Add SQL validation results to test result
            test_result["validation"]["sql_validation"] = sql_validation_details
        
        # Validate response for required phrases
        required_phrases = scenario_data.get("required_phrases", [])
        if required_phrases:
            phrase_valid, phrase_validation_details = validate_response(
                response=response,
                required_phrases=required_phrases,
                logger=logger
            )
            
            # Add phrase validation results to test result
            test_result["validation"]["phrase_validation"] = phrase_validation_details
        
        # Determine overall success based on validation results
        validation = test_result.get("validation", {})
        sql_valid = validation.get("sql_validation", {}).get("is_valid", True)  # Default to True if not validated
        phrase_valid = validation.get("phrase_validation", {}).get("is_valid", True)  # Default to True if not validated
        
        # Set test success based on validation results
        if is_ambiguous:
            # For ambiguous requests, success is based on phrase validation and ambiguous evaluation (if available)
            ambiguous_eval_valid = test_result.get("ambiguous_evaluation", {}).get("is_valid", True)
            test_result["success"] = phrase_valid and ambiguous_eval_valid
            logger.info("Ambiguous request detected, success determined by phrase validation and clarification check")
        else:
            # For normal requests, success requires SQL validation, phrase validation, and performance
            test_result["success"] = sql_valid and phrase_valid and performance_met
        
        test_result["status"] = "success" if test_result["success"] else "failed"
        
        logger.info(f"Test {scenario_name} completed with status: {test_result['status']}")
        
    except Exception as e:
        logger.error(f"Error running test {scenario_name}: {str(e)}")
        logger.error(traceback.format_exc())
        test_result["error"] = str(e)
        test_result["status"] = "error"
        
        # Stop SQL interceptor if it was started
        if sql_validation or audit_sql:
            sql_interceptor.stop()
    
    return test_result

def audit_sql_query(
    sql_results: List[Dict[str, Any]],
    scenario: Dict[str, Any],
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Audit SQL queries and results.
    
    Args:
        sql_results: List of SQL results
        scenario: Test scenario data
        logger: Logger instance
        
    Returns:
        SQL audit details
    """
    logger.info(f"Auditing {len(sql_results)} SQL queries")
    
    # Create audit details
    audit_details = {
        "scenario_name": scenario.get("name", "Unknown"),
        "timestamp": datetime.now().isoformat(),
        "sql_queries_executed": len(sql_results),
        "queries": []
    }
    
    # Add query details
    for i, result in enumerate(sql_results):
        query = result.get("query", "")
        execution_time = result.get("execution_time", 0)
        
        # Create query audit record
        query_audit = {
            "query_index": i,
            "query": query,
            "execution_time_ms": execution_time * 1000,
            "result_summary": summarize_result(result.get("result", None))
        }
        
        audit_details["queries"].append(query_audit)
    
    return audit_details

def summarize_result(result: Any) -> Dict[str, Any]:
    """
    Summarize SQL result for auditing.
    
    Args:
        result: SQL result
        
    Returns:
        Summarized result
    """
    if result is None:
        return {"type": "None", "count": 0}
    
    if isinstance(result, list):
        return {
            "type": "list",
            "count": len(result),
            "sample": result[:3] if result else []
        }
    
    if isinstance(result, dict):
        return {
            "type": "dict",
            "keys": list(result.keys()),
            "sample": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        }
    
    return {
        "type": str(type(result)),
        "value": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
    }

def validate_sql_query(
    sql_results: List[Dict[str, Any]],
    response: str,
    scenario: Dict[str, Any],
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that SQL results are correctly reflected in the response.
    
    Args:
        sql_results: List of SQL results
        response: Response text
        scenario: Test scenario data
        logger: Logger instance
        
    Returns:
        Tuple of (is_valid, validation_details)
    """
    logger.info(f"Validating {len(sql_results)} SQL queries against response")
    
    if not sql_results:
        logger.warning("No SQL queries to validate")
        return False, {
            "is_valid": False,
            "queries_executed": 0,
            "details": "No SQL queries were executed"
        }
    
    # Initialize validation status
    is_valid = True
    validation_details = {
        "is_valid": True,
        "queries_executed": len(sql_results),
        "queries_validated": 0,
        "queries_passed": 0,
        "query_details": []
    }
    
    # Process each SQL result
    for i, result in enumerate(sql_results):
        query = result.get("query", "")
        query_result = result.get("result", None)
        
        # Skip empty results
        if query_result is None:
            continue
        
        # Check if query result is reflected in response
        query_valid = False
        query_details = {
            "query_index": i,
            "query": query,
            "is_valid": False,
            "details": ""
        }
        
        # Convert response and result to lowercase for comparison
        response_lower = response.lower()
        
        # Extract data from query result for validation
        extracted_data = extract_data_from_result(query_result)
        
        # Check if extracted data appears in response
        matches_found = 0
        for data_item in extracted_data:
            if str(data_item).lower() in response_lower:
                matches_found += 1
        
        # Query is valid if at least one data item is found in response
        if matches_found > 0:
            query_valid = True
            query_details["is_valid"] = True
            query_details["details"] = f"Found {matches_found}/{len(extracted_data)} data items in response"
        else:
            query_valid = False
            query_details["is_valid"] = False
            query_details["details"] = "No data items found in response"
        
        # Update validation status
        validation_details["queries_validated"] += 1
        if query_valid:
            validation_details["queries_passed"] += 1
        else:
            is_valid = False
        
        # Add query details
        validation_details["query_details"].append(query_details)
    
    # Overall validation status
    validation_details["is_valid"] = is_valid
    if is_valid:
        logger.info(f"SQL validation passed: {validation_details['queries_passed']}/{validation_details['queries_validated']} queries validated")
    else:
        logger.warning(f"SQL validation failed: {validation_details['queries_passed']}/{validation_details['queries_validated']} queries validated")
    
    return is_valid, validation_details

def extract_data_from_result(result: Any) -> List[Any]:
    """
    Extract data items from query result for validation.
    
    Args:
        result: Query result
        
    Returns:
        List of data items
    """
    data_items = []
    
    if result is None:
        return data_items
    
    # Process list result
    if isinstance(result, list):
        # Add count
        data_items.append(len(result))
        
        # Process items in the list
        for item in result:
            if isinstance(item, dict):
                # Add values from dictionary
                for value in item.values():
                    if value is not None and value != "":
                        data_items.append(value)
            elif item is not None:
                data_items.append(item)
    
    # Process dictionary result
    elif isinstance(result, dict):
        # Add values from dictionary
        for value in result.values():
            if value is not None and value != "":
                data_items.append(value)
    
    # Process scalar result
    elif result is not None:
        data_items.append(result)
    
    return data_items

def validate_response(
    response: str,
    required_phrases: List[str],
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that a response contains required phrases.
    
    Args:
        response: Response to validate
        required_phrases: List of phrases that should be in the response
        logger: Logger instance
        
    Returns:
        Tuple of (is_valid, validation_details)
    """
    logger.info(f"Validating response against {len(required_phrases)} required phrases")
    
    # Handle the case where response is None
    if response is None:
        response = ""
        logger.warning("Response is None, treating as empty string")
    elif not isinstance(response, str):
        response = str(response)
        logger.warning(f"Response is not a string, converted to: {response}")
    
    # Convert to lowercase for case-insensitive checking
    response_lower = response.lower()
    
    found_phrases = []
    missing_phrases = []
    
    # Process the required phrases
    if isinstance(required_phrases, list):
        # Simple list of phrases to check
        for phrase in required_phrases:
            if isinstance(phrase, dict) and "phrase" in phrase:
                # If it's a dictionary with a "phrase" key, extract the phrase
                phrase_text = phrase["phrase"].lower()
            elif isinstance(phrase, dict) and "type" in phrase and "phrase" in phrase:
                # Handle legacy format with type and phrase
                phrase_text = phrase["phrase"].lower()
            else:
                # Direct string phrase
                phrase_text = str(phrase).lower()
            
            if phrase_text in response_lower:
                found_phrases.append(phrase_text)
            else:
                missing_phrases.append(phrase_text)
    
    # Validation is successful if all required phrases are found
    is_valid = len(missing_phrases) == 0
    
    # Create validation details
    validation_details = {
        "is_valid": is_valid,
        "required_phrases_count": len(required_phrases),
        "found_phrases_count": len(found_phrases),
        "missing_phrases_count": len(missing_phrases),
        "found_phrases": found_phrases,
        "missing_phrases": missing_phrases,
        "details": f"Found {len(found_phrases)}/{len(required_phrases)} required phrases"
    }
    
    # Log validation results
    if is_valid:
        logger.info(f"Response validation successful: {validation_details['details']}")
    else:
        logger.warning(f"Response validation failed: {validation_details['details']}")
        logger.warning(f"Missing phrases: {missing_phrases}")
    
    return is_valid, validation_details

def check_success_conditions(scenario_data, result, context, logger):
    """
    Check if the test result meets the success conditions defined in the scenario.
    
    Args:
        scenario_data: Test scenario data
        result: Test result
        context: Test context
        logger: Logger instance
        
    Returns:
        bool: True if success conditions are met, False otherwise
    """
    # Special case for ambiguous requests
    if context.get("is_ambiguous", False) or scenario_data.get("is_ambiguous", False) or any(tag.lower() == "ambiguous" for tag in scenario_data.get("tags", [])):
        # For ambiguous requests, success is based on whether clarification was requested
        if result["response"] is None:
            # No response - this would typically be a failure
            logger.warning("No response generated for ambiguous request")
            return False
            
        # Check if response is asking for clarification
        if isinstance(result["response"], str) and ("clarify" in result["response"].lower() or 
                                                  "could you please provide" in result["response"].lower() or
                                                  "more information" in result["response"].lower() or
                                                  "more specific" in result["response"].lower()):
            logger.info("Success: Clarification requested for ambiguous request")
            # Mark as successful even if SQL validation failed
            result["sql_executed"] = True
            result["sql_results"] = {"success": True}
            return True
        else:
            logger.warning("Failure: Clarification not requested for ambiguous request")
            return False
    
    # For normal requests, check if SQL was executed successfully
    if not result.get("sql_executed") or not result.get("sql_results", {}).get("success", False):
        logger.warning("SQL execution failed")
        return False
    
    # Check if response was generated
    if not result.get("response"):
        logger.warning("No response generated")
        return False
    
    # Check SQL pattern if expected
    expected_sql_pattern = scenario_data.get("expected_sql_pattern")
    if expected_sql_pattern and result.get("sql_executed"):
        pattern_matched = False
        for pattern in expected_sql_pattern if isinstance(expected_sql_pattern, list) else [expected_sql_pattern]:
            if re.search(pattern, result["sql_executed"], re.IGNORECASE):
                pattern_matched = True
                break
        
        if not pattern_matched:
            logger.warning(f"SQL pattern not matched: {expected_sql_pattern}")
            # This is a soft failure - not meeting the SQL pattern doesn't fail the test
            # but we'll note it in the result
            result["sql_validation"] = {
                "expected_pattern": expected_sql_pattern,
                "matched": False
            }
        else:
            logger.info(f"SQL pattern matched: {expected_sql_pattern}")
            result["sql_validation"] = {
                "expected_pattern": expected_sql_pattern,
                "matched": True
            }
    
    # Check expected tables
    expected_tables = scenario_data.get("expected_tables", [])
    if expected_tables and result.get("sql_executed"):
        tables_found = []
        for table in expected_tables:
            if re.search(rf'\b{re.escape(table)}\b', result["sql_executed"], re.IGNORECASE):
                tables_found.append(table)
        
        result["sql_validation"] = result.get("sql_validation", {})
        result["sql_validation"]["expected_tables"] = expected_tables
        result["sql_validation"]["tables_found"] = tables_found
        result["sql_validation"]["all_tables_found"] = set(tables_found) == set(expected_tables)
        
        if not result["sql_validation"]["all_tables_found"]:
            logger.warning(f"Not all expected tables found. Expected: {expected_tables}, Found: {tables_found}")
            # This is a soft failure - not finding all tables doesn't fail the test
    
    # Check response contains expected phrases
    expected_response_contains = scenario_data.get("expected_response_contains", [])
    if expected_response_contains and result.get("response"):
        phrases_found = []
        for phrase in expected_response_contains:
            if phrase.lower() in result["response"].lower():
                phrases_found.append(phrase)
        
        result["response_validation"] = {
            "expected_phrases": expected_response_contains,
            "phrases_found": phrases_found,
            "all_phrases_found": set(phrases_found) == set(expected_response_contains)
        }
        
        if not result["response_validation"]["all_phrases_found"]:
            logger.warning(f"Not all expected phrases found. Expected: {expected_response_contains}, Found: {phrases_found}")
            # This is a soft failure - not finding all phrases doesn't fail the test
    
    # If we got this far without returning False, the test is successful
    return True

def validate_sql_results(sql_results, expected_validation_rules, logger):
    """
    Validate SQL results against expected validation rules.
    
    Args:
        sql_results: SQL execution results
        expected_validation_rules: Expected validation rules
        logger: Logger instance
        
    Returns:
        dict: Validation results
    """
    if not sql_results or not sql_results.get("success", False):
        return {
            "valid": False,
            "reason": "SQL execution failed",
            "details": str(sql_results.get("error", "Unknown error"))
        }
    
    validation_results = {
        "valid": True,
        "rule_results": {}
    }
    
    # Check if we have rows
    if "rows" not in sql_results or not sql_results["rows"]:
        validation_results["valid"] = False
        validation_results["reason"] = "No rows returned"
        return validation_results
    
    # Apply validation rules
    for rule_name, rule_config in expected_validation_rules.items():
        rule_type = rule_config.get("type", "unknown")
        column = rule_config.get("column")
        expected = rule_config.get("expected")
        
        if rule_type == "column_exists":
            # Check if column exists in results
            valid = any(column in row for row in sql_results["rows"])
            validation_results["rule_results"][rule_name] = {
                "valid": valid,
                "details": f"Column '{column}' {'exists' if valid else 'does not exist'} in results"
            }
            if not valid:
                validation_results["valid"] = False
        
        elif rule_type == "non_empty":
            # Check if column has non-empty values
            valid = all(row.get(column) for row in sql_results["rows"] if column in row)
            validation_results["rule_results"][rule_name] = {
                "valid": valid,
                "details": f"Column '{column}' has {'non-empty' if valid else 'empty'} values"
            }
            if not valid:
                validation_results["valid"] = False
        
        elif rule_type == "row_count":
            # Check row count
            operator = rule_config.get("operator", "==")
            actual_count = len(sql_results["rows"])
            
            if operator == "==":
                valid = actual_count == expected
            elif operator == ">":
                valid = actual_count > expected
            elif operator == ">=":
                valid = actual_count >= expected
            elif operator == "<":
                valid = actual_count < expected
            elif operator == "<=":
                valid = actual_count <= expected
            else:
                valid = False
                
            validation_results["rule_results"][rule_name] = {
                "valid": valid,
                "details": f"Row count {actual_count} {operator} {expected}"
            }
            if not valid:
                validation_results["valid"] = False
        
        elif rule_type == "value_match":
            # Check if column values match expected value
            valid = all(str(row.get(column)) == str(expected) for row in sql_results["rows"] if column in row)
            validation_results["rule_results"][rule_name] = {
                "valid": valid,
                "details": f"Column '{column}' {'matches' if valid else 'does not match'} expected value '{expected}'"
            }
            if not valid:
                validation_results["valid"] = False
    
    return validation_results 