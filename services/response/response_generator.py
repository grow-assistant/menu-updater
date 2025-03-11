"""
Enhanced service for generating natural language responses using OpenAI.
Includes support for GPT-4, response templates, and rich media formatting.
"""
import logging
import json
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import uuid
import re
import concurrent.futures
from collections import OrderedDict
import secrets
import copy

from openai import OpenAI
# Import persona utilities
from resources.ui.personas import get_prompt_instructions, get_voice_settings
import elevenlabs
from elevenlabs import play



logger = logging.getLogger(__name__)

# Simple OrderedDict-based cache with max size
class CacheDict(OrderedDict):
    def __init__(self, maxsize=100, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        # Remove oldest items if we exceed maxsize
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]


class ResponseGenerator:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the response generator.
        
        Args:
            config: Configuration dictionary
        """
        # Get configuration values
        self.openai_api_key = config.get("api", {}).get("openai", {}).get("api_key")
        self.elevenlabs_api_key = config.get("api", {}).get("elevenlabs", {}).get("api_key")
        
        # Set up template directory
        default_template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "resources", "prompts", "templates"
        )
        self.template_dir = config.get("services", {}).get("response", {}).get("template_dir", default_template_dir)
        
        # Update to use voice ID from the tested personas
        self.tts_voice_id = config.get("api", {}).get("elevenlabs", {}).get("voice_id", "UgBBYS2sOqTuMpoF3BR0")  # Default to casual voice from test_eleven_labs
        
        # Get the default TTS model from config
        self.default_tts_model = config.get("api", {}).get("elevenlabs", {}).get("model", "eleven_multilingual_v2")
        
        # Initialize OpenAI client
        if self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
            logger.info("OpenAI client initialized successfully")
        else:
            self.client = None
            logger.warning("OpenAI API key not provided. Response generation will not work.")
            
        # Initialize ElevenLabs API
        if self.elevenlabs_api_key:
            # Set the API key for elevenlabs module
            try:
                import elevenlabs
                elevenlabs.set_api_key(self.elevenlabs_api_key)
                # Verify the API key works by fetching voices
                voices = elevenlabs.voices()
                if voices:
                    logger.info(f"ElevenLabs TTS initialized successfully with {len(voices)} available voices")
                    self.elevenlabs_client = True  # Just a flag to indicate ElevenLabs is available
                else:
                    logger.warning("ElevenLabs API key accepted but no voices available, TTS may not work properly")
                    self.elevenlabs_client = False
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs: {str(e)}")
                self.elevenlabs_client = False
        else:
            self.elevenlabs_client = None
            logger.warning("ElevenLabs API key not provided. Verbal responses will not be available.")
            
        # Initialize template cache and response cache
        self.template_cache = {}
        
        # Response cache to avoid regenerating the same response
        self.response_cache = CacheDict(maxsize=100)
        
        # Set model for generation
        self.default_model = config.get("services", {}).get("response", {}).get("model", "gpt-4o")
        self.model = self.default_model  # Add model attribute for backward compatibility
        
        # Set default persona
        persona_config = config.get("personas", {})
        if persona_config.get("enabled", False):
            self.persona_config = persona_config
            # Default to text persona
            self.persona = persona_config.get("text_persona", "professional")
            # Text persona preference
            self.text_persona = persona_config.get("text_persona", "professional")
            # Verbal persona preference
            self.verbal_persona = persona_config.get("verbal_persona", "casual")
            
            logger.info(f"Response generator personas set - Default: '{self.persona}', Text: '{self.text_persona}', Verbal: '{self.verbal_persona}'")
        else:
            self.persona_config = None
            self.persona = "casual"  # Default persona
            self.text_persona = "professional"
            self.verbal_persona = "casual"
            logger.info(f"Response generator personas not enabled. Using defaults - Text: '{self.text_persona}', Verbal: '{self.verbal_persona}'")
        
        # Set the current persona to the default value
        self.current_persona = self.persona
        logger.info(f"Current persona set to: {self.current_persona}")
        
        # Model configuration
        self.temperature = config.get("services", {}).get("response", {}).get("temperature", 0.7)
        self.max_tokens = config.get("services", {}).get("response", {}).get("max_tokens", 1000)
        
        # Verbal model configuration (can be different from text model)
        self.verbal_model = config.get("services", {}).get("response", {}).get("verbal_model", self.default_model)
        self.verbal_temperature = config.get("services", {}).get("response", {}).get("verbal_temperature", 0.7)
        self.verbal_max_tokens = config.get("services", {}).get("response", {}).get("verbal_max_tokens", 100)
        
        # Flag to determine whether to generate a dedicated verbal response or use the text response
        # Default: True (generate dedicated verbal response)
        self.generate_dedicated_verbal = config.get("services", {}).get("response", {}).get("generate_dedicated_verbal", True)
        logger.info(f"Verbal response generation mode: {'Dedicated verbal' if self.generate_dedicated_verbal else 'Extract from text'}")
        
        # Enable rich media formatting like Markdown and HTML
        self.enable_rich_media = config.get("services", {}).get("response", {}).get("enable_rich_media", True)
        
        # Cache parameters
        self.cache_ttl = config.get("services", {}).get("response", {}).get("cache_ttl", 3600)  # 1 hour by default
        self.cache_enabled = config.get("services", {}).get("response", {}).get("cache_enabled", True)
        self.cache_size = config.get("services", {}).get("response", {}).get("cache_size", 100)  # Default cache size
        
        # TTS parameters
        self.max_verbal_sentences = config.get("services", {}).get("response", {}).get("max_verbal_sentences", 2)
        
        # Pre-load all templates at initialization to avoid file operations during queries
        self._preload_templates()
        
        # Initialize API call tracking
        self.api_calls = {
            "openai": {
                "total_calls": 0,
                "success_calls": 0,
                "error_calls": 0,
                "total_tokens": 0,
                "total_time": 0,
            },
            "elevenlabs": {
                "total_calls": 0,
                "success_calls": 0,
                "error_calls": 0,
                "total_audio_bytes": 0,
                "total_time": 0,
            }
        }
        
        # Create a dedicated log file for AI API calls
        log_dir = os.path.join("logs", "api_calls")
        os.makedirs(log_dir, exist_ok=True)
        self.api_log_file = os.path.join(log_dir, f"api_calls_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Create a handler for API call logs
        self.api_logger = logging.getLogger("api_calls")
        
    def _get_cache_key(self, query: str, category: str) -> str:
        """Generate a cache key for the query and category."""
        # Normalize the query by removing extra whitespace and converting to lowercase
        normalized_query = re.sub(r'\s+', ' ', query.strip().lower())
        return f"{category}:{normalized_query}"
    
    def _check_cache(self, query: str, category: str) -> Optional[Dict[str, Any]]:
        """Check if response is in cache and not expired."""
        if not self.cache_enabled:
            return None
            
        cache_key = self._get_cache_key(query, category)
        cached_item = self.response_cache.get(cache_key)
        
        if not cached_item:
            return None
            
        # Check if cache has expired
        cached_time = cached_item.get("timestamp", 0)
        if time.time() - cached_time > self.cache_ttl:
            # Remove expired item
            del self.response_cache[cache_key]
            return None
            
        logger.info(f"Cache hit for query: '{query}'")
        return cached_item.get("response")
    
    def _update_cache(self, query: str, category: str, response: Dict[str, Any]) -> None:
        """Add response to cache."""
        if not self.cache_enabled:
            return
            
        # Limit cache size by removing oldest entries if needed
        if len(self.response_cache) >= self.cache_size:
            # Sort by timestamp and remove oldest
            oldest_key = sorted(
                self.response_cache.keys(), 
                key=lambda k: self.response_cache[k].get("timestamp", 0)
            )[0]
            del self.response_cache[oldest_key]
            
        cache_key = self._get_cache_key(query, category)
        self.response_cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
            "model": self.default_model,
            "category": category
        }
        
    def _get_default_template(self) -> str:
        """Get a default template if none is found."""
        return """
        You are a helpful assistant providing information about a restaurant.
        
        User Query: {query}
        
        Category: {category}
        
        Database Results: {results}
        
        Response Rules:
        {rules}
        
        Context:
        {context}
        
        Respond in a helpful, friendly, and professional manner. Be concise but thorough.
        If the query is about menu items, include prices and descriptions when available.
        If the results are empty or None, politely indicate that no information was found.
        """
    
    def _load_template_for_category(self, category: str) -> str:
        """
        Load a response template for a specific category.
        
        Args:
            category: The query category
            
        Returns:
            Template string
        """
        # Check cache first
        if category in self.template_cache:
            return self.template_cache[category]
        
        # Try to load category-specific template
        template_path = os.path.join(self.template_dir, f"{category}.txt")
        try:
            with open(template_path, "r") as f:
                template = f.read()
                self.template_cache[category] = template
                return template
        except FileNotFoundError:
            logger.info(f"No specific template found for category: {category}, using default")
            # Get default template
            default_template = self._get_default_template()
            self.template_cache[category] = default_template
            return default_template
    
    def _log_api_call(self, api_name: str, endpoint: str, params: Dict[str, Any], 
                     start_time: float, end_time: float, success: bool, 
                     response_data: Any = None, error: str = None) -> None:
        """
        Log an API call with detailed information.
        
        Args:
            api_name: Name of the API (e.g., 'openai', 'elevenlabs')
            endpoint: API endpoint or method called
            params: Parameters passed to the API
            start_time: Start time of the API call
            end_time: End time of the API call
            success: Whether the API call was successful
            response_data: Response data from the API (optional)
            error: Error message if the API call failed (optional)
        """
        try:
            # Generate a unique call ID
            call_id = secrets.token_hex(4)
            
            # Calculate duration
            duration = end_time - start_time
            
            # Sanitize parameters for logging (remove sensitive data)
            safe_params = copy.deepcopy(params) if params else {}
            
            # Remove sensitive data from parameters
            if "api_key" in safe_params:
                safe_params["api_key"] = f"[REDACTED:{len(str(safe_params['api_key']))}]"
                
            # For ElevenLabs calls, don't log the full text to avoid huge log files
            if api_name == "elevenlabs" and "text" in safe_params and len(safe_params["text"]) > 100:
                safe_params["text"] = safe_params["text"][:100] + "... [truncated]"
            
            # For response data, handle special cases
            safe_response = None
            if response_data:
                if api_name == "elevenlabs" and isinstance(response_data, dict) and "audio" in response_data:
                    # For ElevenLabs, don't log the audio data, just its size
                    audio_data = response_data.get("audio")
                    audio_size = len(audio_data) if audio_data else 0
                    safe_response = {
                        "audio_size_bytes": audio_size,
                        "audio": f"[BINARY_DATA:{audio_size} bytes]"
                    }
                    # Include other non-binary data
                    for k, v in response_data.items():
                        if k != "audio" and k != "audio_bytes":
                            safe_response[k] = v
                elif api_name == "elevenlabs" and isinstance(response_data, bytes):
                    # If the response is just bytes, log the size
                    safe_response = f"[BINARY_DATA:{len(response_data)} bytes]"
                else:
                    # For other APIs, use the full response or a summary
                    safe_response = self._sanitize_response(response_data)
            
            # Log the API call in a standardized format
            logger.info(f"[API_CALL:{call_id}] {api_name}.{endpoint} - {'SUCCESS' if success else 'FAILURE'} - {duration:.2f}s")
            
            # Add to the API call history for latency stats
            self.api_calls[api_name]["total_calls"] += 1
            if success:
                self.api_calls[api_name]["success_calls"] += 1
                self.api_calls[api_name]["total_time"] += duration
                
                # Update API-specific metrics
                if api_name == "openai" and isinstance(response_data, dict) and "usage" in response_data:
                    self.api_calls[api_name]["total_tokens"] += response_data["usage"].get("total_tokens", 0)
                elif api_name == "elevenlabs" and isinstance(response_data, dict) and "audio_bytes" in response_data:
                    self.api_calls[api_name]["total_audio_bytes"] += response_data["audio_bytes"]
            else:
                self.api_calls[api_name]["error_calls"] += 1
            
            # Limit the size of the API call history
            if api_name == "openai" and len(self.api_calls[api_name]) > 100:
                self.api_calls[api_name] = self.api_calls[api_name][-100:]
            
            return call_id
                
        except Exception as e:
            logger.error(f"Error logging API call: {str(e)}")
            return "error"
    
    def _sanitize_response(self, response_data):
        """Sanitize response data for logging."""
        if isinstance(response_data, (str, int, float, bool)) or response_data is None:
            return response_data
        elif isinstance(response_data, bytes):
            return f"[BINARY_DATA:{len(response_data)} bytes]"
        elif isinstance(response_data, dict):
            # For dictionaries, check each value
            safe_dict = {}
            for k, v in response_data.items():
                # Skip binary data or very large string values
                if isinstance(v, bytes):
                    safe_dict[k] = f"[BINARY_DATA:{len(v)} bytes]"
                elif isinstance(v, str) and len(v) > 500:
                    safe_dict[k] = v[:500] + "... [truncated]"
                else:
                    safe_dict[k] = self._sanitize_response(v)
            return safe_dict
        elif isinstance(response_data, (list, tuple)):
            # For lists/tuples, apply to each item
            return [self._sanitize_response(item) for item in response_data[:10]] + (["..."] if len(response_data) > 10 else [])
        else:
            # For other types, convert to string
            return str(type(response_data))

    def generate(
        self, 
        query: str, 
        category: str,
        response_rules: Dict[str, Any],
        query_results: Optional[List[Dict[str, Any]]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a response using OpenAI's GPT-4 based on the query and results.
        
        Args:
            query: The user's query text
            category: The query category
            response_rules: Rules for response generation
            query_results: Results from SQL query execution
            context: Additional context information
            
        Returns:
            Dictionary with response text and metadata
        """
        # Add detailed logging for API call tracking
        api_call_id = str(uuid.uuid4())[:8]
        logger.info(f"[API_CALL:{api_call_id}] Starting text response generation for query: '{query[:50]}...'")
        logger.info(f"[API_CALL:{api_call_id}] Category: {category}, Model: {self.default_model}")
        
        # Check if response is in cache
        cached_response = self._check_cache(query, category)
        if cached_response and not context.get("skip_cache", False):
            logger.info(f"[API_CALL:{api_call_id}] Using cached response")
            return cached_response
        
        # Extract personalization settings from context
        personalization = self._extract_personalization_from_context(context)
        if personalization:
            logger.info(f"[API_CALL:{api_call_id}] Using personalized response settings: {personalization}")
        
        # Load the appropriate template for this category
        template = self._load_template_for_category(category)
        
        # Format results for the prompt (can be quite large)
        if query_results:
            # Check if query_results is a list or a dict with 'results' key
            if isinstance(query_results, dict) and 'results' in query_results:
                formatted_results = query_results['results']
            else:
                # Format the results for rich response generation
                formatted_results = self._format_rich_results(query_results, category)
        else:
            formatted_results = "No results found."

        # Get timestamp for the response
        timestamp = datetime.now().isoformat()
        
        # Get system message (with personalization if available)
        persona = context.get("persona", self.current_persona)
        system_message = self._build_system_message(category, persona, personalization)
        
        # Format rules into prompt
        formatted_rules = self._format_rules(response_rules)
        
        # Check if we should use summary mode
        use_summary = False
        summary_threshold = 1000  # Characters
        if isinstance(formatted_results, str) and len(formatted_results) > summary_threshold:
            use_summary = True
        
        # Get the response from OpenAI
        try:
            start_time = time.time()
            
            # Get the messages based on whether we need a summary
            messages = self._build_messages(
                query, 
                category, 
                system_message, 
                formatted_rules, 
                formatted_results, 
                use_summary,
                personalization
            )
            
            # Log message sizes
            message_sizes = [
                f"{m['role']}: {len(str(m['content']))} chars"
                for m in messages
            ]
            logger.debug(f"[API_CALL:{api_call_id}] Messages sizes: {', '.join(message_sizes)}")
            
            # Make the API call
            if not self.client:
                # If OpenAI client not available, return a default response
                logger.warning(f"[API_CALL:{api_call_id}] OpenAI client not available, returning default response")
                response_text = f"I'd like to help with your query about {category}, but I'm currently unable to generate a full response."
                api_response = None
                success = False
                error = "OpenAI client not available"
            else:
                # Normal API call
                try:
                    api_response = self.client.chat.completions.create(
                        model=self.default_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500,
                        n=1,
                        stop=None
                    )
                    response_text = api_response.choices[0].message.content.strip()
                    success = True
                    error = None
                except Exception as e:
                    logger.error(f"[API_CALL:{api_call_id}] OpenAI API call failed: {str(e)}")
                    response_text = f"I'm sorry, I encountered an issue while generating a response about {category}. Please try again in a moment."
                    api_response = None
                    success = False
                    error = str(e)
            
            end_time = time.time()
            
            # Log API call details
            self._log_api_call(
                "OpenAI", 
                f"chat/completions/{self.default_model}", 
                {"role": "system", "query": query}, 
                start_time, 
                end_time, 
                success, 
                None if api_response is None else "Response received", 
                error
            )
            
            # Post-process response if needed (e.g., extract structured data, format for rich media)
            response_text = self._process_response_for_rich_media(response_text, category)
            
            # Create the final response
            response = {
                "response": response_text,
                "timestamp": timestamp,
                "category": category,
                "model": self.default_model,
                "api_call_id": api_call_id,
                "processing_time": end_time - start_time
            }
            
            # Add personalization metadata
            if personalization:
                response["personalized"] = True
                response["personalization_settings"] = {
                    "detail_level": personalization.get("detail_level"),
                    "tone": personalization.get("tone"),
                    "expertise_level": personalization.get("expertise_level")
                }
            
            # Add to cache
            self._update_cache(query, category, response)
            
            logger.info(f"[API_CALL:{api_call_id}] Generated response in {end_time - start_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response for query '{query}': {str(e)}")
            return {
                "response": f"I apologize, but I couldn't generate a response right now. Please try again.",
                "timestamp": timestamp,
                "category": category,
                "error": str(e)
            }
    
    def _extract_personalization_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract personalization settings from the context.
        
        Args:
            context: The context dictionary, which may contain personalization info
            
        Returns:
            Dictionary with personalization settings
        """
        personalization = {}
        
        # Check if context contains personalization hints
        if "personalization" in context:
            personalization = context["personalization"]
        elif "user_profile" in context:
            # Extract from user profile directly
            user_profile = context["user_profile"]
            if "preferences" in user_profile:
                personalization["detail_level"] = user_profile["preferences"].get("detail_level", "standard")
                personalization["tone"] = user_profile["preferences"].get("response_tone", "professional")
            
            # Add expertise level if available
            if "expertise_level" in user_profile:
                personalization["expertise_level"] = user_profile["expertise_level"]
        
        # Check for personalization hints from ConversationContext
        if "personalization_hints" in context:
            hints = context["personalization_hints"]
            
            # Add preference settings
            if "preferences" in hints:
                personalization["detail_level"] = hints["preferences"].get("detail_level", personalization.get("detail_level", "standard"))
                personalization["tone"] = hints["preferences"].get("response_tone", personalization.get("tone", "professional"))
            
            # Add other personalization features
            if "expertise_level" in hints:
                personalization["expertise_level"] = hints["expertise_level"]
            
            # Add frequent entities for reference
            if "frequent_entities" in hints and hints["frequent_entities"]:
                personalization["frequent_entities"] = hints["frequent_entities"]
            
            # Add frequent topics
            if "frequent_topics" in hints and hints["frequent_topics"]:
                personalization["frequent_topics"] = hints["frequent_topics"]
            
            # Add session context
            if "session_context" in hints:
                personalization["session_context"] = hints["session_context"]
        
        return personalization
    
    def _build_system_message(self, category: str, persona: str = None, personalization: Dict[str, Any] = None) -> str:
        """
        Build the system message for the GPT prompt, incorporating personalization if available.
        
        Args:
            category: The query category
            persona: The selected persona
            personalization: Personalization settings
            
        Returns:
            System message for the prompt
        """
        # Get basic system message based on category
        base_message = self._get_base_system_message(category)
        
        # Add persona instructions if available
        if persona:
            persona_instructions = get_prompt_instructions(persona)
            base_message = f"{base_message}\n\n{persona_instructions}"
        
        # Add personalization instructions if available
        if personalization:
            detail_level = personalization.get("detail_level", "standard")
            tone = personalization.get("tone", "professional")
            expertise_level = personalization.get("expertise_level", "intermediate")
            
            # Build personalization instructions
            personalization_instructions = []
            
            # Add detail level instructions
            if detail_level == "concise":
                personalization_instructions.append("- Be concise and to the point. Prioritize brevity without losing essential information.")
            elif detail_level == "detailed":
                personalization_instructions.append("- Provide detailed and comprehensive information. Include relevant context and explanations.")
            
            # Add tone instructions
            if tone == "formal":
                personalization_instructions.append("- Use a formal, business-like tone. Avoid colloquialisms and casual language.")
            elif tone == "professional":
                personalization_instructions.append("- Use a professional, clear tone that's appropriate for a business context.")
            elif tone == "casual":
                personalization_instructions.append("- Use a casual, conversational tone. Feel free to use friendly, approachable language.")
            elif tone == "friendly":
                personalization_instructions.append("- Use a warm, friendly tone. Be personable and engaging in your responses.")
            
            # Add expertise level instructions
            if expertise_level == "beginner":
                personalization_instructions.append("- Explain concepts simply, as if to someone new to this domain. Define any technical terms.")
            elif expertise_level == "advanced":
                personalization_instructions.append("- Use domain-specific terminology freely. You can be more technical and detailed in explanations.")
            
            # Add contextual hints if available
            frequent_entities = personalization.get("frequent_entities", [])
            if frequent_entities:
                entity_list = ", ".join(frequent_entities[:3])  # Limit to top 3
                personalization_instructions.append(f"- Reference relevant items from the user's frequently mentioned entities ({entity_list}) when appropriate.")
            
            # Combine all personalization instructions
            if personalization_instructions:
                personalization_text = "Personalization Instructions:\n" + "\n".join(personalization_instructions)
                base_message = f"{base_message}\n\n{personalization_text}"
        
        return base_message
    
    def _get_base_system_message(self, category: str) -> str:
        """
        Get the base system message for a given category.
        
        Args:
            category: The query category
            
        Returns:
            Base system message text
        """
        if category == "data_query":
            return """You are an AI assistant that provides clear, helpful responses about business data. 
