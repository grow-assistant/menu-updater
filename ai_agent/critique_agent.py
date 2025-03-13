"""
Critique Agent for Restaurant Assistant

This module provides a Critique Agent that analyzes responses from the AI assistant
to ensure they comply with business requirements and accurately reflect the SQL results.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class CritiqueAgent:
    """
    The Critique Agent serves as an independent quality controller that analyzes
    each response before delivery to ensure compliance with SQL and business rules.
    """
    
    def __init__(self, config=None):
        """Initialize the critique agent with optional configuration."""
        self.config = config or {}
        self.required_phrases = {
            "menu": ["our current menu includes", "on our menu", "we offer"],
            "sales": ["your sales", "sales performance", "revenue"],
            "performance": ["performing", "performance", "compared to"],
            "busiest": ["your busiest", "highest traffic", "most customers"],
            "ambiguous": ["clarify", "more specific", "more information", "specify", "what would you like to know"]
        }
        logger.info("Critique Agent initialized")
    
    def critique_response(self, query: str, response: str, sql_query: str, 
                         sql_result: Dict[str, Any], is_ambiguous: bool = False) -> Dict[str, Any]:
        """
        Analyze a response to ensure it's accurate and meets business requirements.
        
        Args:
            query: The original user query
            response: The generated response text
            sql_query: The SQL query used to generate the response
            sql_result: The results returned from the SQL query
            is_ambiguous: Flag indicating if the query is ambiguous
            
        Returns:
            A dictionary containing critique results
        """
        # Handle None response
        response = response or ""
        sql_query = sql_query or ""
        sql_result = sql_result or {}
        
        critique = {
            "query": query,
            "response_length": len(response),
            "sql_query_length": len(sql_query),
            "issues": [],
            "passed": True,
            "summary": ""
        }
        
        # Check if response is empty
        if not response:
            critique["issues"].append("Empty response")
            critique["passed"] = False
        
        # Handle ambiguous queries differently
        if is_ambiguous:
            # For ambiguous queries, we should check for clarification request
            ambiguous_check = self._check_ambiguous_query(query, response)
            if not ambiguous_check["passed"]:
                critique["issues"].extend(ambiguous_check["issues"])
                critique["passed"] = False
            
            # Early return for ambiguous queries - we don't need to check SQL or other aspects
            if critique["passed"]:
                critique["summary"] = "Response appropriately requests clarification for ambiguous query"
            else:
                critique["summary"] = f"Response fails to properly handle ambiguous query ({len(critique['issues'])} issues)"
            
            return critique
        
        # Processing for non-ambiguous queries continues below
        
        # Check SQL query was generated (if needed)
        query_keywords = ["menu", "sales", "order", "inventory", "performance", "busiest"]
        needs_sql = any(keyword in query.lower() for keyword in query_keywords)
        
        if needs_sql and not sql_query:
            critique["issues"].append("Missing SQL query for data-dependent question")
            critique["passed"] = False
        
        # Check required phrases based on query type
        required_phrases_found = self._check_required_phrases(query, response)
        if not required_phrases_found["passed"]:
            critique["issues"].extend(required_phrases_found["issues"])
            critique["passed"] = False
        
        # Check data consistency between SQL results and response
        if sql_result and "rows" in sql_result:
            data_consistency = self._check_data_consistency(response, sql_result)
            if not data_consistency["passed"]:
                critique["issues"].extend(data_consistency["issues"])
                critique["passed"] = False
        
        # Check if response addresses the query
        addresses_query = self._check_addresses_query(query, response)
        if not addresses_query["passed"]:
            critique["issues"].extend(addresses_query["issues"])
            critique["passed"] = False
        
        # Generate summary
        if critique["passed"]:
            critique["summary"] = "Response meets quality standards"
        else:
            critique["summary"] = f"Response has {len(critique['issues'])} issues"
        
        return critique
    
    def _check_ambiguous_query(self, query: str, response: str) -> Dict[str, Any]:
        """
        Check if the response appropriately asks for clarification for an ambiguous query.
        
        Args:
            query: The original user query
            response: The generated response text
            
        Returns:
            A dictionary containing check results
        """
        result = {"passed": False, "issues": []}
        
        # Check for clarification request phrases
        clarification_phrases = self.required_phrases.get("ambiguous", [])
        
        # Check if any clarification phrases are in the response
        found_phrases = []
        for phrase in clarification_phrases:
            if phrase.lower() in response.lower():
                found_phrases.append(phrase)
        
        # Check if response has a question mark (likely asking a question back)
        has_question = "?" in response
        
        # Pass if we have clarification phrases and the response is asking a question
        if found_phrases and has_question:
            result["passed"] = True
        elif not found_phrases:
            result["issues"].append("Response doesn't ask for clarification on ambiguous query")
        elif not has_question:
            result["issues"].append("Response doesn't pose a clarification question to the user")
        
        return result
    
    def _check_required_phrases(self, query: str, response: str) -> Dict[str, Any]:
        """Check if response contains required phrases based on query type."""
        result = {"passed": True, "issues": []}
        
        for query_type, phrases in self.required_phrases.items():
            if query_type in query.lower():
                found = False
                for phrase in phrases:
                    if phrase in response.lower():
                        found = True
                        break
                
                if not found:
                    result["passed"] = False
                    result["issues"].append(f"Missing required phrase for {query_type} query")
        
        return result
    
    def _check_data_consistency(self, response: str, sql_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check if response data is consistent with SQL results."""
        result = {"passed": True, "issues": []}
        
        # Get values from SQL results
        values = []
        if "rows" in sql_result and sql_result["rows"]:
            # Extract all values from all rows
            for row in sql_result["rows"]:
                if isinstance(row, dict):
                    values.extend(str(v) for v in row.values())
                elif isinstance(row, (list, tuple)):
                    values.extend(str(v) for v in row)
        
        # Check if any numeric values from SQL appear in the response
        numeric_values_found = 0
        numeric_values_total = 0
        
        for value in values:
            # Check if value appears to be numeric
            if isinstance(value, str) and value.replace('.', '', 1).isdigit():
                numeric_values_total += 1
                # Check if this value or a rounded version appears in the response
                if value in response:
                    numeric_values_found += 1
                elif '.' in value:
                    # Try rounded versions
                    try:
                        float_val = float(value)
                        rounded = str(round(float_val))
                        if rounded in response:
                            numeric_values_found += 1
                    except ValueError:
                        pass
        
        # If we found SQL numeric values but none appear in the response, that's an issue
        if numeric_values_total > 0 and numeric_values_found == 0:
            result["passed"] = False
            result["issues"].append("Response doesn't contain any numeric values from SQL results")
        
        return result
    
    def _check_addresses_query(self, query: str, response: str) -> Dict[str, Any]:
        """Check if the response addresses the user's query."""
        result = {"passed": True, "issues": []}
        
        # Extract key terms from query
        query = query.lower()
        key_terms = []
        
        # Check for question terms
        question_terms = ["what", "how", "when", "why", "where", "which", "who"]
        for term in question_terms:
            if term in query.split():
                key_terms.append(term)
        
        # Check for business terms
        business_terms = ["menu", "order", "sales", "revenue", "customer", "item", "price"]
        for term in business_terms:
            if term in query:
                key_terms.append(term)
        
        # Check if at least some key terms are addressed in the response
        terms_addressed = 0
        for term in key_terms:
            if term in response.lower():
                terms_addressed += 1
        
        if key_terms and terms_addressed < len(key_terms) / 2:
            result["passed"] = False
            result["issues"].append("Response doesn't adequately address the query")
        
        return result
    
    def critique_conversation(self, scenario: Dict[str, Any], 
                            conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a full conversation to ensure it meets the requirements.
        
        Args:
            scenario: The test scenario details
            conversation_history: List of query/response pairs
            
        Returns:
            A dictionary containing overall critique results
        """
        result = {
            "scenario": scenario.get("name", "Unknown"),
            "turns": len(conversation_history),
            "turn_critiques": [],
            "overall_passed": True,
            "summary": ""
        }
        
        # Check if this is an ambiguous scenario
        is_ambiguous = scenario.get("is_ambiguous", False) or any(tag.lower() == "ambiguous" for tag in scenario.get("tags", []))
        
        # Analyze each turn
        for i, turn in enumerate(conversation_history):
            query = turn.get("query", "")
            response = turn.get("response", "")
            sql_query = turn.get("sql", "")
            sql_result = turn.get("sql_results", {})
            
            turn_critique = self.critique_response(
                query, 
                response, 
                sql_query, 
                sql_result, 
                is_ambiguous=is_ambiguous
            )
            turn_critique["turn"] = i + 1
            
            result["turn_critiques"].append(turn_critique)
            
            if not turn_critique["passed"]:
                result["overall_passed"] = False
        
        # Generate overall summary
        passed_count = sum(1 for tc in result["turn_critiques"] if tc["passed"])
        if result["overall_passed"]:
            result["summary"] = f"All {len(result['turn_critiques'])} turns passed quality checks"
        else:
            result["summary"] = f"{passed_count}/{len(result['turn_critiques'])} turns passed quality checks"
        
        return result 