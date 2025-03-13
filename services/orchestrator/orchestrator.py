"""
Orchestrator service that coordinates the workflow between services.
"""
import logging
import time
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import re  # Add this import
import concurrent.futures
import psutil
import threading
import os
from unittest.mock import MagicMock
from collections import defaultdict  # Add this import
import traceback

from resources.ui.personas import get_voice_settings
from services.utils.service_registry import ServiceRegistry
from services.classification.classifier import ClassificationService
from services.rules.rules_service import RulesService
from services.sql_generator.sql_generator_factory import SQLGeneratorFactory
from services.execution.sql_executor import SQLExecutor
from services.response.response_generator import ResponseGenerator
from services.context_manager import ContextManager

logger = logging.getLogger(__name__)

class OrchestratorService:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator service with the provided configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize logger
        self.logger = logger
        
        # Store config for later use
        self.config = config
        
        # Set default persona
        self.persona = config.get("persona", "casual")
        
        # Initialize conversation history tracking
        self.conversation_history = []
        self.sql_history = []
        self.max_history_items = config.get("application", {}).get("max_history_items", 10)
        
        # Initialize context manager once
        from services.context_manager import ContextManager
        self.context_manager = ContextManager()
        
        # Initialize service registry
        ServiceRegistry.initialize(config)
        
        # Register services
        ServiceRegistry.register("classification", lambda cfg: ClassificationService(cfg))
        ServiceRegistry.register("rules", lambda cfg: RulesService(cfg))
        ServiceRegistry.register("sql_generator", lambda cfg: SQLGeneratorFactory.create_sql_generator(cfg))
        ServiceRegistry.register("execution", lambda cfg: SQLExecutor(cfg))
        ServiceRegistry.register("response", lambda cfg: ResponseGenerator(cfg))
        
        # Register SQL validation service if configured
        if "validation" in config.get("services", {}) and config["services"]["validation"].get("sql_validation", {}).get("enabled", False):
            try:
                from services.validation.sql_validation_service import SQLValidationService
                ServiceRegistry.register("sql_validation", lambda cfg: SQLValidationService(cfg))
                self.logger.info("SQL validation service registered")
            except Exception as e:
                self.logger.error(f"Failed to register SQL validation service: {str(e)}")
        
        # Initialize query context storage
        self.query_context = {
            "time_period_clause": None,
            "previous_query": None,
            "previous_category": None,
            "previous_sql": None,
            "previous_filters": {},
            "previous_constraints": []
        }
        
        # Initialize time period context for storing time periods from queries
        self.time_period_context = None
        
        # Get service instances - use existing mock instances if they are set for testing
        if hasattr(self, 'classifier') and isinstance(self.classifier, MagicMock):
            self.logger.info("Using existing mock classifier")
        else:
            self.classifier = ServiceRegistry.get_service("classification")
            
        if hasattr(self, 'rules') and isinstance(self.rules, MagicMock):
            self.logger.info("Using existing mock rules service")
        else:
            self.rules = ServiceRegistry.get_service("rules")
            
        if hasattr(self, 'sql_generator') and isinstance(self.sql_generator, MagicMock):
            self.logger.info("Using existing mock SQL generator")
        else:
            self.sql_generator = ServiceRegistry.get_service("sql_generator")
            
        if hasattr(self, 'sql_executor') and isinstance(self.sql_executor, MagicMock):
            self.logger.info("Using existing mock SQL executor")
        else:
            self.sql_executor = ServiceRegistry.get_service("execution")
            
        # For backwards compatibility
        self.execution_service = self.sql_executor
            
        if hasattr(self, 'response_generator') and isinstance(self.response_generator, MagicMock):
            self.logger.info("Using existing mock response generator")
        else:
            self.response_generator = ServiceRegistry.get_service("response")
        
        # Check service health
        self.health_check()
        
        self.error_context = {}
        self.retry_counter = 0  # Add retry counter
        
        # Initialize ElevenLabs for TTS at startup
        self.elevenlabs_initialized = False
        self.initialize_elevenlabs_tts()
    
    def initialize_elevenlabs_tts(self) -> bool:
        """
        Initialize the ElevenLabs TTS client.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        self.logger.info("Initializing ElevenLabs for TTS during startup")
        
        # Get the API key from config
        api_key = self.config.get("api", {}).get("elevenlabs", {}).get("api_key")
        
        if not api_key:
            self.logger.error("No ElevenLabs API key provided in config")
            self.elevenlabs_initialized = False
            return False
            
        try:
            # Set the API key length for logging without revealing the actual key
            self.logger.info(f"Setting ElevenLabs API key (length: {len(api_key)})")
            
            # Import and set up ElevenLabs
            import elevenlabs
            elevenlabs.set_api_key(api_key)
            
            # Validate by checking available voices
            voices = elevenlabs.voices()
            
            if voices:
                self.logger.info(f"ElevenLabs API key validated successfully, found {len(voices)} voices")
                # Store available voices for later use
                self.elevenlabs_voices = voices
                self.logger.info("ElevenLabs initialized successfully for TTS")
                
                # Ensure the response generator also has ElevenLabs properly initialized
                if hasattr(self, 'response_generator') and self.response_generator:
                    if hasattr(self.response_generator, 'elevenlabs_client') and not self.response_generator.elevenlabs_client:
                        self.logger.info("Reinitializing ElevenLabs in response generator")
                        self.response_generator.elevenlabs_api_key = api_key
                        try:
                            elevenlabs.set_api_key(api_key)
                            self.response_generator.elevenlabs_client = True
                            self.logger.info("ElevenLabs reinitialized in response generator")
                        except Exception as e:
                            self.logger.error(f"Failed to reinitialize ElevenLabs in response generator: {str(e)}")
                
                self.elevenlabs_initialized = True
                return True
            else:
                self.logger.error("ElevenLabs returned no voices")
                self.elevenlabs_initialized = False
                return False
                
        except ImportError:
            self.logger.error("ElevenLabs module not installed. Please install it with 'pip install elevenlabs'")
            self.elevenlabs_initialized = False
            return False
        except Exception as e:
            self.logger.error(f"Error initializing ElevenLabs: {str(e)}")
            self.elevenlabs_initialized = False
            return False
    
    def health_check(self) -> Dict[str, bool]:
        """Check the health of all services."""
        return ServiceRegistry.check_health()
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for query processing.
        
        Args:
            query: The user query to process
            context: Additional context for query processing
            
        Returns:
            Response dictionary with results
        """
        # Initialize context if not provided
        context = context or {}
        
        # Log input parameters
        fast_mode = context.get("fast_mode", False)
        self.logger.info(f"PROCESS_QUERY INPUT - query: '{query}'")
        if context:
            self.logger.info(f"PROCESS_QUERY INPUT - context: {context}")
        self.logger.info(f"PROCESS_QUERY INPUT - fast_mode: {fast_mode}")
        
        # Generate a unique ID for this query
        query_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Initialize timers for performance tracking
        timers = {
            'total_start': time.perf_counter(),
            'classification': 0.0,
            'rule_processing': 0.0,
            'sql_generation': 0.0,
            'sql_execution': 0.0,
            'text_response': 0.0,
            'tts_generation': 0.0,
            'sql_validation': 0.0,
            'total_time': 0.0
        }
        
        # Log query information
        self.logger.info(f"Processing query: '{query}' (ID: {query_id})")
        
        # Check if verbal response is requested in context
        voice_enabled = context.get("enable_verbal", False)
        self.logger.info(f"Voice enabled from context: {voice_enabled}")
        
        # If voice is enabled, we need to disable fast mode
        if voice_enabled:
            self.logger.info("Voice enabled, setting fast_mode to False")
            fast_mode = False
            
            # Make sure TTS is initialized if voice is requested
            if not self.elevenlabs_initialized:
                self.logger.warning("Verbal response requested but ElevenLabs not initialized, attempting to initialize")
                self._initialize_elevenlabs()
        
        # Get the previous query category if available (for follow-up detection)
        previous_category = None
        if "previous_category" in context:
            previous_category = context.get("previous_category")
        elif "session_history" in context and context["session_history"]:
            previous_response = context["session_history"][-1]
            if "category" in previous_response:
                previous_category = previous_response["category"]
                self.logger.info(f"Providing context from previous query: {previous_category}")
                
                # Update context with previous category
                if previous_category:
                    self.query_context["previous_category"] = previous_category
        
        # Step 1: Classify the query
        t1 = time.perf_counter()
        classification = None
        
        # Enhanced classification with context if available
        if previous_category:
            self.logger.info("Using enhanced classification with context")
            try:
                if hasattr(self.classifier, 'get_classification_with_context'):
                    classification = self.classifier.get_classification_with_context(query, {"previous_category": previous_category})
                else:
                    classification = self.classifier.classify(query)
            except Exception as e:
                self.logger.error(f"Error during classification: {str(e)}")
                # Use basic fallback classification as a backup
                category = self._basic_fallback_classification(query)
                classification = {"category": category, "confidence": 0.5, "is_followup": False}
        else:
            try:
                classification = self.classifier.classify(query)
            except Exception as e:
                self.logger.error(f"Error during classification: {str(e)}")
                # Use basic fallback classification as a backup
                category = self._basic_fallback_classification(query)
                classification = {"category": category, "confidence": 0.5, "is_followup": False}
        
        timers['classification'] = time.perf_counter() - t1
        
        if not classification:
            self.logger.error(f"Classification failed for query: {query}")
            return {
                "query_id": query_id,
                "query": query,
                "category": "unknown",
                "response": "I couldn't understand your query. Could you please rephrase it?",
                "response_model": None,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "has_verbal": False,
                "query_results": None
            }
        
        # Extract classification information
        category = classification.get("category", "unknown")
        is_followup = classification.get("is_followup", False)
        
        # Check for follow-up reclassification
        if hasattr(self.classifier, 'detect_follow_up') and previous_category:
            try:
                is_category_change, suggested_category = self.classifier.detect_follow_up(query, previous_category)
                if is_category_change:
                    self.logger.info(f"Follow-up detected: Override category from {category} to {suggested_category}")
                    category = suggested_category
                    is_followup = True
            except Exception as e:
                self.logger.error(f"Error in follow-up detection: {str(e)}")
        
        # Log classification results
        self.logger.info(f"Query classified as: {category}")
        self.logger.info(f"Is follow-up: {is_followup}")
        
        # Store current category for future reference
        self.query_context["previous_category"] = category
        
        # Special handling for order_history category - default to completed orders
        if category == "order_history" and not any(status in query.lower() for status in ["pending", "cancelled", "refunded", "in progress"]):
            self.logger.info("No status specified, defaulting to completed orders (status=7)")
            # Apply filter for completed orders
            self.query_context["previous_filters"]["status"] = "completed"
        
        # Step 2: If this is a follow-up, check for time period carry-over
        if is_followup:
            # Check if we have a time period from a previous query
            if "time_period_clause" in self.query_context and self.query_context["time_period_clause"]:
                self.logger.info(f"Follow-up question detected. Using cached time period: {self.query_context['time_period_clause']}")
            
            # Check if the follow-up relates to the previous category
            if previous_category:
                self.logger.info(f"Follow-up relates to previous category: {previous_category}")
                
                # For follow-up questions, sometimes we want to use the previous category
                # rather than classifying as a "follow_up" type
                if category == "follow_up" and previous_category != "follow_up":
                    self.logger.info(f"Using previous category '{previous_category}' for this follow-up query instead of 'follow_up'")
                    category = previous_category
            
            # Get filters from previous query
            if "previous_filters" in self.query_context and self.query_context["previous_filters"]:
                for filter_name, filter_value in self.query_context["previous_filters"].items():
                    self.logger.info(f"Using filters from previous query: {filter_name}: {filter_value}")
            
            # Explicitly preserve time period for follow-up queries
            if "time_period_clause" in self.query_context and self.query_context["time_period_clause"]:
                self.logger.info("Detected follow-up query, explicitly preserving time period context")
                self.logger.info(f"Using time period from previous query: {self.query_context['time_period_clause']}")
            
            # Check if we had a status filter from the previous query
            if "previous_filters" in self.query_context and "status" in self.query_context["previous_filters"]:
                status_value = self.query_context["previous_filters"]["status"]
                self.logger.info(f"Preserving status filter from previous query: status = {7 if status_value == 'completed' else status_value}")
        
        # Step 3: Get response rules and generate SQL (skip for ambiguous requests)
        t1 = time.perf_counter()
        response_rules = self.rules.get_rules(category, query)
        timers['rule_processing'] = time.perf_counter() - t1
        
        sql = None
        query_results = None
        
        # Skip SQL generation and execution for ambiguous requests
        is_ambiguous = category == "ambiguous"
        
        if not is_ambiguous:
            # Generate SQL
            t1 = time.perf_counter()
            generation_result = self.sql_generator.generate(
                query, 
                category,
                response_rules,
                self.query_context
            )
            sql = generation_result.get("sql")
            timers['sql_generation'] = time.perf_counter() - t1
            
            # Track the generated SQL for context
            self.query_context["previous_sql"] = sql
            
            # Extract time period from SQL if not already provided by classifier
            if not self.query_context.get("time_period_clause") and sql:
                # Look for date patterns in the SQL that might be time constraints
                date_patterns = [
                    r"\(o\.updated_at - INTERVAL '[^']+'\)::date\s*=\s*TO_DATE\('([^']+)'",  # (updated_at - INTERVAL '7 hours')::date = TO_DATE('2/21/2025'
                    r"updated_at::date\s*=\s*'([^']+)'",  # updated_at::date = '2025-02-21'
                    r"DATE\(updated_at\)\s*=\s*'([^']+)'",  # DATE(updated_at) = '2025-02-21'
                ]
                
                for pattern in date_patterns:
                    date_match = re.search(pattern, sql)
                    if date_match:
                        date_value = date_match.group(1)
                        # Create a proper time_period_clause - without the WHERE keyword and without double table references
                        time_period_clause = f"(o.updated_at - INTERVAL '7 hours')::date = TO_DATE('{date_value}', 'MM/DD/YYYY')"
                        
                        # Ensure there are no double table references
                        time_period_clause = time_period_clause.replace("o.o.", "o.")
                        
                        self.query_context["time_period_clause"] = time_period_clause
                        self.logger.info(f"Extracted time period from SQL: {self.query_context['time_period_clause']}")
                        break
            
            # Handle status filters, time constraints, etc.
            # ... [existing code for SQL cleaning] ...
            
            # Make sure we have valid SQL before continuing
            if not sql:
                self.logger.error(f"Failed to generate SQL for query: {query}")
                # Initialize result dict with error response
                result = {
                    "query_id": query_id,
                    "query": query,
                    "category": category,
                    "response": "I couldn't generate SQL for your query. Could you please rephrase it?",
                    "response_model": None,
                    "execution_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat(),
                    "has_verbal": False,
                    "query_results": None,
                    "timers": timers
                }
                return result
            
            # Step 4: Execute SQL
            t1 = time.perf_counter()
            execution_result = self.sql_executor.execute(sql)
            timers['sql_execution'] = time.perf_counter() - t1
            
            # Retrieve query results
            if execution_result and execution_result.get("success", False):
                query_results = execution_result.get("results")
                # Store the SQL query in context for validation
                if "context_updates" not in context:
                    context["context_updates"] = {}
                context["context_updates"]["sql_query"] = sql
        
        # Step 5: Generate response
        t1 = time.perf_counter()
        if voice_enabled and not fast_mode:
            # Use combined text+verbal generation if voice is enabled
            response_data = self.response_generator.generate_with_verbal(
                query, category, response_rules, query_results, {
                    "previous_sql": sql,
                    "sql_query": sql,
                    **context
                }
            )
        else:
            # Use text-only response generation
            response_data = self.response_generator.generate(
                query, category, response_rules, query_results, {
                    "previous_sql": sql,
                    "sql_query": sql,
                    **context
                }
            )
        timers['text_response'] = time.perf_counter() - t1
        
        # Step 6: Validate response with SQL validation service if available
        validation_feedback = None
        validation_blocked = False
        
        if sql and query_results and ServiceRegistry.service_exists("sql_validation"):
            try:
                t1 = time.perf_counter()
                sql_validation_service = ServiceRegistry.get_service("sql_validation")
                validation_result = sql_validation_service.validate_response(
                    sql_query=sql,
                    sql_results=query_results,
                    response_text=response_data.get("response", "")
                )
                
                # Extract validation results
                validation_status = validation_result.get("validation_status", True)
                validation_blocked = validation_result.get("should_block_response", False)
                validation_feedback = validation_result.get("detailed_feedback", "No validation feedback available")
                
                # Log validation results
                self.logger.info(f"SQL validation completed with status: {validation_status}")
                if not validation_status:
                    self.logger.warning(f"SQL validation failed: {validation_feedback}")
                
                # If validation blocked the response, replace with error message
                if validation_blocked:
                    self.logger.warning("Response was blocked by SQL validation")
                    response_data["response"] = "I'm sorry, but I can't provide an accurate response based on the data. Please try again or rephrase your question."
                
                timers['sql_validation'] = time.perf_counter() - t1
            except Exception as e:
                self.logger.error(f"Error during SQL validation: {str(e)}")
                self.logger.error(traceback.format_exc())
                validation_feedback = f"SQL validation error: {str(e)}"
        else:
            self.logger.warning("SQL validation skipped - SQL validation service not available or no results to validate")
            validation_feedback = "SQL validation skipped - service not available or no results to validate"
        
        # Step 7: TTS processing (if enabled)
        verbal_audio = None
        if voice_enabled:
            # Extract the verbal audio if already generated in combined mode
            if "verbal_audio" in response_data:
                verbal_audio = response_data.get("verbal_audio")
            else:
                t1 = time.perf_counter()
                verbal_audio = self._generate_tts(response_data.get("response"), category)
                timers['tts_generation'] = time.perf_counter() - t1
        
        # Step 8: Build final response
        response = response_data.get("response")
        
        # Calculate total execution time
        execution_time = time.time() - start_time
        
        # Build result dictionary
        result = {
            "query_id": query_id,
            "query": query,
            "category": category,
            "response": response,
            "response_model": response_data.get("response_model"),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "has_verbal": verbal_audio is not None,
            "query_results": query_results,
            "validation_feedback": validation_feedback
        }
        
        # Add verbal audio if available
        if verbal_audio:
            result["verbal_audio"] = verbal_audio
        else:
            if voice_enabled:
                self.logger.warning("No verbal audio available to add to the response")
        
        # Log total execution time and performance breakdown
        timers['total_time'] = time.perf_counter() - timers['total_start']
        self.logger.info(f"Query processing completed in {timers['total_time']:.2f}s")
        self.logger.info(f"""
            Performance Breakdown:
            - Classification: {timers['classification']:.2f}s
            - Rule Processing: {timers['rule_processing']:.2f}s
            - SQL Generation: {timers['sql_generation']:.2f}s
            - SQL Execution: {timers['sql_execution']:.2f}s
            - Text Response: {timers['text_response']:.2f}s
            - TTS Generation: {timers['tts_generation']:.2f}s
            - SQL Validation: {timers['sql_validation']:.2f}s
            - Other/Unaccounted: {timers['total_time'] - timers['classification'] - timers['rule_processing'] - timers['sql_generation'] - timers['sql_execution'] - timers['text_response'] - timers['tts_generation'] - timers['sql_validation']:.2f}s
            - Total Time: {timers['total_time']:.2f}s
        """)
        
        # Log the output, but sanitize the result
        sanitized_result = result.copy()
        if "verbal_audio" in sanitized_result:
            sanitized_result["verbal_audio"] = f"[BINARY_DATA:{len(sanitized_result['verbal_audio'])} bytes]"
        self.logger.info(f"PROCESS_QUERY OUTPUT - result: {sanitized_result}")
        
        return result

    def _preprocess_sql(self, sql_query: str) -> str:
        """
        Preprocess SQL query by replacing symbolic placeholders with default values.
        This is a simplified version of the more complex preprocessing in SQLExecutor.
        
        Args:
            sql_query: The SQL query with potential placeholders
            
        Returns:
            Processed SQL with placeholders replaced
        """
        self.logger.info(f"PREPROCESS_SQL INPUT - sql_query: '{sql_query}'")
        
        if not sql_query:
            return sql_query
            
        # Find all symbolic placeholders like [PLACEHOLDER]
        placeholder_pattern = r'\[([A-Z_]+)\]'
        
        # Find all placeholders in the query
        placeholders = re.findall(placeholder_pattern, sql_query)
        if not placeholders:
            # No placeholders to replace
            return sql_query
            
        # Replace symbolic placeholders with default values
        processed_sql = sql_query
        for placeholder_name in placeholders:
            placeholder = f"[{placeholder_name}]"
            param_key = placeholder_name.lower()
            
            # Provide a default value for common placeholders
            if "location_id" in param_key:
                # Get location_id from config if available
                value = self.config.get("location", {}).get("default_id")
                if value is None:
                    # Try environment variable format
                    value = self.config.get("DEFAULT_LOCATION_ID")
                if value is None:
                    # Try application section
                    value = self.config.get("application", {}).get("default_location_id")
                if value is None:
                    # Fallback to 1 if not in config
                    value = 1
            elif "user_id" in param_key:
                value = self.config.get("user", {}).get("default_id", 1)  # Default user ID
            elif "date" in param_key or "time" in param_key:
                from datetime import datetime
                value = datetime.now().date().isoformat()  # Today's date
            else:
                value = "NULL"  # Default for unknown placeholders
                
            # Directly replace the placeholder with the value
            if isinstance(value, str) and value != "NULL":
                # Add quotes for string values
                processed_sql = processed_sql.replace(placeholder, f"'{value}'")
            else:
                # Use the value directly for numbers and NULL
                processed_sql = processed_sql.replace(placeholder, str(value))
                
        self.logger.info(f"Preprocessed SQL: {processed_sql[:100]}..." if len(processed_sql) > 100 else processed_sql)
        
        # Get the location_id from all possible sources for accurate logging
        location_id = self.config.get("DEFAULT_LOCATION_ID")
        if location_id is None:
            location_id = self.config.get("application", {}).get("default_location_id")
        if location_id is None:
            location_id = self.config.get("location", {}).get("default_id", 1)
            
        self.logger.info(f"Using location_id: {location_id}")
        
        self.logger.info(f"PREPROCESS_SQL OUTPUT - processed_sql: '{processed_sql}'")
        return processed_sql

    def set_persona(self, persona_name: str) -> None:
        """
        Set the current persona for response generation.
        
        Args:
            persona_name: Name of the persona to use
        """
        self.logger.info(f"SET_PERSONA INPUT - persona_name: '{persona_name}'")
        
        self.persona = persona_name
        
        # Get the persona configuration from the config
        persona_config = self.config.get("persona", {})
        
        # Create a persona configuration dict with text and verbal settings
        if persona_config and persona_config.get("enabled", False):
            persona_dict = {
                "default": persona_name,
                "text_persona": persona_config.get("text_persona", "professional"),
                "verbal_persona": persona_config.get("verbal_persona", persona_name),
                "available": persona_config.get("available", [])
            }
            self.logger.info(f"Set persona to: {persona_name} with text persona: {persona_dict['text_persona']} and verbal persona: {persona_dict['verbal_persona']}")
            
            # Pass the full persona configuration to the response generator
            self.response_generator.set_persona(persona_dict)
        else:
            self.logger.info(f"Set persona to: {persona_name}")
            self.response_generator.set_persona(persona_name)
        
        self.logger.info(f"SET_PERSONA COMPLETE - persona set to: '{persona_name}'")
    
    def get_tts_response(self, text: str, model: str = "eleven_multilingual_v2", max_sentences: int = 1) -> Dict[str, Any]:
        """
        Generate a TTS response for the given text.
        
        Args:
            text: Text to convert to speech
            model: ElevenLabs model to use
            max_sentences: Maximum number of sentences to include (0 for all)
            
        Returns:
            Dictionary with TTS results
        """
        # Check if text is None or empty
        if text is None or not text.strip():
            self.logger.error("Cannot generate TTS: text is None or empty")
            return {"success": False, "error": "Text is None or empty", "text": ""}
            
        # Don't log the full text to avoid huge log files
        log_text = text[:100] + "..." if len(text) > 100 else text
        self.logger.info(f"GET_TTS_RESPONSE INPUT - text: '{log_text}' (length: {len(text)})")
        self.logger.info(f"GET_TTS_RESPONSE INPUT - model: '{model}', max_sentences: {max_sentences}")
        
        try:
            # Ensure we have ElevenLabs client
            if not self.elevenlabs_initialized:
                self.logger.warning("ElevenLabs not initialized, initializing now")
                self.elevenlabs_initialized = self.initialize_elevenlabs_tts()
                
            if not self.elevenlabs_initialized:
                self.logger.error("Failed to initialize ElevenLabs")
                return {"success": False, "error": "ElevenLabs not initialized", "text": text}
                
            # Limit the text to the specified number of sentences
            if max_sentences > 0:
                sentences = re.split(r'(?<=[.!?])\s+', text)
                if len(sentences) > max_sentences:
                    text = ' '.join(sentences[:max_sentences])
                    self.logger.info(f"Limited text to {max_sentences} sentences: '{text[:100]}...' (original length: {len(text)})")
            
            # Get voice settings based on current persona
            voice_settings = get_voice_settings(self.persona)
            voice_id = voice_settings.get('voice_id')
            
            if not voice_id:
                self.logger.warning(f"No voice ID configured for persona {self.persona}, using default voice")
                voice_id = "EXAVITQu4vr4xnSDxMaL"  # Default voice ID
            
            # Convert text to speech
            self.logger.info(f"Using ElevenLabs voice ID: {voice_id}")
            self.logger.info(f"Using ElevenLabs model: {model}")
            
            import elevenlabs
            audio_data = elevenlabs.generate(
                text=text, 
                voice=voice_id,
                model=model
            )
            
            # Log success but don't include the audio data in the logs
            if audio_data:
                self.logger.info("TTS generated successfully")
                return {
                    "success": True,
                    "audio": audio_data,
                    "text": text,
                    "voice_id": voice_id,
                    "model": model
                }
            else:
                self.logger.error("ElevenLabs returned empty audio data")
                return {"success": False, "error": "Empty audio data returned", "text": text}
                
        except Exception as e:
            self.logger.error(f"Error generating TTS response: {str(e)}")
            return {"success": False, "error": str(e), "text": text}

    def _get_error_context(self):
        """Collect critical debugging context for error analysis"""
        context = {
            'current_query': getattr(self, 'current_query', None),
            'classification_result': self.error_context.get('classification'),
            'generated_sql': self.error_context.get('generated_sql'),
            'execution_result': self.error_context.get('execution_result'),
            'retry_count': self.retry_counter,
            'timers': self.error_context.get('timers', {}),
            'system': {
                'memory_usage': psutil.Process().memory_info().rss,
                'cpu_usage': psutil.cpu_percent(),
                'active_threads': threading.active_count()
            }
        }
        
        try:
            context['connection_pool'] = self.sql_executor.get_pool_metrics()
        except Exception as e:
            context['connection_pool_error'] = str(e)
            
        try:
            context['llm_metrics'] = self.sql_generator.get_performance_metrics()
        except Exception as e:
            context['llm_metrics_error'] = str(e)
            
        return context
    
    def _record_failure_metrics(self, failure_type: str, context: Dict[str, Any], timers: Dict[str, float]):
        """
        Record metrics about failures to help with monitoring and debugging.
        
        Args:
            failure_type: Type of failure (e.g., sql_generation_failed, execution_failed)
            context: Context information for the failure
            timers: Performance timers up to the point of failure
        """
        # Log comprehensive error context for debugging
        self.logger.error(f"Failure context: {self._get_error_context()}")
        
        # In a production system, you might want to:
        # 1. Send metrics to a monitoring system
        # 2. Record failure details to a database
        # 3. Trigger alerts for critical failures
        pass
        
    def test_tts(self, text: str = None, save_to_file: bool = True) -> Dict[str, Any]:
        """
        Test the TTS functionality directly.
        
        Args:
            text: Optional text to convert to speech (default is a test message)
            save_to_file: Whether to save the audio to a file for testing
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"TEST_TTS INPUT - text: '{text[:100] if text else 'None'}...'")
        self.logger.info(f"TEST_TTS INPUT - save_to_file: {save_to_file}")
        
        if text is None:
            text = "This is a test of the ElevenLabs text-to-speech system. If you can hear this message, audio playback is working correctly."
            
        self.logger.info(f"Testing TTS functionality with text: '{text[:50]}...'")
        
        try:
            # Test TTS generation
            start_time = time.time()
            tts_response = self.get_tts_response(text, model="eleven_multilingual_v2", max_sentences=0)
            generation_time = time.time() - start_time
            
            if tts_response and tts_response.get("audio"):
                audio_data = tts_response.get("audio")
                self.logger.info(f"TTS test successful: Generated audio in {generation_time:.2f}s")
                
                # Save audio to file if requested
                if save_to_file:
                    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_output")
                    os.makedirs(test_dir, exist_ok=True)
                    audio_file = os.path.join(test_dir, "tts_test.mp3")
                    
                    with open(audio_file, "wb") as f:
                        f.write(audio_data)
                    self.logger.info(f"Saved test audio to: {audio_file}")
                    
                return {
                    "success": True,
                    "audio_file": audio_file if save_to_file else None,
                    "text": tts_response.get("text")
                }
            else:
                error = tts_response.get("error") if tts_response else "Unknown error"
                self.logger.error(f"TTS test failed: {error}")
                return {
                    "success": False,
                    "error": error
                }
                
        except Exception as e:
            self.logger.error(f"Error in TTS test: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_filters_from_sql(self, sql: str) -> Dict[str, str]:
        """Extract filters from SQL query for context tracking."""
        filters = {}
        
        # Safety check for None or empty SQL
        if not sql:
            self.logger.warning("Cannot extract filters from empty SQL")
            return filters
        
        # Look for status as a numeric value (most common case)
        status_numeric_match = re.search(r"(?:o\.)?status\s*=\s*(\d+)", sql, re.IGNORECASE)
        if status_numeric_match:
            status_code = status_numeric_match.group(1)
            # Map status codes to human-readable values
            status_map = {
                "7": "completed",
                "6": "canceled",
                "3": "pending",
                "4": "in_progress",
                "5": "ready"
            }
            filters["status"] = status_map.get(status_code, f"status_{status_code}")
            
        # Look for string status (less common)
        status_string_match = re.search(r"status\s*=\s*['\"]([\w]+)['\"]", sql, re.IGNORECASE)
        if status_string_match and "status" not in filters:
            filters["status"] = status_string_match.group(1)
            
        # Look for completed orders specifically
        if "status" not in filters:
            if "status = 7" in sql.lower() or "status=7" in sql.lower():
                filters["status"] = "completed"
            elif "completed" in sql.lower():
                if "status" in sql.lower() or "where" in sql.lower():
                    filters["status"] = "completed"
                    
        # Extract date/time filters
        date_match = re.search(r"(?:updated_at|date)\s*=\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?", sql, re.IGNORECASE)
        if date_match:
            filters["date"] = date_match.group(1)
            
        # Add more filter extractions as needed
        return filters

    def get_time_period_context(self) -> str:
        """
        Get the cached time period context from the previous query.
        
        Returns:
            The cached time period WHERE clause or None if not available
        """
        return self.query_context.get("time_period_clause")
        
    def get_query_context(self) -> Dict[str, Any]:
        """
        Get the complete query context for follow-up questions.
        
        Returns:
            Dictionary with all context information from previous queries
        """
        return self.query_context

    def _extract_constraints_from_query(self, query: str) -> Dict[str, str]:
        """Extract constraints from natural language query."""
        constraints = {}
        
        # Check for completed orders
        if "completed" in query.lower() or "complete" in query.lower():
            constraints["status"] = "completed"
            
        # Check for pending orders
        if "pending" in query.lower():
            constraints["status"] = "pending"
            
        # Check for canceled orders
        if "canceled" in query.lower() or "cancelled" in query.lower():
            constraints["status"] = "canceled"
            
        # Check for order type based on keywords
        if "delivery" in query.lower() and "pickup" not in query.lower():
            constraints["order_type"] = "delivery"
        elif "pickup" in query.lower() and "delivery" not in query.lower():
            constraints["order_type"] = "pickup"
            
        return constraints

    def _generate_sql_conditions_from_filters(self, filters: Dict[str, str]) -> List[str]:
        """Generate explicit SQL WHERE conditions from filters."""
        conditions = []
        
        # Generate status conditions
        if "status" in filters:
            status = filters["status"].lower()
            if status == "completed":
                conditions.append("o.status = 7")
            elif status == "pending":
                conditions.append("o.status = 3")
            elif status in ("canceled", "cancelled"):
                conditions.append("o.status = 6")
            elif status == "in_progress":
                conditions.append("o.status IN (4, 5)")
            elif status.startswith("status_"):  # Numeric status we don't have a name for
                try:
                    status_code = int(status.split("_")[1])
                    conditions.append(f"o.status = {status_code}")
                except (IndexError, ValueError):
                    pass
                    
        # Add date conditions
        if "date" in filters:
            date_value = filters["date"]
            if re.match(r"\d{4}-\d{2}-\d{2}", date_value):  # YYYY-MM-DD format
                conditions.append(f"(o.updated_at - INTERVAL '7 hours')::date = '{date_value}'")
                
        return conditions

    def _basic_fallback_classification(self, query: str) -> str:
        """
        Basic fallback classification when the regular classifier fails.
        
        Args:
            query: The user query to classify
            
        Returns:
            A basic category for the query
        """
        query_lower = query.lower()
        
        # Simple rule-based classification
        if any(word in query_lower for word in ["order", "purchase", "buy", "bought", "sold", "sale"]):
            return "order_history"
        elif any(word in query_lower for word in ["menu", "food", "dish", "item", "price"]):
            return "menu_inquiry"
        elif any(word in query_lower for word in ["popular", "best", "most", "common", "frequently"]):
            return "popular_items" 
        elif any(word in query_lower for word in ["trend", "growth", "increase", "decrease", "pattern"]):
            return "trend_analysis"
        else:
            return "general_question"

# Alias OrchestratorService as Orchestrator for compatibility with frontend code
Orchestrator = OrchestratorService