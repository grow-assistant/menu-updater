"""
Orchestrator service that coordinates the workflow between services.
"""
import logging
import time
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import re  # Add this import
import concurrent.futures
import psutil
import threading
import os

from services.utils.service_registry import ServiceRegistry
from services.classification.classifier import ClassificationService
from services.rules.rules_service import RulesService
from services.sql_generator.sql_generator_factory import SQLGeneratorFactory
from services.execution.sql_executor import SQLExecutor
from services.response.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class OrchestratorService:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the orchestrator with service registry."""
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
        
        # Initialize service registry
        ServiceRegistry.initialize(config)
        
        # Register services
        ServiceRegistry.register("classification", lambda cfg: ClassificationService(cfg))
        ServiceRegistry.register("rules", lambda cfg: RulesService(cfg))
        ServiceRegistry.register("sql_generator", lambda cfg: SQLGeneratorFactory.create_sql_generator(cfg))
        ServiceRegistry.register("execution", lambda cfg: SQLExecutor(cfg))
        ServiceRegistry.register("response", lambda cfg: ResponseGenerator(cfg))
        
        # Get service instances
        self.classifier = ServiceRegistry.get_service("classification")
        self.rules = ServiceRegistry.get_service("rules")
        self.sql_generator = ServiceRegistry.get_service("sql_generator")
        self.sql_executor = ServiceRegistry.get_service("execution")
        self.response_generator = ServiceRegistry.get_service("response")
        
        # Check service health
        self.health_check()
        
        self.error_context = {}
        self.retry_counter = 0  # Add retry counter
    
    def health_check(self) -> Dict[str, bool]:
        """Check the health of all services."""
        return ServiceRegistry.check_health()
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None, fast_mode: bool = True) -> Dict[str, Any]:
        """
        Process a query through the entire pipeline.
        
        Args:
            query: The user's query
            context: Additional context data (optional)
            fast_mode: If True, skips verbal response generation for faster response time (default is now True)
            
        Returns:
            Dictionary with results and metadata
        """
        self.current_query = query  # Track current query
        self.retry_counter = 0  # Reset retry counter
        
        # Add detailed timing instrumentation
        timers = {
            'total_start': time.perf_counter(),
            'classification': 0.0,
            'rule_processing': 0.0,
            'sql_generation': 0.0,
            'sql_execution': 0.0,
            'response_generation': 0.0,
            'tts_generation': 0.0
        }
        
        try:
            start_time = time.time()
            query_id = str(uuid.uuid4())
            
            self.logger.info(f"Processing query: '{query}' (ID: {query_id})")
            
            # Initialize context if not provided
            if context is None:
                context = {}
            
            # Only enable fast_mode if voice is not enabled
            if context.get("enable_verbal", False):
                fast_mode = False
                self.logger.info(f"Verbal response requested, disabling fast_mode (original fast_mode={fast_mode})")
                # Initialize ElevenLabs if needed
                self._ensure_elevenlabs_initialized()
                self.logger.debug(f"ElevenLabs initialization status: client={hasattr(self.response_generator, 'elevenlabs_client')}, key={bool(self.response_generator.elevenlabs_api_key) if hasattr(self.response_generator, 'elevenlabs_api_key') else False}")
            else:
                self.logger.info(f"Verbal response not requested in context (fast_mode={fast_mode})")
                
            context["fast_mode"] = fast_mode
            
            # Step 1: Classify the query
            self.logger.debug(f"Classifying query: '{query}'")
            t1 = time.perf_counter()
            classification = self.classifier.classify(query)
            category = classification.get("category")
            timers['classification'] = time.perf_counter() - t1
            
            self.logger.info(f"Query classified as: {category}")
            
            # Step 2: Get rules and examples for this category
            self.logger.debug(f"Loading rules for category: {category}")
            t2 = time.perf_counter()
            rules_and_examples = self.rules.get_rules_and_examples(category)
            timers['rule_processing'] = time.perf_counter() - t2
            
            # Skip database operations for certain categories
            skip_db = classification.get("skip_database", False)
            
            # Initialize query_results to None
            query_results = None
            current_sql = None
            
            # Use a thread pool for parallelizing tasks
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                sql_future = None
                
                if not skip_db:
                    # Create a context dictionary for SQL generation that includes previous SQL for context
                    sql_context = {
                        "previous_sql": self.sql_history[-3:] if self.sql_history else []  # Last 3 SQL statements
                    }
                    
                    # Step 3: Generate SQL query with previous SQL context (in parallel)
                    self.logger.debug("Generating SQL query with context")
                    t3 = time.perf_counter()
                    
                    # Submit SQL generation to thread pool
                    sql_future = executor.submit(
                        self.sql_generator.generate,
                        query,
                        category,
                        rules_and_examples,
                        sql_context
                    )
                    
                    # Continue with other tasks while SQL is being generated
                    # ... other tasks can be done here ...
                    
                    # Get SQL generation result with proper error handling
                    try:
                        sql_result = sql_future.result(timeout=30)  # 30 second timeout
                        timers['sql_generation'] = time.perf_counter() - t3
                        
                        current_sql = sql_result.get("query")
                        self.logger.debug(f"SQL query generated: {current_sql[:100] if current_sql else 'None'}...")
                        
                        # Add to SQL history
                        if current_sql:
                            self.sql_history.append(current_sql)
                    except concurrent.futures.TimeoutError:
                        self.logger.error("SQL generation timed out after 30 seconds")
                        timers['sql_generation'] = time.perf_counter() - t3
                        current_sql = None
                    except Exception as e:
                        self.logger.error(f"Error in SQL generation: {str(e)}")
                        timers['sql_generation'] = time.perf_counter() - t3
                        current_sql = None
                
                # Prepare SQL execution (in parallel with response generation)
                if current_sql:
                    t4 = time.perf_counter()
                    # Submit SQL execution to thread pool
                    execution_future = executor.submit(
                        self.sql_executor.execute,
                        current_sql
                    )
                else:
                    execution_future = None
            
            # Prepare response generation (can be done in parallel)
            response_context = {
                "query": query,
                "category": category,
                "classification": classification,
                "rules": rules_and_examples.get("response_rules", {}),
                "sql": current_sql
            }
            
            # Wait for SQL execution if it was submitted
            if not skip_db and current_sql and execution_future:
                try:
                    query_results = execution_future.result(timeout=15)  # 15 second timeout
                    timers['sql_execution'] = time.perf_counter() - t4
                    response_context["results"] = query_results
                except concurrent.futures.TimeoutError:
                    self.logger.error("SQL execution timed out after 15 seconds")
                    timers['sql_execution'] = time.perf_counter() - t4
                    query_results = {"success": False, "error": "SQL execution timed out"}
                except Exception as e:
                    self.logger.error(f"Error in SQL execution: {str(e)}")
                    timers['sql_execution'] = time.perf_counter() - t4
                    query_results = {"success": False, "error": f"SQL execution error: {str(e)}"}
            
            # Step 5: Generate natural language response
            self.logger.debug("Generating response")
            
            # Check if verbal response is requested
            enable_verbal = context.get("enable_verbal", False)
            
            if enable_verbal:
                # Generate both text and verbal responses
                resp_gen_start = time.perf_counter()
                response = self.response_generator.generate_with_verbal(
                    query, 
                    category, 
                    rules_and_examples.get("response_rules", {}),
                    query_results.get("results") if query_results and query_results.get("success", False) else None,
                    context
                )
                timers['response_generation'] = time.perf_counter() - resp_gen_start
                
                tts_start = time.perf_counter()
                verbal_response = self.response_generator.generate_verbal_response(
                    query, 
                    category, 
                    rules_and_examples.get("response_rules", {}),
                    query_results.get("results") if query_results and query_results.get("success", False) else None,
                    context
                )
                timers['tts_generation'] = time.perf_counter() - tts_start
            else:
                # Generate only text response
                resp_gen_start = time.perf_counter()
                response = self.response_generator.generate(
                    query, 
                    category, 
                    rules_and_examples.get("response_rules", {}),
                    query_results.get("results") if query_results and query_results.get("success", False) else None,
                    context
                )
                timers['response_generation'] = time.perf_counter() - resp_gen_start
            
            # Build final response
            result = {
                "query_id": query_id,
                "query": query,
                "category": category,
                "response": response.get("text"),
                "response_model": response.get("model"),
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add verbal response if available
            if enable_verbal and response.get("has_verbal", False):
                result["verbal_audio"] = response.get("verbal_audio")
                result["verbal_text"] = response.get("verbal_text")
                result["has_verbal"] = True
                
                # Log verbal response generation
                verbal_text_length = len(response.get("verbal_text", ""))
                self.logger.info(f"Verbal response generated: {verbal_text_length} chars, {len(response.get('verbal_audio', b''))} bytes")
            elif enable_verbal:
                # Force TTS generation if verbal was requested but not generated
                try:
                    # Generate TTS directly with longer content (up to 3 sentences)
                    self.logger.info("Forcing TTS generation since verbal was requested but not generated")
                    tts_response = self.get_tts_response(
                        result["response"], 
                        model="eleven_multilingual_v2", 
                        max_sentences=3
                    )
                    
                    if tts_response and tts_response.get("audio"):
                        result["verbal_audio"] = tts_response.get("audio")
                        result["verbal_text"] = tts_response.get("text")
                        result["has_verbal"] = True
                        audio_size = len(tts_response.get("audio", b""))
                        text_length = len(tts_response.get("text", ""))
                        self.logger.info(f"Forced verbal response generation: {text_length} chars, {audio_size} bytes")
                        
                        # Save the audio file for debugging if needed
                        if self.config.get("debug", {}).get("save_audio_files", False):
                            try:
                                audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "debug", "audio")
                                os.makedirs(audio_dir, exist_ok=True)
                                audio_file = os.path.join(audio_dir, f"audio_{result['query_id']}.mp3")
                                with open(audio_file, "wb") as f:
                                    f.write(tts_response.get("audio"))
                                self.logger.info(f"Saved audio file for debugging: {audio_file}")
                            except Exception as e:
                                self.logger.error(f"Error saving debug audio file: {str(e)}")
                    else:
                        result["has_verbal"] = False
                        error_msg = tts_response.get("error", "Unknown error")
                        self.logger.error(f"Forced verbal response failed to generate audio: {error_msg}")
                except Exception as e:
                    self.logger.error(f"Error generating forced verbal response: {str(e)}")
                    result["has_verbal"] = False
                    self.logger.info("No verbal response could be generated")
            else:
                result["has_verbal"] = False
                self.logger.info("No verbal response was generated")
                # Add detailed debugging information about why no verbal response was generated
                if fast_mode:
                    self.logger.info("Verbal response skipped because fast_mode is enabled")
                elif not hasattr(self.response_generator, 'elevenlabs_client') or not self.response_generator.elevenlabs_client:
                    self.logger.info("Verbal response skipped because ElevenLabs client is not initialized")
                elif not hasattr(self.response_generator, 'elevenlabs_api_key') or not self.response_generator.elevenlabs_api_key:
                    self.logger.info("Verbal response skipped because ElevenLabs API key is not configured")
                elif not self.config.get("features", {}).get("enable_tts", False):
                    self.logger.info("Verbal response skipped because TTS feature is not enabled in config")
                else:
                    self.logger.info("Verbal response skipped for unknown reason")
            
            # Include query results in the response if available and successful
            if query_results and query_results.get("success", False):
                result["query_results"] = query_results.get("results")
                # Include performance metrics if available
                if "performance_metrics" in query_results:
                    result["performance_metrics"] = query_results.get("performance_metrics")
            elif query_results and not query_results.get("success", False):
                # Include error information if execution failed
                result["error"] = query_results.get("error")
            
            # Log query completion
            self.logger.info(f"Query processing completed in {result['execution_time']:.2f}s")
            
            # Add the current interaction to conversation history
            conversation_entry = {
                "timestamp": result["timestamp"],
                "query": query,
                "response": result["response"],
                "verbal_text": result.get("verbal_text", ""),
                "category": category
            }
            
            # Add entry to conversation history, limiting the size
            self.conversation_history.append(conversation_entry)
            if len(self.conversation_history) > self.max_history_items:
                self.conversation_history = self.conversation_history[-self.max_history_items:]
            
            # Store SQL in history if it was generated
            if current_sql:
                sql_entry = {
                    "timestamp": result["timestamp"],
                    "query": query,
                    "sql": current_sql,
                    "category": category
                }
                self.sql_history.append(sql_entry)
                if len(self.sql_history) > self.max_history_items:
                    self.sql_history = self.sql_history[-self.max_history_items:]
            
            # Generate perf breakdown
            # Final timing summary
            timers['total_duration'] = time.perf_counter() - timers['total_start']
            
            # Calculate properly measured timings
            measured_time = (
                timers['classification'] + 
                timers['rule_processing'] + 
                timers['sql_generation'] + 
                timers['sql_execution'] + 
                timers['response_generation'] + 
                timers['tts_generation']
            )
            
            # Ensure other/unaccounted doesn't go negative
            other_time = max(0.01, timers['total_duration'] - measured_time)
            
            logger.info(f"""
                Performance Breakdown:
                - Classification: {timers['classification']:.2f}s
                - Rule Processing: {timers['rule_processing']:.2f}s
                - SQL Generation: {timers['sql_generation']:.2f}s
                - SQL Execution: {timers['sql_execution']:.2f}s
                - Text Response: {timers['response_generation']:.2f}s
                - TTS Generation: {timers['tts_generation']:.2f}s
                - Other/Unaccounted: {other_time:.2f}s
                - Total Time: {timers['total_duration']:.2f}s
            """)

            return result
        except Exception as e:
            self.retry_counter += 1  # Increment on retry
            logger.error(f"Failure context: {self._get_error_context()}")
            raise

    def _preprocess_sql(self, sql_query: str) -> str:
        """
        Preprocess SQL query by replacing symbolic placeholders with default values.
        This is a simplified version of the more complex preprocessing in SQLExecutor.
        
        Args:
            sql_query: The SQL query with potential placeholders
            
        Returns:
            Processed SQL with placeholders replaced
        """
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
        return processed_sql

    def set_persona(self, persona_name: str) -> None:
        """
        Set the current persona for response generation.
        
        Args:
            persona_name: Name of the persona to use
        """
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
    
    def get_tts_response(self, text: str, model: str = "eleven_multilingual_v2", max_sentences: int = 1) -> Dict[str, Any]:
        """
        Get a text-to-speech response using the configured TTS service.
        
        Args:
            text: The text to convert to speech
            model: The TTS model to use
            max_sentences: Maximum number of sentences to include
            
        Returns:
            Dictionary with audio data and metadata
        """
        try:
            # Extract the first few sentences if needed
            if max_sentences > 0:
                sentences = re.split(r'(?<=[.!?])\s+', text)
                limited_text = ' '.join(sentences[:max_sentences])
            else:
                limited_text = text
            
            self.logger.info(f"Generating TTS for text: '{limited_text[:100]}...' (length: {len(limited_text)})")
                
            # Use elevenlabs if available
            if hasattr(self.response_generator, 'elevenlabs_client') and self.response_generator.elevenlabs_client:
                try:
                    # Ensure elevenlabs is imported and API key is set
                    import elevenlabs
                    elevenlabs.set_api_key(self.response_generator.elevenlabs_api_key)
                    
                    # Get voice ID from configuration - use a known working voice ID as fallback
                    voice_id = self.config.get("api", {}).get("elevenlabs", {}).get("voice_id", "EXAVITQu4vr4xnSDxMaL")
                    self.logger.info(f"Using ElevenLabs voice ID: {voice_id}")
                    
                    # Generate audio with specified model (using approach from test_elevenlabs.py)
                    start_time = time.time()
                    audio_data = elevenlabs.generate(
                        text=limited_text,
                        voice=voice_id,
                        model=model
                    )
                    gen_time = time.time() - start_time
                    
                    if audio_data:
                        self.logger.info(f"Successfully generated {len(audio_data)} bytes of audio data in {gen_time:.2f}s")
                        return {
                            "audio": audio_data,
                            "text": limited_text,
                            "success": True
                        }
                    else:
                        self.logger.error("ElevenLabs returned empty audio data")
                        return {
                            "audio": None,
                            "text": limited_text,
                            "success": False,
                            "error": "Empty audio data returned"
                        }
                        
                except Exception as e:
                    self.logger.error(f"Error generating TTS with ElevenLabs: {str(e)}")
                    # Provide more detailed error information
                    error_details = str(e)
                    if "401" in error_details:
                        self.logger.error("Authentication error with ElevenLabs API. Check your API key.")
                    elif "voice not found" in error_details.lower():
                        self.logger.error(f"Voice ID '{voice_id}' not found in your ElevenLabs account.")
                    elif "model not found" in error_details.lower():
                        self.logger.error(f"Model '{model}' not found. Try using eleven_multilingual_v2 instead.")
                    
                    return {
                        "audio": None,
                        "text": limited_text,
                        "success": False,
                        "error": f"ElevenLabs error: {str(e)}"
                    }
            
            # Fallback to a different TTS service or return nothing
            return {
                "audio": None,
                "text": limited_text,
                "success": False,
                "error": "No TTS service available"
            }
        except Exception as e:
            self.logger.error(f"Error in TTS processing: {str(e)}")
            return {
                "audio": None,
                "text": text,
                "success": False,
                "error": f"TTS processing error: {str(e)}"
            }

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
        
    def test_tts(self, text: str = None, save_to_file: bool = True) -> Dict[str, Any]:
        """
        Test the TTS functionality directly.
        
        Args:
            text: Optional text to convert to speech (default is a test message)
            save_to_file: Whether to save the audio to a file for testing
            
        Returns:
            Dictionary with test results
        """
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
                audio_size = len(audio_data)
                self.logger.info(f"TTS test successful: Generated {audio_size} bytes in {generation_time:.2f}s")
                
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
                    "audio_size": audio_size,
                    "generation_time": generation_time,
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

    def _ensure_elevenlabs_initialized(self):
        """Ensure ElevenLabs is properly initialized for TTS"""
        # Add initialization debugging
        self.logger.info("Attempting to initialize ElevenLabs for TTS")
        
        # Check if TTS is enabled in configuration
        if not self.config.get("features", {}).get("enable_tts", False):
            self.logger.warning("TTS feature is disabled in configuration, skipping ElevenLabs initialization")
            return False
            
        # Check if response generator exists
        if not hasattr(self, 'response_generator') or self.response_generator is None:
            self.logger.error("Response generator is not initialized, cannot setup ElevenLabs")
            return False
            
        # Check if API key is configured
        elevenlabs_api_key = getattr(self.response_generator, 'elevenlabs_api_key', None)
        if not elevenlabs_api_key:
            self.logger.error("ElevenLabs API key is not configured in response generator")
            return False
        
        # Check if response generator has elevenlabs client
        if hasattr(self.response_generator, 'elevenlabs_client') and self.response_generator.elevenlabs_client:
            try:
                # Ensure elevenlabs is imported and API key is set
                import elevenlabs
                
                # Log the API key length for debugging (don't log the actual key)
                self.logger.info(f"Setting ElevenLabs API key (length: {len(elevenlabs_api_key)})")
                elevenlabs.set_api_key(elevenlabs_api_key)
                
                # Try to validate the API key by making a small request
                try:
                    voices = elevenlabs.voices()
                    voice_count = len(voices) if hasattr(voices, '__len__') else 0
                    self.logger.info(f"ElevenLabs API key validated successfully, found {voice_count} voices")
                except Exception as e:
                    self.logger.error(f"ElevenLabs API key validation failed: {str(e)}")
                    return False
                
                self.logger.info("ElevenLabs initialized successfully for TTS")
                return True
            except Exception as e:
                self.logger.error(f"Error initializing ElevenLabs: {str(e)}")
                return False
        else:
            self.logger.warning("ElevenLabs client not available in response generator")
            return False

# Alias OrchestratorService as Orchestrator for compatibility with frontend code
Orchestrator = OrchestratorService