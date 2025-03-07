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
            elevenlabs.set_api_key(self.elevenlabs_api_key)
            self.elevenlabs_client = True  # Just a flag to indicate ElevenLabs is available
            logger.info("ElevenLabs TTS initialized successfully")
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
        
        # Model configuration
        self.temperature = config.get("services", {}).get("response", {}).get("temperature", 0.7)
        self.max_tokens = config.get("services", {}).get("response", {}).get("max_tokens", 1000)
        
        # Verbal model configuration (can be different from text model)
        self.verbal_model = config.get("services", {}).get("response", {}).get("verbal_model", self.default_model)
        self.verbal_temperature = config.get("services", {}).get("response", {}).get("verbal_temperature", 0.7)
        self.verbal_max_tokens = config.get("services", {}).get("response", {}).get("verbal_max_tokens", 100)
        
        self.generate_dedicated_verbal = config.get("services", {}).get("response", {}).get("generate_dedicated_verbal", True)
        
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
        Log detailed information about an API call for debugging purposes.
        
        Args:
            api_name: Name of the API service (e.g., 'openai', 'elevenlabs')
            endpoint: Specific endpoint or method called
            params: Parameters sent to the API
            start_time: API call start time
            end_time: API call end time
            success: Whether the call was successful
            response_data: Optional summary of response data
            error: Error message if the call failed
        """
        call_id = str(uuid.uuid4())[:8]
        duration = end_time - start_time
        
        # Update API call statistics
        if api_name in self.api_calls:
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
        
        # Create a detailed log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id,
            "api": api_name,
            "endpoint": endpoint,
            "duration_seconds": duration,
            "success": success,
            "params": {k: v for k, v in params.items() if k not in ["messages", "text"]}  # Avoid logging full prompts
        }
        
        # Add request summary if available
        if api_name == "openai" and "messages" in params:
            # Summarize the messages without including full content
            log_entry["request_summary"] = {
                "message_count": len(params["messages"]),
                "system_message_length": len(params["messages"][0]["content"]) if params["messages"] and params["messages"][0]["role"] == "system" else 0,
                "user_message_length": sum(len(m["content"]) for m in params["messages"] if m["role"] == "user")
            }
        elif api_name == "elevenlabs" and "text" in params:
            log_entry["request_summary"] = {
                "text_length": len(params["text"]),
                "text_preview": params["text"][:50] + "..." if len(params["text"]) > 50 else params["text"]
            }
        
        # Add response summary or error details
        if success and response_data:
            if api_name == "openai":
                log_entry["response_summary"] = {
                    "tokens": response_data.get("usage", {}).get("total_tokens", 0),
                    "completion_length": len(response_data.get("choices", [{}])[0].get("message", {}).get("content", "")) if response_data.get("choices") else 0
                }
            elif api_name == "elevenlabs":
                log_entry["response_summary"] = {
                    "audio_bytes": len(response_data.get("audio", b"")) if isinstance(response_data.get("audio"), bytes) else 0
                }
        elif error:
            log_entry["error"] = error
        
        # Log to both console and file
        logger.info(f"[API_CALL:{call_id}] {api_name}.{endpoint} - {'SUCCESS' if success else 'FAILED'} - {duration:.2f}s")
        
        # Write detailed log to file
        with open(self.api_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return call_id

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
        
        # Load the appropriate template for this category
        template = self._load_template_for_category(category)
        
        # Format results for the prompt (can be quite large)
        if query_results:
            results_text = json.dumps(query_results, indent=2)
        else:
            results_text = "No database results available."
            
        # Format response rules
        rules_text = self._format_rules(response_rules)
        
        # System message based on category and persona
        system_message = self._build_system_message(category)
        
        # Add conversation history to provide context
        history_prompt = ""
        if context.get("conversation_history"):
            history_entries = context["conversation_history"]
            
            if history_entries:
                history_prompt = "\nPrevious conversation history:\n"
                
                # Include the most recent entries (limited to 3 for brevity)
                for i, entry in enumerate(history_entries[-3:], 1):
                    history_prompt += f"User query {i}: {entry.get('query', '')}\n"
                    history_prompt += f"Your response {i}: {entry.get('response', '')}\n"
                    history_prompt += "\n"
                
                history_prompt += "Use this conversation history to maintain a natural conversation flow in your response.\n"
        
        # Create user message
        user_message = f"""
