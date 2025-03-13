"""
Test validator module for validating test results against requirements.

This module implements validation of test results against the requirements from the
AI Agent Development Plan, including SQL validation, response validation, and 
compliance with required phrases.
"""

import logging
import re
import json
from typing import Dict, Any, List, Tuple, Optional, Union

def validate_test_results(
    test_results: Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]],
    threshold: float,
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate test results against specified threshold.
    
    Args:
        test_results: List or dictionary of test results
        threshold: Threshold for passing rate (0.0 to 1.0)
        logger: Logger instance
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    # Process test results based on input type (list or dict)
    results_dict = {}
    if isinstance(test_results, list):
        # Convert list to dict with scenario names as keys
        for result in test_results:
            scenario_name = result.get("scenario", {}).get("name", f"scenario_{len(results_dict)}")
            results_dict[scenario_name] = result
    else:
        # Already a dictionary
        results_dict = test_results
    
    # Calculate success rates for tests, SQL validation, phrase validation
    total_tests = len(results_dict)
    if total_tests == 0:
        logger.warning("No test results found for validation")
        return False, {"is_valid": False, "message": "No test results found"}
    
    # Check overall test success
    success_count = sum(1 for result in results_dict.values() if result.get("success", False))
    test_success_rate = success_count / total_tests if total_tests > 0 else 0.0
    
    # Check SQL validation success
    sql_validation_count = 0
    sql_success_count = 0
    for result in results_dict.values():
        # Get validation information from the test result
        validation = result.get("validation", {})
        # Check if SQL validation was performed
        if "sql_validation" in validation:
            sql_validation_count += 1
            # Check if SQL validation was successful
            if validation.get("sql_validation", {}).get("is_valid", False):
                sql_success_count += 1
    
    sql_success_rate = sql_success_count / sql_validation_count if sql_validation_count > 0 else 0.0
    
    # Check phrase validation success
    phrase_validation_count = 0
    phrase_success_count = 0
    for result in results_dict.values():
        # Get validation information from the test result
        validation = result.get("validation", {})
        # Check if phrase validation was performed
        if "phrase_validation" in validation:
            phrase_validation_count += 1
            # Check if phrase validation was successful
            if validation.get("phrase_validation", {}).get("is_valid", False):
                phrase_success_count += 1
    
    phrase_success_rate = phrase_success_count / phrase_validation_count if phrase_validation_count > 0 else 0.0
    
    # Calculate overall validation status
    is_valid = (
        test_success_rate >= threshold and
        (sql_validation_count == 0 or sql_success_rate >= threshold) and
        (phrase_validation_count == 0 or phrase_success_rate >= threshold)
    )
    
    # Prepare detailed validation results
    validation_results = {
        "is_valid": is_valid,
        "threshold": threshold,
        "test_success_rate": test_success_rate,
        "test_success_percentage": test_success_rate * 100,
        "sql_success_rate": sql_success_rate,
        "sql_success_percentage": sql_success_rate * 100,
        "phrase_success_rate": phrase_success_rate,
        "phrase_success_percentage": phrase_success_rate * 100,
        "total_tests": total_tests,
        "successful_tests": success_count,
        "total_sql_validations": sql_validation_count,
        "successful_sql_validations": sql_success_count,
        "total_phrase_validations": phrase_validation_count,
        "successful_phrase_validations": phrase_success_count,
        "scenario_results": {
            name: {
                "success": result.get("success", False),
                "sql_validation": result.get("validation", {}).get("sql_validation", {}).get("is_valid", False) 
                    if "validation" in result and "sql_validation" in result.get("validation", {}) else None,
                "phrase_validation": result.get("validation", {}).get("phrase_validation", {}).get("is_valid", False)
                    if "validation" in result and "phrase_validation" in result.get("validation", {}) else None,
            }
            for name, result in results_dict.items()
        }
    }
    
    # Log validation results
    logger.info(f"Validating {total_tests} test results against threshold {threshold:.2%}")
    logger.info(f"Test Success Rate: {test_success_rate:.2%}")
    if sql_validation_count > 0:
        logger.info(f"SQL Validation Success Rate: {sql_success_rate:.2%}")
    if phrase_validation_count > 0:
        logger.info(f"Phrase Validation Success Rate: {phrase_success_rate:.2%}")
    
    if is_valid:
        logger.info(f"Validation PASSED: Success rates meet the required threshold of {threshold:.2%}")
    else:
        logger.warning(f"Validation FAILED: One or more success rates do not meet the required threshold of {threshold:.2%}")
        if test_success_rate < threshold:
            logger.warning(f"Test Success Rate {test_success_rate:.2%} < {threshold:.2%}")
        if sql_validation_count > 0 and sql_success_rate < threshold:
            logger.warning(f"SQL Validation Success Rate {sql_success_rate:.2%} < {threshold:.2%}")
        if phrase_validation_count > 0 and phrase_success_rate < threshold:
            logger.warning(f"Phrase Validation Success Rate {phrase_success_rate:.2%} < {threshold:.2%}")
    
    return is_valid, validation_results