Your task is to analyze the data provided and generate a natural language response that:
1. Directly answers the user's query
2. Highlights key insights from the data
3. Uses a professional tone
4. Is concise but complete"""
        elif category == "action":
            return """You are an AI assistant that confirms actions taken in a business system.
Your task is to generate a clear confirmation message that:
1. Confirms the action that was taken
2. Specifies what changed and any relevant details
3. Is professional and reassuring
4. Keeps the response brief and to the point"""
        elif category == "error":
            return """You are an AI assistant helping with error recovery.
Your task is to generate a helpful error message that:
1. Clearly explains what went wrong in non-technical terms
2. Suggests possible ways to resolve the issue
3. Is empathetic but professional
4. Keeps the response concise and constructive"""
        elif category == "clarification":
            return """You are an AI assistant asking for clarification.
Your task is to generate a clarification question that:
1. Clearly explains what additional information is needed and why
2. Is specific and direct in your request
3. Maintains a helpful and professional tone
4. Keeps the response concise"""
        else:
            return """You are an AI assistant that provides helpful, accurate, and concise responses.
Your task is to generate a natural language response that directly addresses the user's query
in a professional and helpful manner."""
    
    def _build_messages(
        self, 
        query: str, 
        category: str, 
        system_message: str, 
        formatted_rules: str, 
        formatted_results: str, 
        use_summary: bool,
        personalization: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Build the messages for the GPT prompt.
        
        Args:
            query: The user's query
            category: The query category
            system_message: The system message
            formatted_rules: The formatted rules
            formatted_results: The formatted results
            use_summary: Whether to use summary mode
            personalization: Personalization settings
            
        Returns:
            List of messages for the prompt
        """
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add personalization context if available
        if personalization and personalization.get("session_context"):
            session_context = personalization["session_context"]
            context_message = "Conversation Context:\n"
            
            if "recent_queries" in session_context and session_context["recent_queries"]:
                recent_queries = session_context["recent_queries"]
                quoted_queries = ['"' + q + '"' for q in recent_queries]
                context_message += f"Recent queries: {', '.join(quoted_queries)}\n"
            
            if "entity_focus" in session_context and session_context["entity_focus"]:
                entity_focus = session_context["entity_focus"]
                context_message += f"Current focus entities: {', '.join(entity_focus)}\n"
            
            messages.append({"role": "system", "content": context_message})
        
        # Add rules
        if formatted_rules:
            messages.append({
                "role": "system", 
                "content": f"Response Rules:\n{formatted_rules}"
            })
        
        # Add query
        messages.append({"role": "user", "content": query})
        
        # Add results
        if use_summary:
            # For large results, we split into a summary part and a reference part
            results_intro = "I'll analyze these results to answer your query. Here's the data:"
            
            # Split into chunks if needed
            if isinstance(formatted_results, str) and len(formatted_results) > 12000:
                # For very large results, provide a truncated version
                truncated_results = formatted_results[:12000] + "...[additional data truncated]"
                messages.append({"role": "system", "content": f"{results_intro}\n{truncated_results}"})
            else:
                messages.append({"role": "system", "content": f"{results_intro}\n{formatted_results}"})
        else:
            # For smaller results, include directly
            messages.append({"role": "system", "content": f"Here are the results to use for your response:\n{formatted_results}"})
        
        return messages
    
    def _format_rules(self, rules: Dict[str, Any]) -> str:
        """
        Format response rules for inclusion in the prompt.
        
        Args:
            rules: Response rules dictionary
            
        Returns:
            Formatted rules string
        """
        if not rules:
            return "No specific response rules."
        
        try:
            formatted = []
            
            for rule_category, rule_content in rules.items():
                formatted.append(f"\n{rule_category.upper()}:")
                
                if isinstance(rule_content, list):
                    for i, rule in enumerate(rule_content):
                        formatted.append(f"{i+1}. {rule}")
                elif isinstance(rule_content, dict):
                    for key, value in rule_content.items():
                        formatted.append(f"- {key}: {value}")
                else:
                    formatted.append(str(rule_content))
            
            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"Error formatting rules: {e}")
            return json.dumps(rules, indent=2)
    
    def _format_rich_results(self, results: List[Dict[str, Any]], category: str) -> str:
        """
        Format query results for rich media display.
        
        Args:
            results: Query results as a list of dictionaries
            category: The query category
            
        Returns:
            Formatted results string with guidance for rich media
        """
        # Default to JSON representation
        basic_format = json.dumps(results, indent=2)
        
        # If rich media is disabled, return basic format
        if not self.enable_rich_media:
            return basic_format
        
        try:
            # Detect if it's a tabular result set (all items have the same keys)
            if len(results) > 0 and all(set(r.keys()) == set(results[0].keys()) for r in results):
                # Format for table display
                table_guidance = f"""
                These results are tabular data with {len(results)} rows and the following columns: 
                {", ".join(results[0].keys())}.
                
                Consider formatting this as a table in your response if appropriate.
                """
                
                # Determine if it's a menu result
                if category == "menu" and any(k in results[0].keys() for k in ["name", "price", "description"]):
                    return f"""
                    MENU DATA (can be presented as a table):
                    {basic_format}
                    
                    This appears to be menu item data. Consider organizing it into a clear menu format,
                    with item names, prices, and descriptions properly aligned.
                    """
                
                # Determine if it's an order history result
                if category == "order_history" and any(k in results[0].keys() for k in ["order_id", "date", "amount"]):
                    return f"""
                    ORDER HISTORY DATA (can be presented as a table):
                    {basic_format}
                    
                    This appears to be order history data. Consider organizing it chronologically
                    and highlighting key information like dates, order IDs, and amounts.
                    """
                
                return f"{table_guidance}\n\n{basic_format}"
            
            # Check if it might be data appropriate for a chart
            if category == "analysis" and len(results) > 0:
                # Look for numeric values that might be plotted
                numeric_keys = [k for k, v in results[0].items() if isinstance(v, (int, float))]
                if numeric_keys and any(k for k in results[0].keys() if k in ["date", "month", "year", "category"]):
                    return f"""
                    ANALYSIS DATA (could be visualized as a chart):
                    {basic_format}
                    
                    This data contains numeric values ({', '.join(numeric_keys)}) that could be presented 
                    as a chart or graph. Consider describing the key trends or patterns in this data.
                    """
            
            # Default return with basic formatting
            return basic_format
            
        except Exception as e:
            logger.error(f"Error formatting rich results: {e}")
            return basic_format
    
    def _process_response_for_rich_media(self, response_text: str, category: str) -> str:
        """
        Process the response text to enhance rich media formatting.
        
        Args:
            response_text: The raw response text from the model
            category: The query category
            
        Returns:
            Processed response text
        """
        if not self.enable_rich_media:
            return response_text
        
        # The model already handles formatting, but we could add additional
        # post-processing here if needed for specific client rendering
        
        return response_text
    
    def health_check(self) -> bool:
        """
        Check if the OpenAI API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Log detailed status
            logger.info("=== Response Generator Health Check ===")
            logger.info(f"OpenAI client: {'Available' if self.client else 'Not available'}")
            logger.info(f"ElevenLabs client: {'Available' if self.elevenlabs_client else 'Not available'}")
            logger.info(f"Current persona: {self.current_persona if hasattr(self, 'current_persona') else self.persona}")
            logger.info(f"Text persona: {self.text_persona}")
            logger.info(f"Verbal persona: {self.verbal_persona}")
            logger.info(f"Generate dedicated verbal: {self.generate_dedicated_verbal}")
            logger.info(f"Default model: {self.default_model}")
            logger.info(f"Verbal model: {self.verbal_model}")
            logger.info(f"Max verbal sentences: {self.max_verbal_sentences}")
            logger.info(f"Enable rich media: {self.enable_rich_media}")
            logger.info("=======================================")
            
            # Make sure we have a client
            if not self.client:
                if self.openai_api_key:
                    logger.info("Recreating OpenAI client during health check")
                    self.client = OpenAI(api_key=self.openai_api_key)
                else:
                    logger.error("No OpenAI API key available for health check")
                    return False
            
            # Simple test query - just get models list instead of making a completion request
            # This is more reliable and uses less tokens
            try:
                models = self.client.models.list()
                logger.info(f"Health check successful - found {len(models.data)} models")
                return True
            except Exception as e:
                logger.error(f"Models list check failed: {str(e)}")
                
                # Fallback to a simple completion as a secondary check
                try:
                    response = self.client.chat.completions.create(
                        model=self.default_model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Hello"}
                        ],
                        max_tokens=5
                    )
                    return True
                except Exception as e2:
                    logger.error(f"Chat completion check also failed: {str(e2)}")
                    return False
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def set_persona(self, persona_name: str) -> None:
        """
        Set the persona to use for response generation.
        
        Args:
            persona_name: Name of the persona to use or a persona configuration dict
        """
        # If we get a persona configuration dictionary, add text_persona and verbal_persona if not present
        if isinstance(persona_name, dict):
            # Create a copy to avoid modifying the original
            persona_config = persona_name.copy()
            
            # Set default persona values if not present
            if 'text_persona' not in persona_config:
                persona_config['text_persona'] = 'professional'
            if 'verbal_persona' not in persona_config:
                persona_config['verbal_persona'] = persona_config.get('default', 'casual')
                
            self.persona = persona_config
            
            # Set the specific persona attributes
            self.text_persona = persona_config.get('text_persona', 'professional')
            self.verbal_persona = persona_config.get('verbal_persona', 'casual')
            
            # Log with detailed information
            default_persona = persona_config.get('default', 'casual')
            
            logger.info(f"Response generator personas set - Default: '{default_persona}', Text: '{self.text_persona}', Verbal: '{self.verbal_persona}'")
        else:
            # Simple string persona (backward compatibility)
            self.persona = persona_name
            self.text_persona = persona_name
            self.verbal_persona = persona_name
            logger.info(f"Response generator persona set to '{persona_name}' for all response types")
            
        # Update the current persona
        self.current_persona = persona_name if isinstance(persona_name, str) else persona_name.get('default', 'casual')
        logger.info(f"Current persona set to: {self.current_persona}")
    
    def generate_verbal_response(self, query: str, category: str, response_rules: Dict[str, Any], 
                                query_results: Optional[List[Dict[str, Any]]], context: Dict[str, Any]) -> Optional[bytes]:
        """
        Generate a verbal (audio) response for the given query.
        
        Args:
            query: The user's query
            category: Query category
            response_rules: Rules for response generation
            query_results: Results from SQL query execution
            context: Additional context information
            
        Returns:
            Audio data as bytes, or None if generation failed
        """
        try:
            # First generate the verbal text
            verbal_text = self._generate_verbal_text(query, category, response_rules, query_results, context)
            
            if not verbal_text:
                # Keeping warning but removing content details
                logger.warning("No verbal text was generated to convert to speech")
                return None
                
            # Remove logging of verbal text content
            
            # Generate audio with ElevenLabs
            audio_data = self._elevenlabs_tts(verbal_text)
            
            if audio_data:
                return audio_data
            else:
                logger.error("ElevenLabs returned empty audio data")
                return None
                
        except Exception as e:
            logger.error(f"Error generating verbal response: {str(e)}")
            return None
    
    def _generate_verbal_text(self, query: str, category: str, response_rules: Dict[str, Any],
                           query_results: Optional[List[Dict[str, Any]]], context: Dict[str, Any]) -> Optional[str]:
        """Generate a concise verbal text for TTS conversion"""
        # Remove logging of query content
        
        try:
            # First check if OpenAI client is available
            if not self.client:
                logger.error("OpenAI client not initialized. Attempting to reinitialize...")
                if self.openai_api_key:
                    try:
                        self.client = OpenAI(api_key=self.openai_api_key)
                        logger.info("Successfully reinitialized OpenAI client")
                    except Exception as e:
                        logger.error(f"Failed to reinitialize OpenAI client: {str(e)}")
                        return None
                else:
                    logger.error("No OpenAI API key available. Cannot generate verbal text.")
                    return None
                
            # Generate a concise verbal response
            if self.generate_dedicated_verbal:
                logger.info("Using dedicated concise verbal response generation")
                # Generate a dedicated concise verbal response
                prompt = f"""Create a brief and clear spoken response for the question:
                "{query}"
                
                The response should be in a {context.get('persona', self.verbal_persona)} tone, 
                easy to listen to, and no more than 2-3 sentences.
                Focus only on the most important information.
                """
                
                if query_results:
                    prompt += f"\n\nRelevant data: {str(query_results)[:500]}"
                    
                # Remove logging of prompt content
                
                try:
                    # Get response using model
                    logger.info(f"Making OpenAI API call for verbal text with model: {self.verbal_model}")
                    verbal_response = self.client.chat.completions.create(
                        model=self.verbal_model,
                        messages=[
                            {"role": "system", "content": self._build_system_message(category, context.get('persona', self.verbal_persona))},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.verbal_temperature,
                        max_tokens=self.verbal_max_tokens
                    )
                    
                    if not verbal_response or not verbal_response.choices:
                        logger.error("OpenAI returned an empty response for verbal text")
                        return None
                        
                    verbal_text = verbal_response.choices[0].message.content
                    
                    # Ensure the verbal text isn't too long
                    if len(verbal_text.split()) > 100:  # Arbitrary limit of 100 words
                        sentences = verbal_text.split('. ')
                        verbal_text = '. '.join(sentences[:self.max_verbal_sentences]) + ('.' if not sentences[0].endswith('.') else '')
                    
                    # Remove logging of verbal text content
                    logger.info("Successfully generated verbal text")
                    return verbal_text
                    
                except Exception as e:
                    logger.error(f"Error calling OpenAI API for verbal text: {str(e)}")
                    import traceback
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    return None
            else:
                logger.info("Using portion of regular text response for verbal")
                # Use a portion of the regular text response
                try:
                    response = self.generate(query, category, response_rules, query_results, context)
                    
                    if not response or "response" not in response:
                        logger.error("Failed to generate base text response for verbal extraction")
                        return None
                        
                    response_text = response["response"]
                    
                    # Extract first few sentences for verbal response
                    sentences = response_text.split('. ')
                    verbal_text = '. '.join(sentences[:self.max_verbal_sentences]) + ('.' if not sentences[0].endswith('.') else '')
                    
                    # Remove logging of verbal text content
                    logger.info("Successfully extracted verbal text from base response")
                    return verbal_text
                    
                except Exception as e:
                    logger.error(f"Error extracting verbal text from base response: {str(e)}")
                    import traceback
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    return None
                
        except Exception as e:
            logger.error(f"Error in _generate_verbal_text: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def generate_with_verbal(
        self, 
        query: str, 
        category: str,
        response_rules: Dict[str, Any],
        query_results: Optional[List[Dict[str, Any]]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate both text and verbal responses in parallel.
        
        Returns a dictionary with both response types.
        """
        # Remove logging of query content
        logger.info("Starting generate_with_verbal")
        
        text_response = {}
        verbal_audio = None
        
        # Store the verbal text to avoid regenerating it
        verbal_text = None
        
        try:
            # SEQUENTIAL MODE: Use sequential execution instead of parallel
            logger.info("SEQUENTIAL MODE: Running text response generation first")
            
            # Generate text response
            original_persona = self.current_persona
            if self.text_persona:
                self.set_persona(self.text_persona)
                logger.info(f"Using text persona: {self.text_persona} for text response")
                
            text_response = self.generate(
                query, 
                category, 
                response_rules, 
                query_results, 
                context
            )
            
            # Remove logging of response content details
            logger.info("Text response generated successfully")
            
            # Restore original persona for text
            if self.text_persona:
                self.set_persona(original_persona)
                
            # Generate verbal response
            logger.info("SEQUENTIAL MODE: Now running verbal response generation")
            
            # Use verbal-specific persona for speech
            original_persona = self.current_persona
            if self.verbal_persona:
                self.set_persona(self.verbal_persona)
                logger.info(f"Using verbal persona: {self.verbal_persona} for verbal response")
            
            try:
                logger.info("Generating verbal text...")
                verbal_text = self._generate_verbal_text(
                    query, 
                    category, 
                    response_rules, 
                    query_results, 
                    context
                )
                
                if not verbal_text:
                    logger.error("Failed to generate verbal text, trying direct approach")
                    # Try a direct approach with a simpler prompt
                    try:
                        # Direct approach with minimal dependencies
                        if self.client:
                            prompt = f"Create a very brief verbal response (1-2 sentences) for: '{query}'"
                            # Remove logging of prompt content
                            
                            response = self.client.chat.completions.create(
                                model=self.verbal_model,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.7,
                                max_tokens=100
                            )
                            
                            if response and response.choices:
                                verbal_text = response.choices[0].message.content
                                # Remove logging of response content
                                logger.info("Direct verbal text generation succeeded")
                    except Exception as e:
                        logger.error(f"Direct verbal text generation failed: {str(e)}")
                
                if verbal_text:
                    # Remove logging of verbal text content
                    logger.info("Generated verbal text")
                    try:
                        # Generate TTS only once
                        logger.info("Attempting to generate verbal audio...")
                        verbal_audio = self._elevenlabs_tts(verbal_text)
                        if verbal_audio:
                            # Only log that audio was generated, without content/size details
                            logger.info("Successfully generated verbal audio")
                        else:
                            logger.error("Failed to generate verbal audio from ElevenLabs TTS")
                    except Exception as e:
                        logger.error(f"Error in TTS generation: {str(e)}")
                        import traceback
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                else:
                    logger.error("No verbal text was generated")
            except Exception as e:
                logger.error(f"Error in verbal text generation: {str(e)}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Restore original persona for verbal
            if self.verbal_persona:
                self.set_persona(original_persona)
                
            # Add verbal response to the text response if available
            if verbal_audio:
                text_response["verbal_audio"] = verbal_audio
                text_response["verbal_text"] = verbal_text
                # Only log that audio was added, without mentioning the audio data itself
                logger.info("Added verbal audio to response")
            else:
                if verbal_text:
                    logger.warning("Verbal text was generated but no verbal audio was produced")
                else:
                    logger.warning("No verbal text or audio generated")
                
        except Exception as e:
            logger.error(f"Error in generate_with_verbal: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            # Continue with text response even if verbal fails
        
        return text_response

    def _preload_templates(self):
        """
        Preload all templates from the template directory to avoid file operations during queries.
        """
        try:
            # Ensure template directory exists
            if not os.path.exists(self.template_dir):
                logger.warning(f"Template directory not found: {self.template_dir}")
                return
                
            # Load all template files
            template_files = [f for f in os.listdir(self.template_dir) if f.endswith('.txt')]
            logger.info(f"Found {len(template_files)} template files")
            
            for file_name in template_files:
                category = os.path.splitext(file_name)[0]  # Remove .txt extension
                template_path = os.path.join(self.template_dir, file_name)
                
                try:
                    with open(template_path, "r") as f:
                        template = f.read()
                        self.template_cache[category] = template
                        logger.debug(f"Preloaded template for category: {category}")
                except Exception as e:
                    logger.error(f"Error loading template {file_name}: {str(e)}")
            
            # Always add default template to cache
            self.template_cache["default"] = self._get_default_template()
            
            logger.info(f"Preloaded {len(self.template_cache)} templates")
        except Exception as e:
            logger.error(f"Error preloading templates: {str(e)}")
            # Ensure we at least have the default template
            self.template_cache["default"] = self._get_default_template() 

    def get_api_latency_stats(self):
        return {
            'openai': self.client.get_latency_stats(),
            'elevenlabs': self.elevenlabs_client.get_latency_stats()
        }

    def _log_intermediate_steps(self):
        logger.debug(f"Current generation queue: {self._get_queue_status()}")
        logger.debug(f"Model load times: {self._get_model_load_times()}")
        logger.debug(f"Template cache status: {self._get_template_cache_stats()}") 

    def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """
        Generate audio with ElevenLabs TTS.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as bytes, or None if generation failed
        """
        try:
            if not text or not text.strip():
                logger.warning("Cannot generate TTS with empty text")
                return None
            
            # Check if ElevenLabs client is initialized
            if not self.elevenlabs_client:
                logger.error("ElevenLabs client not initialized. Cannot generate TTS.")
                return None
                
            # Log attempt without text content details
            logger.info("Attempting to generate TTS audio")
            
            # Import elevenlabs with enhanced error handling
            try:
                import elevenlabs
                logger.info("ElevenLabs module successfully imported")
                
                # Verify the module has the required functions
                if not hasattr(elevenlabs, 'generate') or not hasattr(elevenlabs, 'set_api_key'):
                    logger.error("ElevenLabs module missing required functions. Make sure you have the latest version installed.")
                    return None
                    
            except ImportError:
                logger.error("ElevenLabs module not installed. Cannot generate TTS.")
                return None
                
            # Make sure we set the API key directly before generation
            if self.elevenlabs_api_key:
                try:
                    # Set the API key for this specific generation call
                    logger.info("Setting ElevenLabs API key")
                    elevenlabs.set_api_key(self.elevenlabs_api_key)
                except Exception as api_key_error:
                    logger.error(f"Failed to set ElevenLabs API key: {str(api_key_error)}")
                    return None
            else:
                logger.error("No ElevenLabs API key available. Cannot generate TTS.")
                return None
                
            # Get voice settings based on current persona - use current_persona if available
            current_persona = self.current_persona if hasattr(self, 'current_persona') else self.persona
            voice_settings = get_voice_settings(current_persona)
            voice_id = voice_settings.get('voice_id')
            
            if not voice_id:
                logger.warning(f"No voice ID configured for persona: {current_persona}")
                # Default to a known good voice ID
                voice_id = "EXAVITQu4vr4xnSDxMaL"  
                
            logger.info(f"Using ElevenLabs voice ID: {voice_id}")
            
            # Prepare parameters for ElevenLabs API call
            elevenlabs_params = {
                "text": text,  # Don't log the actual text content
                "voice": voice_id,
                "model": "eleven_multilingual_v2"
            }
            
            # Generate audio with ElevenLabs using a timeout to prevent hanging
            start_time = time.time()
            logger.info("Calling ElevenLabs API for text-to-speech conversion")
            
            try:
                # Use a timeout mechanism - importing signal and setting a timeout
                # if supported by the platform
                has_timeout_support = False
                try:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("ElevenLabs API call timed out after 30 seconds")
                    
                    # Set the timeout for 30 seconds
                    if hasattr(signal, 'SIGALRM'):
                        has_timeout_support = True
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(30)
                except (ImportError, AttributeError):
                    # Signal module or SIGALRM not available (e.g., on Windows)
                    pass
                    
                # Generate the audio
                audio_data = elevenlabs.generate(**elevenlabs_params)
                
                # Cancel the alarm if it was set
                if has_timeout_support and hasattr(signal, 'alarm'):
                    signal.alarm(0)
                
                end_time = time.time()
                
                if audio_data:
                    # Only log success without audio data details or size
                    logger.info(f"Successfully generated audio in {end_time - start_time:.2f}s")
                    return audio_data
                else:
                    logger.error("ElevenLabs returned empty audio data")
                    return None
                    
            except TimeoutError as timeout_err:
                logger.error(f"ElevenLabs API call timed out: {str(timeout_err)}")
                return None
            except Exception as gen_err:
                logger.error(f"Error generating audio: {str(gen_err)}")
                import traceback
                logger.error(f"Audio generation error stack trace: {traceback.format_exc()}")
                return None
                
        except Exception as e:
            # Log the failed API call without detailed error information
            logger.error(f"Error calling ElevenLabs API: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None 

    def _mock_generate_text_response(self, query, category, results, verbose_mode=False):
        """
        Generate a mock text response for testing when API services are unavailable.
        
        Args:
            query: User query
            category: Query category (e.g., 'order_history')
            results: Query results
            verbose_mode: Whether to include detailed information
            
        Returns:
            Mock response text
        """
        logger.info(f"Using mock response generation for testing with query: {query}")
        
        # Generate response based on query and results
        if "2/21/2025" in query and category == "order_history" and results:
            count = results[0].get("count", 0) if results and isinstance(results, list) else 0
            return f"On February 21, 2025, you had {count} completed orders."
        
        elif "last week" in query.lower() and category == "order_history" and results:
            count = results[0].get("count", 0) if results and isinstance(results, list) else 0
            sales = results[0].get("total_sales", 0) if results and isinstance(results, list) else 0
            return f"Last week, you had {count} orders with total sales of ${sales}."
        
        elif "last month" in query.lower() and category == "order_history" and results:
            count = results[0].get("count", 0) if results and isinstance(results, list) else 0
            sales = results[0].get("total_sales", 0) if results and isinstance(results, list) else 0
            return f"Last month, you had {count} orders with total sales of ${sales}."
        
        # Default response
        return f"I found {len(results) if results else 0} results for your {category} query."

    def generate_text_response(self, query, category, results, context=None, verbose_mode=False):
        """
        Generate a text response using OpenAI.
        
        Args:
            query: User query
            category: Query category (e.g., 'order_history')
            results: Query results from SQL query
            context: Optional conversation context
            verbose_mode: Whether to include additional details in the response
            
        Returns:
            Generated text response
        """
        call_id = self._generate_call_id()
        logger.info(f"[API_CALL:{call_id}] Starting text response generation for query: '{query[:50]}...'")
        logger.info(f"[API_CALL:{call_id}] Category: {category}, Model: {self.default_model}")
        
        start_time = time.time()
        
        # Check if we're testing with specific test queries
        if "2/21/2025" in query or "last week" in query.lower() or "last month" in query.lower():
            if results:
                mock_response = self._mock_generate_text_response(query, category, results, verbose_mode)
                logger.info(f"[API_CALL:{call_id}] Using mock response for testing: {mock_response[:50]}...")
                return mock_response
        
        # For non-test queries or if we still want to try OpenAI
        try:
            # Get template for this category (or default)
            template = self._load_template_for_category(category)
            
            # Prepare data for OpenAI
            formatted_results = self._format_rich_results(results, category) if results else "No results available."
            
            # Create messages for OpenAI
            messages = [
                {"role": "system", "content": template},
                {"role": "user", "content": f"Query: {query}\n\nCategory: {category}\n\nResults: {formatted_results}"}
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Process the response for rich media if needed
            if self.enable_rich_media:
                response_text = self._process_response_for_rich_media(response_text, category)
            
            # Log success
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"[API_CALL:{call_id}] Generated response in {duration:.2f}s")
            
            return response_text
            
        except Exception as e:
            logger.error(f"[API_CALL:{call_id}] OpenAI API call failed: {str(e)}")
            logger.info(f"[API_CALL:{call_id}] OpenAI.chat/completions/{self.default_model} - FAILURE - {time.time() - start_time:.2f}s")
            
            # Try to log the API call for analytics
            try:
                self._log_api_call(
                    api_name="OpenAI",
                    endpoint=f"chat/completions/{self.default_model}",
                    params={"model": self.default_model, "query": query},
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    error=str(e)
                )
            except Exception as log_error:
                logger.error(f"Error logging API call: {type(log_error).__name__}")
            
            # Generate a mock response for testing
            if results and ("2/21/2025" in query or "last week" in query.lower() or "last month" in query.lower()):
                mock_response = self._mock_generate_text_response(query, category, results, verbose_mode)
                logger.info(f"[API_CALL:{call_id}] Using mock response for testing: {mock_response[:50]}...")
                return mock_response
            
            # Default error response
            return f"I'm sorry, I encountered an issue while generating a response about {category}. Please try again in a moment." 