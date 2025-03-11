"""
Testing Orchestrator for AI Testing

This module manages the end-to-end testing process, including test case execution,
result collection, and evaluation.
"""

import os
import time
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path

from .headless_streamlit import HeadlessStreamlit
from .ai_user_simulator import AIUserSimulator
from .database_validator import DatabaseValidator
from .monitoring import create_test_monitor

logger = logging.getLogger(__name__)

class TestingOrchestrator:
    """Manages the testing process for the AI system."""
    
    def __init__(
        self, 
        headless_app: HeadlessStreamlit,
        user_simulator: AIUserSimulator,
        db_validator: Optional[DatabaseValidator] = None,
        test_scenarios: Optional[Dict[str, Any]] = None,
        results_dir: str = "test_results",
        enable_monitoring: bool = True
    ):
        """Initialize the testing orchestrator."""
        self.headless_app = headless_app
        self.user_simulator = user_simulator
        self.db_validator = db_validator
        self.test_scenarios = test_scenarios or self._default_scenarios()
        self.test_results = []
        self.monitoring_callbacks = []
        self.results_dir = results_dir
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        # Set up monitoring if enabled
        self.monitor = None
        if enable_monitoring:
            self.monitor, monitor_callback = create_test_monitor()
            self.add_monitoring_callback(monitor_callback)
        
        logger.info(f"Initialized TestingOrchestrator with {len(self.test_scenarios)} scenarios")
        
    def run_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Run a specific test scenario."""
        logger.info(f"Running test scenario: {scenario_name}")
        
        if scenario_name not in self.test_scenarios:
            error_msg = f"Scenario '{scenario_name}' not found in test scenarios"
            logger.error(error_msg)
            return {
                "scenario": scenario_name,
                "status": "error",
                "error": error_msg,
                "interactions": [],
                "validation_results": [],
                "execution_time": 0
            }
            
        scenario = self.test_scenarios[scenario_name]
        start_time = time.time()
        
        # Reset the application state
        self.headless_app.reset()
        
        # Set up user simulator with scenario-specific context
        if "context" in scenario:
            self.user_simulator.set_context(scenario["context"])
            
        # Set persona if specified
        if "persona" in scenario:
            self.user_simulator.set_persona(scenario["persona"])
            
        # Set error rate if specified
        if "error_rate" in scenario:
            original_error_rate = self.user_simulator.error_rate
            self.user_simulator.error_rate = scenario["error_rate"]
            
        # Track all interactions and evaluations
        interactions = []
        validation_results = []
        scenario_status = "success"
        scenario_error = None
        
        try:
            # Generate initial query
            query = self.user_simulator.generate_initial_query()
            
            # Run the conversation for specified turns or until termination condition
            max_turns = scenario.get("max_turns", 5)
            for turn in range(max_turns):
                logger.debug(f"Turn {turn + 1}/{max_turns}: Processing query: {query}")
                
                # Process query in headless app
                self.headless_app.set_input(query)
                query_start_time = time.time()
                
                # Process the input (this would typically be handled by run_app())
                # We're simulating app execution here
                self._process_input()
                
                query_processing_time = time.time() - query_start_time
                
                # Extract system response
                if not self.headless_app.terminal_output:
                    logger.warning("No response generated by the application")
                    system_response = "No response from the system."
                    scenario_status = "warning"
                else:
                    system_response = self.headless_app.terminal_output[-1]["text"]
                
                # Evaluate response if validator is available
                validation_result = None
                if self.db_validator and "response_type" in scenario:
                    try:
                        validation_result = self.db_validator.validate_response(
                            system_response, 
                            scenario["response_type"],
                            scenario.get("entities")
                        )
                        validation_results.append(validation_result)
                        
                        # Update scenario status if validation failed
                        if not validation_result.get("valid", True):
                            scenario_status = "validation_error"
                    except Exception as e:
                        logger.error(f"Error during validation: {str(e)}", exc_info=True)
                        validation_result = {
                            "error": str(e),
                            "valid": False
                        }
                        validation_results.append(validation_result)
                        scenario_status = "validation_error"
                
                # Record interaction
                interaction = {
                    "turn": turn,
                    "query": query,
                    "response": system_response,
                    "processing_time": query_processing_time,
                    "validation_result": validation_result,
                    "timestamp": time.time()
                }
                interactions.append(interaction)
                
                # Trigger real-time monitoring callbacks
                for callback in self.monitoring_callbacks:
                    callback(interaction)
                
                # Check termination conditions
                if self._should_terminate(scenario, turn, interactions):
                    logger.debug(f"Termination condition met after turn {turn + 1}")
                    break
                
                # Generate follow-up if not at max turns
                if turn < max_turns - 1:
                    query = self.user_simulator.generate_followup(system_response)
        
        except Exception as e:
            logger.error(f"Error during scenario execution: {str(e)}", exc_info=True)
            scenario_status = "error"
            scenario_error = str(e)
            
        finally:
            # Reset error rate if it was modified
            if "error_rate" in scenario:
                self.user_simulator.error_rate = original_error_rate
        
        execution_time = time.time() - start_time
        
        # Compile results
        result = {
            "scenario": scenario_name,
            "status": scenario_status,
            "error": scenario_error,
            "interactions": interactions,
            "validation_results": validation_results,
            "execution_time": execution_time,
            "timestamp": time.time()
        }
        
        # Save results to file
        self._save_result(result)
        
        # Add to in-memory results
        self.test_results.append(result)
        
        logger.info(f"Completed scenario '{scenario_name}' with status: {scenario_status} in {execution_time:.2f} seconds")
        return result
    
    def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Run all available test scenarios."""
        logger.info(f"Running all {len(self.test_scenarios)} test scenarios")
        results = []
        
        for scenario_name in self.test_scenarios:
            result = self.run_test_scenario(scenario_name)
            results.append(result)
            
        return results
    
    def add_monitoring_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback function for real-time monitoring."""
        self.monitoring_callbacks.append(callback)
    
    def generate_report(self, results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a summary report of test results."""
        results = results or self.test_results
        
        if not results:
            return {"error": "No test results available"}
        
        # Calculate statistics
        total_scenarios = len(results)
        successful_scenarios = sum(1 for r in results if r["status"] == "success")
        validation_errors = sum(1 for r in results if r["status"] == "validation_error")
        warnings = sum(1 for r in results if r["status"] == "warning")
        errors = sum(1 for r in results if r["status"] == "error")
        
        total_interactions = sum(len(r["interactions"]) for r in results)
        avg_interactions_per_scenario = total_interactions / total_scenarios if total_scenarios > 0 else 0
        
        total_time = sum(r["execution_time"] for r in results)
        avg_time_per_scenario = total_time / total_scenarios if total_scenarios > 0 else 0
        
        # Validation statistics
        valid_responses = 0
        invalid_responses = 0
        validation_count = 0
        
        for result in results:
            for validation in result.get("validation_results", []):
                validation_count += 1
                if validation.get("valid", False):
                    valid_responses += 1
                else:
                    invalid_responses += 1
        
        validation_success_rate = valid_responses / validation_count if validation_count > 0 else 0
        
        report = {
            "timestamp": time.time(),
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "validation_errors": validation_errors,
            "warnings": warnings,
            "errors": errors,
            "success_rate": successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
            "total_interactions": total_interactions,
            "avg_interactions_per_scenario": avg_interactions_per_scenario,
            "total_execution_time": total_time,
            "avg_time_per_scenario": avg_time_per_scenario,
            "validation_statistics": {
                "validation_count": validation_count,
                "valid_responses": valid_responses,
                "invalid_responses": invalid_responses,
                "validation_success_rate": validation_success_rate
            }
        }
        
        return report
    
    def _process_input(self) -> None:
        """Simulate processing the input through the app.
        
        In a real implementation, this would be handled by the app's run function.
        We're simulating it here for testing purposes.
        """
        query = self.headless_app.current_input
        
        # Example response generation for testing
        with self.headless_app.chat_message("assistant") as container:
            container.write(f"Echo: {query}")
    
    def _should_terminate(self, scenario: Dict[str, Any], turn: int, interactions: List[Dict[str, Any]]) -> bool:
        """Determine if the test scenario should terminate."""
        # Check if we've reached the maximum number of turns
        if turn >= scenario.get("max_turns", 5):
            logger.info(f"Terminating scenario '{scenario.get('name', 'unnamed')}' due to max turns reached")
            return True
            
        # Debug the entire function call
        logger.debug(f"_should_terminate called with turn={turn}, scenario={scenario}")
        logger.debug(f"interactions={interactions}")
            
        # Check for termination phrases
        if not interactions:
            logger.debug("No interactions to check")
            return False
            
        if "response" not in interactions[-1]:
            logger.debug("Last interaction has no response")
            return False
            
        last_response = interactions[-1]["response"].lower()  # Convert to lowercase
        logger.debug(f"Last response (lowercase): '{last_response}'")
            
        # Check for termination phrases
        termination_phrases = scenario.get("termination_phrases", [])
        logger.debug(f"Termination phrases: {termination_phrases}")
        
        for phrase in termination_phrases:
            phrase_lower = phrase.lower()  # Ensure phrase is lowercase
            logger.debug(f"Checking if termination phrase '{phrase_lower}' is in '{last_response}'")
            if phrase_lower in last_response:
                logger.info(f"Terminating scenario due to termination phrase: '{phrase}'")
                return True
                
        # Check for success conditions if specified
        success_conditions = scenario.get("success_conditions", [])
        logger.debug(f"Success conditions: {success_conditions}")
        
        if success_conditions:
            for condition in success_conditions:
                logger.debug(f"Checking condition: {condition}")
                
                # Handle dictionary condition format
                if isinstance(condition, dict) and condition.get("type") == "response_contains":
                    phrase = condition.get("phrase", "").lower()  # Ensure phrase is lowercase
                    logger.debug(f"Dictionary condition - Checking if '{phrase}' is in '{last_response}'")
                    # Check if the phrase is anywhere in the response
                    phrase_found = phrase in last_response
                    logger.debug(f"Phrase found: {phrase_found}")
                    
                    if phrase_found:
                        logger.info(f"Terminating scenario due to success condition met: '{phrase}'")
                        return True
                # Handle string condition format
                elif isinstance(condition, str):
                    condition_lower = condition.lower()  # Ensure condition is lowercase
                    logger.debug(f"String condition - Checking if '{condition_lower}' is in '{last_response}'")
                    # Check if the condition is anywhere in the response
                    condition_found = condition_lower in last_response
                    logger.debug(f"Condition found: {condition_found}")
                    
                    if condition_found:
                        logger.info(f"Terminating scenario due to success condition met: '{condition}'")
                        return True
                else:
                    logger.debug(f"Unknown condition type: {type(condition)}")
        
        logger.debug("No termination criteria met, continuing scenario")
        return False
    
    def _save_result(self, result: Dict[str, Any]) -> None:
        """Save a test result to a file."""
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Create a filename with the scenario name and timestamp
        scenario_name = result.get("scenario", "unnamed")
        timestamp = result.get("timestamp", int(time.time()))
        filename = f"{scenario_name}_{timestamp}.json"
        file_path = os.path.join(self.results_dir, filename)
        
        # Write the result to a JSON file
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Saved test result to {file_path}")
    
    def _default_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Create default test scenarios."""
        return {
            "menu_inquiry_casual": {
                "description": "A casual customer asks about menu items",
                "persona": "casual_diner",
                "context": {
                    "inquiry_type": "menu"
                },
                "response_type": "menu_query",
                "max_turns": 3,
                "error_rate": 0.0
            },
            "order_history_inquiry": {
                "description": "A frequent customer asks about their order history",
                "persona": "frequent_customer",
                "context": {
                    "inquiry_type": "order_history",
                    "customer_id": 123
                },
                "response_type": "order_history",
                "max_turns": 3,
                "error_rate": 0.0
            },
            "new_user_confusion": {
                "description": "A new user who is confused about how to use the system",
                "persona": "new_user",
                "context": {
                    "inquiry_type": "general"
                },
                "response_type": "general",
                "max_turns": 4,
                "error_rate": 0.0
            },
            "error_resilience_test": {
                "description": "Test system resilience with error-prone input",
                "persona": "casual_diner",
                "context": {
                    "inquiry_type": "menu"
                },
                "response_type": "menu_query",
                "max_turns": 3,
                "error_rate": 0.3
            },
            "non_native_speaker": {
                "description": "Customer with limited English proficiency",
                "persona": "non_native_speaker",
                "context": {
                    "inquiry_type": "menu"
                },
                "response_type": "menu_query",
                "max_turns": 3,
                "error_rate": 0.0
            }
        }
    
    def generate_ai_test_cases(self, feature_description: str, 
                              categories: Optional[List[str]] = None,
                              num_scenarios: int = 5,
                              system_context: Optional[str] = None,
                              add_to_library: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Generate test cases using AI based on feature description.
        
        Args:
            feature_description: Description of the feature to test
            categories: Specific categories of tests to generate (e.g., "menu_query", "edge_cases")
            num_scenarios: Number of scenarios to generate
            system_context: Additional context about the system to help the AI
            add_to_library: Whether to add generated scenarios to the test scenario library
            
        Returns:
            Dictionary of generated test scenarios
        """
        logger.info(f"Generating AI test cases for feature: {feature_description}")
        
        try:
            # Build system prompt
            system_prompt = """You are an expert test case generator for conversational AI systems for restaurants.
Your task is to create diverse and realistic test scenarios that will thoroughly validate the system's functionality.

Each test scenario should include:
1. A descriptive name
2. A clear category (menu_query, order_history, recommendations, edge_cases, error_recovery, multi_turn, special_requests)
3. A detailed description of what the scenario is testing
4. The priority level (high, medium, low)
5. Relevant tags
6. Contextual information needed for the test
7. Initial query hints for the AI user simulator
8. Expected entities that should be identified
9. Success conditions that determine if the test passes
10. Termination phrases that should end the conversation
11. The maximum number of conversation turns
12. Any specific validation requirements

Produce JSON output with scenario names as keys and detailed scenario objects as values."""

            # Build user prompt
            user_prompt = f"Generate {num_scenarios} diverse test scenarios for testing this feature: {feature_description}."
            
            # Add category filtering if specified
            if categories:
                category_list = ", ".join(categories)
                user_prompt += f" Focus on these categories: {category_list}."
                
            # Add system context if provided
            if system_context:
                user_prompt += f"\n\nSystem context: {system_context}"
                
            user_prompt += "\n\nFormat the output as a structured JSON object with scenario names as keys and scenario details as values."
            
            # Use the user simulator's OpenAI client
            response = self.user_simulator.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Process and structure the generated test cases
            test_cases_text = response.choices[0].message.content
            
            # Extract JSON from response
            test_cases = self._parse_generated_test_cases(test_cases_text)
            
            # Validate and enhance the generated test cases
            validated_test_cases = {}
            for name, scenario in test_cases.items():
                # Ensure all required fields are present
                enhanced_scenario = self._enhance_generated_scenario(name, scenario)
                validated_test_cases[name] = enhanced_scenario
            
            # Add the generated test cases to our scenarios if requested
            if add_to_library:
                for name, scenario in validated_test_cases.items():
                    if name not in self.test_scenarios:
                        self.test_scenarios[name] = scenario
                        logger.info(f"Added new AI-generated test scenario: {name}")
                    else:
                        new_name = f"{name}_{uuid.uuid4().hex[:8]}"
                        self.test_scenarios[new_name] = scenario
                        logger.info(f"Added new AI-generated test scenario with modified name: {new_name}")
            
            return validated_test_cases
            
        except Exception as e:
            logger.error(f"Error generating AI test cases: {str(e)}", exc_info=True)
            return {}
    
    def _enhance_generated_scenario(self, name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a generated scenario by ensuring all required fields are present
        and properly formatted.
        """
        # Default field values
        default_fields = {
            "name": name,
            "category": "general",
            "description": f"Test scenario for {name}",
            "priority": "medium",
            "tags": [],
            "context": {},
            "initial_query_hints": [],
            "expected_entities": [],
            "success_conditions": [],
            "termination_phrases": ["goodbye", "thank you", "thanks"],
            "max_turns": 5,
            "validation_requirements": []
        }
        
        # Merge with defaults for any missing fields
        enhanced = {**default_fields, **scenario}
        
        # Ensure tags is a list
        if isinstance(enhanced["tags"], str):
            enhanced["tags"] = [tag.strip() for tag in enhanced["tags"].split(",")]
        
        # Ensure context is a dictionary
        if not isinstance(enhanced["context"], dict):
            enhanced["context"] = {"additional_info": enhanced["context"]}
            
        # Ensure lists are proper lists
        for field in ["initial_query_hints", "expected_entities", "success_conditions", 
                     "termination_phrases", "validation_requirements"]:
            if not isinstance(enhanced[field], list):
                if enhanced[field]:  # If not empty
                    enhanced[field] = [enhanced[field]]
                else:
                    enhanced[field] = []
        
        return enhanced
    
    def _parse_generated_test_cases(self, test_cases_text: str) -> Dict[str, Dict[str, Any]]:
        """Parse the generated test cases from the AI response."""
        # Try to extract JSON from the text
        try:
            # Find JSON-like content between triple backticks if present
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', test_cases_text)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = test_cases_text
                
            # Parse the JSON
            test_cases = json.loads(json_str)
            
            # Validate the structure - ensure it's a dictionary of scenarios
            if not isinstance(test_cases, dict):
                logger.warning("Generated test cases are not in the expected dictionary format")
                if isinstance(test_cases, list):
                    # Convert list to dictionary using indices as keys
                    converted = {}
                    for i, scenario in enumerate(test_cases):
                        if isinstance(scenario, dict):
                            name = scenario.get("name", f"scenario_{i}")
                            converted[name] = scenario
                    return converted
                return {}
                
            return test_cases
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing generated test cases: {str(e)}", exc_info=True)
            logger.debug(f"Raw test cases text: {test_cases_text}")
            return {}
    
    def generate_targeted_test_cases(self, 
                                 target_area: str, 
                                 difficulty: str = "medium",
                                 focus_on_edge_cases: bool = False,
                                 num_scenarios: int = 3) -> Dict[str, Dict[str, Any]]:
        """
        Generate test cases targeted at a specific area or functionality.
        
        Args:
            target_area: The specific area to test (e.g., "menu search", "order history")
            difficulty: How challenging the tests should be ("easy", "medium", "hard")
            focus_on_edge_cases: Whether to focus on edge cases and error conditions
            num_scenarios: Number of scenarios to generate
            
        Returns:
            Dictionary of generated test scenarios
        """
        # Create a more specific prompt for the targeted area
        description = f"Generate targeted test scenarios for the '{target_area}' functionality."
        if focus_on_edge_cases:
            description += " Focus on edge cases, error conditions, and unexpected user behaviors."
            categories = ["edge_cases", "error_recovery"]
        else:
            categories = None
            
        # Add context about the difficulty level
        system_context = f"These tests should be {difficulty} difficulty level."
        if difficulty == "hard":
            system_context += " Include complex multi-turn interactions and challenging user behaviors."
        elif difficulty == "easy":
            system_context += " Focus on straightforward, common use cases that should definitely work."
            
        return self.generate_ai_test_cases(
            feature_description=description,
            categories=categories,
            num_scenarios=num_scenarios,
            system_context=system_context
        )
        
    def analyze_and_suggest_test_cases(self, 
                                     previous_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Analyze previous test results and suggest new test cases to improve coverage.
        
        Args:
            previous_results: Previous test results to analyze, or use self.test_results if None
            
        Returns:
            Dictionary of suggested new test scenarios
        """
        results = previous_results or self.test_results
        if not results:
            logger.warning("No previous test results available for analysis")
            return {}
            
        # Extract information about previous tests
        scenarios_tested = set()
        scenarios_failed = set()
        categories_tested = set()
        common_issues = []
        
        for result in results:
            scenario_name = result.get("scenario")
            if scenario_name:
                scenarios_tested.add(scenario_name)
                
                # Check if the scenario had issues
                if result.get("status") == "failed":
                    scenarios_failed.add(scenario_name)
                
                # Get the category if available
                if scenario_name in self.test_scenarios:
                    category = self.test_scenarios[scenario_name].get("category")
                    if category:
                        categories_tested.add(category)
                
                # Extract issues from critiques
                for critique in result.get("critiques", []):
                    if "message" in critique:
                        common_issues.append(critique["message"])
        
        # Create a system context based on the analysis
        system_context = f"""
Analysis of previous test results:
- {len(scenarios_tested)} scenarios have been tested
- {len(scenarios_failed)} scenarios failed
- Categories tested: {', '.join(categories_tested) if categories_tested else 'None'}

Based on this analysis, generate test scenarios that:
1. Cover categories not yet well-tested
2. Explore edge cases related to failed scenarios
3. Address common issues identified in previous tests
"""

        # Identify untested categories
        all_categories = [
            "menu_query", "order_history", "recommendations", 
            "edge_cases", "error_recovery", "multi_turn", "special_requests"
        ]
        untested_categories = [cat for cat in all_categories if cat not in categories_tested]
        
        # Generate scenarios
        return self.generate_ai_test_cases(
            feature_description="Generate test scenarios to improve test coverage based on previous results",
            categories=untested_categories if untested_categories else None,
            num_scenarios=5,
            system_context=system_context
        )
        
    def generate_test_suite(self, 
                          suite_description: str,
                          categories: List[str] = None,
                          num_per_category: int = 2,
                          add_to_library: bool = True) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Generate a complete test suite with scenarios for multiple categories.
        
        Args:
            suite_description: Overall description of the test suite
            categories: List of categories to include (defaults to all standard categories)
            num_per_category: Number of scenarios to generate per category
            add_to_library: Whether to add generated scenarios to the test library
            
        Returns:
            Dictionary mapping categories to their generated test scenarios
        """
        if not categories:
            categories = [
                "menu_query", "order_history", "recommendations", 
                "edge_cases", "error_recovery", "multi_turn", "special_requests"
            ]
            
        suite = {}
        
        # Generate scenarios for each category
        for category in categories:
            logger.info(f"Generating {num_per_category} test scenarios for category: {category}")
            category_description = f"{suite_description} - {category.replace('_', ' ').title()} scenarios"
            
            scenarios = self.generate_ai_test_cases(
                feature_description=category_description,
                categories=[category],
                num_scenarios=num_per_category,
                add_to_library=add_to_library
            )
            
            suite[category] = scenarios 