def validate_sql_query(
    response_content: str,
    sql_query: str,
    sql_result: Dict[str, Any],
    logger: logging.Logger,
    is_ambiguous: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that the response content matches the SQL results.
    
    Args:
        response_content: Generated response text
        sql_query: SQL query text
        sql_result: SQL query result
        logger: Logger instance
        is_ambiguous: Whether the request is ambiguous, defaults to False
        
    Returns:
        Tuple of (is_valid, validation_details)
    """
    # For ambiguous requests, skip SQL validation and return success
    if is_ambiguous:
        logger.info("Skipping SQL validation for ambiguous request")
        return True, {
            "sql_query": sql_query,
            "data_points_count": 0,
            "validation_success": True,
            "missing_elements": [],
            "note": "Validation skipped for ambiguous request"
        }
    
    # Handle the case where response_content is None
    if response_content is None:
        response_content = ""
        logger.warning("Response content is None, treating as empty string")
    elif not isinstance(response_content, str):
        response_content = str(response_content)
        logger.warning(f"Response content is not a string, converted to: {response_content}")
    
    # Convert response content to lowercase for case-insensitive checks
    response_content_lower = response_content.lower()
    
    logger.info(f"Validating SQL query result for query: {sql_query}")
    
    # Handle different SQL result formats
    result_rows = []
    result_columns = []
    
    # Try to extract rows based on different possible structures
    if isinstance(sql_result, list):
        # Direct list of rows
        result_rows = sql_result
        # Try to get column names if rows are dictionaries
        if len(result_rows) > 0 and isinstance(result_rows[0], dict):
            result_columns = list(result_rows[0].keys())
    elif isinstance(sql_result, dict):
        # Dictionary with 'rows' or 'data' key
        if 'rows' in sql_result:
            result_rows = sql_result['rows']
        elif 'data' in sql_result:
            result_rows = sql_result['data']
        
        # Try to get column information
        if 'columns' in sql_result:
            result_columns = sql_result['columns']
        elif 'headers' in sql_result:
            result_columns = sql_result['headers']
    
    # If we couldn't extract rows in a standard way, log a warning
    if not result_rows and sql_result:
        logger.warning(f"Could not extract rows from SQL result: {sql_result}")
        # If we can't determine the structure, use the full result for validation
        result_rows = [sql_result]
    
    # Convert rows to string for matching in response
    row_strings = []
    
    # Extract string representations based on result structure
    for row in result_rows:
        if isinstance(row, dict):
            # For dict rows, we want key-value pairs
            row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
            row_strings.append(row_str)
        elif isinstance(row, (list, tuple)):
            # For list/tuple rows, we want comma-separated values
            row_str = ", ".join([str(v) for v in row])
            row_strings.append(row_str)
        else:
            # Fallback for simple values
            row_strings.append(str(row))
    
    # Check if the key data points from the SQL results are reflected in the response
    validation_success = True
    missing_elements = []
    
    # If no data was returned, we only need to check if the response reflects this
    if not result_rows or len(result_rows) == 0:
        no_results_phrases = ["no results", "no data", "found 0", "0 records", "empty", "no records"]
        found_no_results_phrase = False
        
        for phrase in no_results_phrases:
            if phrase in response_content_lower:
                found_no_results_phrase = True
                break
        
        if not found_no_results_phrase:
            validation_success = False
            missing_elements.append("No indication that query returned no results")
    else:
        # For each row, check if key elements are reflected in the response
        for row_str in row_strings:
            # Extract significant fragments from the row string
            significant_fragments = extract_significant_fragments(row_str)
            
            # Check if any significant fragments are missing from the response
            for fragment in significant_fragments:
                if fragment and len(fragment) > 2 and fragment not in response_content_lower:  # Skip very short fragments
                    missing_elements.append(fragment)
                    validation_success = False
    
    details = {
        "sql_query": sql_query,
        "data_points_count": len(result_rows),
        "validation_success": validation_success,
        "missing_elements": missing_elements
    }
    
    if validation_success:
        logger.info("SQL validation successful")
    else:
        logger.warning(f"SQL validation failed: {missing_elements}")
    
    return validation_success, details

def extract_significant_fragments(row_str: str) -> List[str]:
    """
    Extract meaningful fragments from a row string that should be reflected in a response.
    
    Args:
        row_str: String representation of a data row
        
    Returns:
        List of significant fragments
    """
    # Split by common separators
    fragments = re.split(r'[,;|:]', row_str)
    
    # Filter and clean fragments
    clean_fragments = []
    for fragment in fragments:
        # Clean up the fragment
        clean = fragment.strip()
        
        # Skip empty or very short fragments
        if clean and len(clean) > 2 and not clean.isdigit():
            # Remove quotes and unnecessary characters
            clean = clean.strip('"\'`')
            clean_fragments.append(clean)
    
    return clean_fragments

def validate_response(
    response: str,
    required_phrases: List[str],
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that the response contains all required phrases.
    
    Args:
        response: Response text
        required_phrases: List of required phrases
        logger: Logger instance
        
    Returns:
        Tuple of (is_valid, validation_details)
    """
    logger.info(f"Validating response against {len(required_phrases)} required phrases")
    
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

def validate_performance(
    execution_time: float,
    performance_target: float,
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that the execution time meets the performance target.
    
    Args:
        execution_time: Execution time in seconds
        performance_target: Performance target in milliseconds
        logger: Logger instance
        
    Returns:
        Tuple of (is_valid, validation_details)
    """
    # Convert execution time to milliseconds
    execution_time_ms = execution_time * 1000
    
    # Check if execution time is within target
    is_valid = execution_time_ms <= performance_target
    
    # Create validation details
    validation_details = {
        "is_valid": is_valid,
        "execution_time_ms": execution_time_ms,
        "performance_target_ms": performance_target,
        "difference_ms": performance_target - execution_time_ms,
        "details": f"Execution time {execution_time_ms:.2f}ms vs target {performance_target:.2f}ms "
                  f"({'within' if is_valid else 'exceeds'} target by "
                  f"{abs(performance_target - execution_time_ms):.2f}ms)"
    }
    
    # Log result
    if is_valid:
        logger.info(f"Performance validation successful: {validation_details['details']}")
    else:
        logger.warning(f"Performance validation failed: {validation_details['details']}")
    
    return is_valid, validation_details

def validate_compliance(
    test_results: Dict[str, Dict[str, Any]],
    threshold: float,
    logger: logging.Logger
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate compliance based on test results.
    
    Args:
        test_results: Dictionary mapping scenario names to test results
        threshold: Minimum passing percentage threshold (0.0-1.0)
        logger: Logger instance
        
    Returns:
        Tuple of (is_compliant, compliance_results)
    """
    logger.info(f"Validating compliance against threshold {threshold:.2%}")
    
    # Calculate success rates
    total_tests = len(test_results)
    success_count = sum(1 for result in test_results.values() if result.get("success", False))
    sql_validation_count = sum(1 for result in test_results.values() 
                             if result.get("sql_validation", {}).get("is_valid", False))
    phrase_validation_count = sum(1 for result in test_results.values() 
                                if result.get("phrase_validation", {}).get("is_valid", False))
    
    # Calculate rates
    success_rate = success_count / max(1, total_tests)
    sql_validation_rate = sql_validation_count / max(1, total_tests)
    phrase_validation_rate = phrase_validation_count / max(1, total_tests)
    
    # Compliance is successful if all rates meet threshold
    is_compliant = (
        success_rate >= threshold and
        sql_validation_rate >= threshold and
        phrase_validation_rate >= threshold
    )
    
    # Create compliance results
    compliance_results = {
        "is_compliant": is_compliant,
        "threshold": threshold,
        "total_tests": total_tests,
        "success_rate": success_rate,
        "sql_validation_rate": sql_validation_rate,
        "phrase_validation_rate": phrase_validation_rate,
        "details": f"Success rate: {success_rate:.2%}, SQL validation rate: {sql_validation_rate:.2%}, "
                  f"Phrase validation rate: {phrase_validation_rate:.2%}",
        "requirements_met": {
            "success_rate": success_rate >= threshold,
            "sql_validation_rate": sql_validation_rate >= threshold,
            "phrase_validation_rate": phrase_validation_rate >= threshold
        }
    }
    
    # Log compliance results
    if is_compliant:
        logger.info(f"Compliance validation successful: {compliance_results['details']}")
    else:
        logger.warning(f"Compliance validation failed: {compliance_results['details']}")
    
    return is_compliant, compliance_results 