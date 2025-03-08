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

from resources.ui.personas import get_voice_settings
from services.utils.service_registry import ServiceRegistry
from services.classification.classifier import ClassificationService
from services.rules.rules_service import RulesService
from services.sql_generator.sql_generator_factory import SQLGeneratorFactory
from services.execution.sql_executor import SQLExecutor
from services.response.response_generator import ResponseGenerator

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
        
        # Initialize service registry
        ServiceRegistry.initialize(config)
        
        # Register services
        ServiceRegistry.register("classification", lambda cfg: ClassificationService(cfg))
        ServiceRegistry.register("rules", lambda cfg: RulesService(cfg))
        ServiceRegistry.register("sql_generator", lambda cfg: SQLGeneratorFactory.create_sql_generator(cfg))
        ServiceRegistry.register("execution", lambda cfg: SQLExecutor(cfg))
        ServiceRegistry.register("response", lambda cfg: ResponseGenerator(cfg))
        
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
        
        # Log all input parameters
        self.logger.info(f"PROCESS_QUERY INPUT - query: '{query}'")
        self.logger.info(f"PROCESS_QUERY INPUT - context: {context}")
        self.logger.info(f"PROCESS_QUERY INPUT - fast_mode: {fast_mode}")
        
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
            
            # Check if verbal response is requested
            if context and context.get("enable_verbal", False):
                self.logger.info(f"Verbal response requested, disabling fast_mode (original fast_mode={fast_mode})")
                fast_mode = False
                
                # Check if ElevenLabs is initialized, and try to initialize it if not
                if not self.elevenlabs_initialized:
                    self.logger.warning("Verbal response requested but ElevenLabs not initialized, attempting to initialize")
                    self.elevenlabs_initialized = self.initialize_elevenlabs_tts()
                    if not self.elevenlabs_initialized:
                        self.logger.warning("Failed to initialize ElevenLabs, switching back to fast_mode (text-only response)")
                        # If ElevenLabs couldn't be initialized, go back to text-only mode
                        fast_mode = True
                        context["enable_verbal"] = False
                
                # Perform a health check on the response generator
                self.logger.info("Performing health check on response generator")
                response_generator_health = False
                try:
                    if self.response_generator:
                        response_generator_health = self.response_generator.health_check()
                        self.logger.info(f"Response generator health check result: {response_generator_health}")
                    else:
                        self.logger.error("Response generator not available")
                except Exception as e:
                    self.logger.error(f"Error during response generator health check: {str(e)}")
            
            context["fast_mode"] = fast_mode
            
            # Step 1: Classify the query
            self.logger.debug(f"Classifying query: '{query}'")
            t1 = time.perf_counter()
            classification = self.classifier.classify(query)
            category = classification.get("category")
            time_period_clause = classification.get("time_period_clause")  # Extract time period clause
            is_followup = classification.get("is_followup", False)  # Extract follow-up indicator
            timers['classification'] = time.perf_counter() - t1
            
            self.logger.info(f"Query classified as: {category}")
            
            # Handle time period context
            if time_period_clause:
                self.logger.info(f"Time period identified: {time_period_clause}")
                # Update query context with time period
                self.query_context["time_period_clause"] = time_period_clause
                
            # Extract constraints from the query text itself
            query_constraints = self._extract_constraints_from_query(query)
            if query_constraints:
                constraint_str = ", ".join([f"{k}: {v}" for k, v in query_constraints.items()])
                self.logger.info(f"Constraints extracted from query: {constraint_str}")
                self.query_context["previous_filters"].update(query_constraints)
                
            elif is_followup:
                # This is a follow-up question - use full context from previous query
                if self.query_context["time_period_clause"]:
                    self.logger.info(f"Follow-up question detected. Using cached time period: {self.query_context['time_period_clause']}")
                if self.query_context["previous_category"]:
                    self.logger.info(f"Follow-up relates to previous category: {self.query_context['previous_category']}")
                if self.query_context["previous_filters"]:
                    filter_str = ", ".join([f"{k}: {v}" for k, v in self.query_context["previous_filters"].items()])
                    self.logger.info(f"Using filters from previous query: {filter_str}")
            
            # Update query context
            self.query_context["previous_query"] = query
            self.query_context["previous_category"] = category
            
            # Step 2: Get rules for the query category
            t1 = time.perf_counter()
            response_rules = self.rules.get_rules(category, query)
            timers['rule_processing'] = time.perf_counter() - t1
            
            # Step 3: Generate SQL
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
            
            # Make sure we have valid SQL before continuing
            if not sql:
                self.logger.error(f"Failed to generate SQL for query: {query}")
                return {
                    "success": False,
                    "errors": ["Failed to generate SQL. Please try rephrasing your query."],
                    "response": "I couldn't understand how to answer that question. Could you please rephrase it?",
                    "execution_time": time.time() - start_time,
                    "query": query,
                    "category": category,
                    "timers": timers
                }
            
            self.error_context["generated_sql"] = sql
            self.sql_history.append({"sql": sql, "timestamp": datetime.now().isoformat(), "category": category})
            
            # Extract filters from SQL for future reference
            extracted_filters = self._extract_filters_from_sql(sql)
            if extracted_filters:
                self.query_context["previous_filters"].update(extracted_filters)
            
            # Step 4: Execute SQL
            t1 = time.perf_counter()
            execution_result = self.sql_executor.execute(sql)
            timers['sql_execution'] = time.perf_counter() - t1
            self.error_context["execution_result"] = execution_result
            
            query_results = None
            if execution_result and execution_result.get("success", False):
                query_results = execution_result.get("results")
            
            # Step 5: Generate response - THIS IS THE CRITICAL SECTION THAT NEEDS FIXING
            response_data = None
            verbal_audio = None
            
            # Add a check to make sure query_results is not None before generating a response
            if query_results is not None:
                t1 = time.perf_counter()
                
                # Check if we need a verbal response
                if not fast_mode:
                    self.logger.info(f"Generating text and verbal response for query: '{query}'")
                    response_data = self.response_generator.generate_with_verbal(
                        query, 
                        category, 
                        response_rules, 
                        query_results, 
                        context
                    )
                    
                    # Get verbal audio data from response
                    if response_data and "verbal_audio" in response_data:
                        verbal_audio = response_data["verbal_audio"]
                        self.logger.info("Verbal audio received from response generator")
                    elif response_data and "verbal_data" in response_data:  # For backward compatibility
                        verbal_audio = response_data["verbal_data"]
                        self.logger.info("Verbal audio received as 'verbal_data'")
                else:
                    self.logger.info(f"Generating text-only response for query: '{query}'")
                    response_data = self.response_generator.generate(
                        query, 
                        category, 
                        response_rules, 
                        query_results, 
                        context
                    )
                    
                timers['response_generation'] = time.perf_counter() - t1
                
                # Store response in conversation history
                if response_data and response_data.get("response"):
                    self.conversation_history.append({
                        "query": query,
                        "response": response_data.get("response"),
                        "timestamp": datetime.now().isoformat(),
                        "category": category
                    })
                    
                    # Trim history to maximum size
                    if len(self.conversation_history) > self.max_history_items:
                        self.conversation_history = self.conversation_history[-self.max_history_items:]
            else:
                self.logger.warning("Query results were None or empty, cannot generate response")

            # Step 6: Handle TTS if verbal response requested
            verbal_text = None
            
            # Check for verbal response in response_data
            if response_data and response_data.get("verbal_text"):
                verbal_text = response_data.get("verbal_text")
            # If verbal response wasn't generated but is requested, try fallback
            elif not fast_mode and response_data and response_data.get("response") and self.elevenlabs_initialized:
                self.logger.info("Attempting fallback TTS generation")
                t1 = time.perf_counter()
                
                response_text = response_data.get("response")
                if response_text:
                    # Extract first few sentences for verbal response
                    sentences = response_text.split('. ')
                    verbal_text = '. '.join(sentences[:3]) + ('.' if not sentences[0].endswith('.') else '')
                    
                    try:
                        # Only try to generate TTS if ElevenLabs is initialized
                        if self.elevenlabs_initialized:
                            tts_result = self.get_tts_response(verbal_text)
                            if tts_result and tts_result.get("success"):
                                verbal_audio = tts_result.get("audio")
                                self.logger.info("Fallback TTS generated audio")
                            else:
                                self.logger.error(f"Fallback TTS failed: {tts_result.get('error') if tts_result else 'Unknown error'}")
                        else:
                            self.logger.warning("Skipping fallback TTS generation because ElevenLabs is not initialized")
                    except Exception as e:
                        self.logger.error(f"Error in fallback TTS: {str(e)}")
                else:
                    self.logger.error("Cannot generate TTS: text is None or empty")
                    
                timers['tts_generation'] = time.perf_counter() - t1
            
            # Prepare response
            result = {
                "query_id": query_id,
                "query": query,
                "category": category,
                "response": response_data.get("response") if response_data else None,
                "response_model": response_data.get("model") if response_data else None,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "has_verbal": verbal_audio is not None,
                "query_results": query_results
            }
            
            # Add verbal audio to result if available
            if verbal_audio:
                result["verbal_audio"] = verbal_audio
                result["verbal_text"] = verbal_text
                self.logger.info("Added verbal audio to response")
            
            # Add a default response if none was generated but we have query results
            if result["response"] is None and query_results:
                # Create a simple default response based on the query results
                if category == "order_history" and len(query_results) > 0:
                    count = query_results[0].get("order_count", 0)
                    
                    # Try to extract date from the query context
                    date_str = "the specified date"
                    if "time_period_clause" in self.query_context:
                        # Extract date from time period clause if available
                        date_match = re.search(r"updated_at\s*=\s*'([^']+)'", self.query_context["time_period_clause"])
                        if date_match:
                            date_str = date_match.group(1)
                    
                    result["response"] = f"I found {count} completed order(s) on {date_str}."
                elif category == "popular_items" and len(query_results) > 0:
                    # Create a response for popular items queries
                    result["response"] = "Here are the popular items based on your query:\n\n"
                    for idx, item in enumerate(query_results[:5], 1):  # Show top 5 items
                        item_name = item.get("item_name", f"Item {idx}")
                        count = item.get("order_count", 0)
                        result["response"] += f"{idx}. **{item_name}** - Ordered {count} times\n"
                elif category == "trend_analysis" and len(query_results) > 0:
                    # Create a response for trend analysis queries
                    result["response"] = "Here's the trend analysis for your query:\n\n"
                    result["response"] += "The data shows " + ("an upward trend" if len(query_results) > 1 else "the following pattern") + " for the requested period.\n\n"
                    result["response"] += "You can see more details in the Query Details section below."
                else:
                    # Generic response for other categories
                    result["response"] = f"I found {len(query_results)} results for your query. You can see the details in the Query Details section below."

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

            # Log the complete result before returning
            log_result = {k: v for k, v in result.items() if k != 'verbal_audio'}
            self.logger.info(f"PROCESS_QUERY OUTPUT - result: {log_result}")
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

# Alias OrchestratorService as Orchestrator for compatibility with frontend code
Orchestrator = OrchestratorService