QUERY RESULTS FROM DATABASE (USE THIS DATA REGARDLESS OF DATES):
{results_text}

Category: {category}

Response Rules:
{rules_text}

{history_prompt}

User Query: {query}
"""

        # Set up logging for the prompt and response
        session_id = str(uuid.uuid4())[:8]
        log_dir = os.path.join("logs", "ai_prompts")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"openai_response_{session_id}.log")
        
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"QUERY: {query}\n")
            f.write(f"CATEGORY: {category}\n")
            f.write("\n----- SYSTEM MESSAGE -----\n\n")
            f.write(system_message)
            f.write("\n\n----- USER MESSAGE -----\n\n")
            f.write(user_message)
            f.write("\n\n")

        logger.info(f"Response generation prompt logged to: {log_file}")
        
        # Create messages for the chat completion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Prepare parameters for API call
        api_params = {
            "model": self.default_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        # Call OpenAI API with detailed logging
        try:
            start_time = time.time()
            logger.info(f"Sending request to OpenAI API with model: {self.default_model}")
            
            response = self.client.chat.completions.create(**api_params)
            
            end_time = time.time()
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            # Log the successful API call
            response_data = {
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                },
                "choices": [{
                    "message": {
                        "content": response_text
                    }
                }]
            }
            
            call_id = self._log_api_call(
                api_name="openai",
                endpoint="chat.completions.create",
                params=api_params,
                start_time=start_time,
                end_time=end_time,
                success=True,
                response_data=response_data
            )
            
            # Process response for rich media if enabled
            if self.enable_rich_media:
                response_text = self._process_response_for_rich_media(response_text, category)
            
            # At the end, update cache with the new response
            self._update_cache(query, category, {
                "text": response_text,
                "model": self.default_model,
                "processing_time": time.time(),
                "category": category,
                "api_call_id": call_id  # Add the API call ID for tracking
            })
            
            return {
                "text": response_text,
                "model": self.default_model,
                "processing_time": time.time(),
                "category": category,
                "api_call_id": call_id  # Add the API call ID for tracking
            }
        except Exception as e:
            end_time = time.time()
            error_msg = f"Error generating response: {str(e)}"
            
            # Log the failed API call
            call_id = self._log_api_call(
                api_name="openai",
                endpoint="chat.completions.create",
                params=api_params,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error=str(e)
            )
            
            logger.error(f"[API_CALL:{call_id}] {error_msg}")
            
            # Log the error
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("----- ERROR -----\n\n")
                f.write(error_msg)
                f.write("\n\n")
            
            return {
                "text": f"I apologize, but I encountered an issue generating a response. Error: {str(e)}",
                "model": self.default_model,
                "error": str(e),
                "api_call_id": call_id  # Add the API call ID for tracking
            }
    
    def _build_system_message(self, category: str, persona: str = None) -> str:
        """
        Build a system message based on the query category and current persona.
        
        Args:
            category: The query category
            persona: Optional persona override, defaults to self.persona if not provided
            
        Returns:
            System message string
        """
        base_message = "You are a helpful restaurant assistant providing accurate information."
        
        # Add category-specific instructions
        if category == "menu":
            category_instructions = " When discussing menu items, be enthusiastic and highlight unique features. Format prices consistently."
        elif category == "order_history":
            category_instructions = " When discussing order history, be professional and precise with dates and order details. IMPORTANT: Always use the Query Results provided to you regardless of the dates mentioned - these come directly from our database which contains data for past, present, and future dates. Do NOT apply your knowledge cutoff date to the database content."
        elif category in ["update_price", "enable_item", "disable_item", "delete_options"]:
            category_instructions = " Confirm database changes clearly and concisely, highlighting what was modified."
        elif category == "analysis":
            category_instructions = " Provide data-driven insights and summarize key trends. Be analytical but explain clearly."
        elif category == "error":
            category_instructions = " Apologize for the error and provide any helpful information about what might have gone wrong."
        else:
            category_instructions = ""
        
        # Add critical instruction for ALL categories about using provided data
        data_instructions = "\n\nCRITICAL: The 'Query Results' provided to you contain real-time data from our database system. You MUST use this data to answer questions regardless of dates mentioned (past, present, or future). The database contains valid data for all dates, including dates beyond your training cutoff. NEVER refuse to answer or state you don't have data if Query Results are provided."
        
        # Add persona-specific instructions
        try:
            # Handle case where self.persona might be a dict or a string
            persona_name = persona if persona else self.persona
            if isinstance(self.persona, dict):
                persona_name = self.persona.get('default', 'casual')
                logger.info(f"Using persona configuration with default: {persona_name}")
            
            persona_instructions = get_prompt_instructions(persona_name)
            if persona_instructions:
                logger.info(f"Using persona '{persona_name}' for response generation")
                # Combine base message, category instructions, data instructions, and persona instructions
                return f"{base_message}{category_instructions}{data_instructions}\n\n{persona_instructions}"
        except Exception as e:
            logger.warning(f"Error loading persona instructions: {str(e)}")
        
        # Default message with just category and data instructions if no persona is available
        return base_message + category_instructions + data_instructions
    
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
            # Simple test query
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=5
            )
            return response is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
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
            logger.info(f"Response generator persona set to: {persona_name}")
    
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
                logger.warning("No verbal text was generated to convert to speech")
                return None
                
            logger.info(f"Verbal text generated: '{verbal_text[:100]}...' ({len(verbal_text)} chars)")
            
            # Get voice settings based on current persona
            voice_settings = get_voice_settings(self.persona)
            voice_id = voice_settings.get('voice_id')
            
            if not voice_id:
                logger.warning("No voice ID configured for persona: {self.persona}")
                voice_id = "EXAVITQu4vr4xnSDxMaL"  # Use default voice
                
            logger.info(f"Using ElevenLabs voice ID: {voice_id}")
            
            # Prepare parameters for ElevenLabs API call
            elevenlabs_params = {
                "text": verbal_text,
                "voice": voice_id,
                "model": "eleven_multilingual_v2"
            }
            
            # Generate audio with ElevenLabs with detailed logging
            start_time = time.time()
            logger.info("Calling ElevenLabs API for text-to-speech conversion")
            
            try:
                audio_data = elevenlabs.generate(**elevenlabs_params)
                end_time = time.time()
                
                if audio_data:
                    # Log the successful API call
                    call_id = self._log_api_call(
                        api_name="elevenlabs",
                        endpoint="generate",
                        params=elevenlabs_params,
                        start_time=start_time,
                        end_time=end_time,
                        success=True,
                        response_data={"audio": audio_data, "audio_bytes": len(audio_data)}
                    )
                    
                    logger.info(f"[VERBAL_API_CALL:{call_id}] Successfully generated {len(audio_data)} bytes of audio data")
                    return audio_data
                else:
                    # Log the unsuccessful API call (no error but empty response)
                    call_id = self._log_api_call(
                        api_name="elevenlabs",
                        endpoint="generate",
                        params=elevenlabs_params,
                        start_time=start_time,
                        end_time=time.time(),
                        success=False,
                        error="ElevenLabs returned empty audio data"
                    )
                    
                    logger.error(f"[VERBAL_API_CALL:{call_id}] ElevenLabs returned empty audio data")
                    return None
                    
            except Exception as e:
                # Log the failed API call
                call_id = self._log_api_call(
                    api_name="elevenlabs",
                    endpoint="generate",
                    params=elevenlabs_params,
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    error=str(e)
                )
                
                logger.error(f"[VERBAL_API_CALL:{call_id}] Error calling ElevenLabs API: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating verbal response: {str(e)}")
            return None
    
    def _generate_verbal_text(self, query: str, category: str, response_rules: Dict[str, Any],
                           query_results: Optional[List[Dict[str, Any]]], context: Dict[str, Any]) -> Optional[str]:
        """Generate a concise verbal text for TTS conversion"""
        try:
            # Generate a concise verbal response
            if self.generate_dedicated_verbal:
                # Generate a dedicated concise verbal response
                prompt = f"""Create a brief and clear spoken response for the question:
                "{query}"
                
                The response should be in a {context.get('persona', self.verbal_persona)} tone, 
                easy to listen to, and no more than 2-3 sentences.
                Focus only on the most important information.
                """
                
                if query_results:
                    prompt += f"\n\nRelevant data: {str(query_results)[:500]}"
                
                # Get response using model
                verbal_response = self.client.chat.completions.create(
                    model=self.verbal_model,
                    messages=[
                        {"role": "system", "content": self._build_system_message(category, context.get('persona', self.verbal_persona))},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.verbal_temperature,
                    max_tokens=self.verbal_max_tokens
                )
                
                verbal_text = verbal_response.choices[0].message.content
                
                # Ensure the verbal text isn't too long
                if len(verbal_text.split()) > 100:  # Arbitrary limit of 100 words
                    sentences = verbal_text.split('. ')
                    verbal_text = '. '.join(sentences[:self.max_verbal_sentences]) + ('.' if not sentences[0].endswith('.') else '')
            else:
                # Use a portion of the regular text response
                response = self.generate(query, category, response_rules, query_results, context)
                response_text = response["response"]
                
                # Extract first few sentences for verbal response
                sentences = response_text.split('. ')
                verbal_text = '. '.join(sentences[:self.max_verbal_sentences]) + ('.' if not sentences[0].endswith('.') else '')
                
            return verbal_text
            
        except Exception as e:
            logger.error(f"Error generating verbal text: {str(e)}")
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
        Generate both text and verbal responses using multi-threading for efficiency.
        
        Args:
            Same as generate()
            
        Returns:
            Response dictionary with both text response and verbal audio
        """
        # Check if elevenlabs is available to avoid wasted processing
        enable_verbal = context.get("enable_verbal", False) and self.elevenlabs_client
        
        # Define the text and verbal response generation functions
        def generate_text_response():
            # Use text-specific persona for text response
            text_persona = context.get("text_persona", self.text_persona)
            text_context = context.copy()
            text_context["persona"] = text_persona
            
            return self.generate(
                query, 
                category, 
                response_rules, 
                query_results, 
                text_context
            )
        
        def generate_verbal_response_wrapper():
            # Use verbal-specific persona for speech
            verbal_persona = context.get("verbal_persona", self.verbal_persona)
            verbal_context = context.copy()
            verbal_context["persona"] = verbal_persona
            
            return self.generate_verbal_response(
                query, 
                category, 
                response_rules, 
                query_results, 
                verbal_context
            )
            
        # Generate both responses, with text generation always running
        text_response = generate_text_response()
        verbal_audio = None
        
        # Generate verbal response if enabled
        if enable_verbal:
            try:
                # Generate verbal response
                verbal_audio = generate_verbal_response_wrapper()
                
                # Mark that we have verbal response
                if verbal_audio:
                    text_response["has_verbal"] = True
                    text_response["verbal_audio"] = verbal_audio
            except Exception as e:
                logger.error(f"Error generating verbal response: {str(e)}")
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